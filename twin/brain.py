"""The autonomous robot's decision cycle, for the governor service (docs/AUTONOMY_PLAN.md).

Nothing here is per-scenario. Each cycle:

1. the scene agent (erisml_compiler.runtime) classifies the perception facts into events of
   Margaret's home model and steps its moral state machines;
2. it chooses one action from the allowed set;
3. if that action is `request_authority`, the governor rules on the elevated action it names,
   with the analyzer scoring the situation live (twin/msa_live.py), and the ruling is stepped
   into the moral state as an event; the agent then chooses again from the new allowed set;
4. the whole cycle (facts, events, rejected events, moral state, proposal, ruling, action) is one
   record in the service's hash chain.

Sensors reach the governor through the same trust rule the camera adapter applies: a reading
that is not attested is low-confidence, so it can never count as a witness.

Every call to emergency services the robot places is gated here too (docs/AUTONOMY_PLAN.md,
section 3b), so a fooled or compromised robot cannot send emergency services to Margaret's door
on words alone. The governor rules on the usual bar of two attested physical witnesses (elevate,
which also lifts privacy and the physical actions). Only when the scene's model says the centre
could not be reached does it rule again on a bar of one, and that ruling (authorize_ems)
authorizes the call and nothing else. With no attested witness, nothing authorizes it.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import threading
import time
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from governor import W_MIN, eval_text, govern  # noqa: E402
from cascade import ModelUnavailable  # noqa: E402
from input_layer import validate_facts  # noqa: E402
from output_gate import IDLE as IDLE_ACTION, OutputGate  # noqa: E402
from scenarios import Scenario, Sensor  # noqa: E402

FRESHNESS_BOUND_S = 30.0
EMS = "call_emergency_services"
RESTRAINT_BAR = 3
REFLEX_HOLD_S = 20.0


class BigOutputAdapter:
    """NRP-hosted reasoning models spend output tokens thinking first; give them room."""

    def __init__(self, inner, max_tokens: int = 8000):
        self.inner, self.max_tokens, self.name = inner, max_tokens, getattr(inner, "name", "adapter")

    def call(self, system, user, **kw):
        kw.setdefault("max_tokens", self.max_tokens)
        return self.inner.call(system, user, **kw)


def device_key(device: str) -> bytes:
    """The twin's stand-in for a key provisioned into a device's secure element."""
    return hashlib.sha256(f"gtc-twin-device-key|{device}".encode("utf-8")).digest()


def verify_hmac(payload: bytes, signature: str, key_id: str) -> bool:
    return hmac.compare_digest(hmac.new(device_key(key_id), payload, hashlib.sha256).hexdigest(), str(signature or ""))


class Readings:
    """Trust for sensor readings, applied once before anything counts them.

    Each reading must carry its device's attestation, checked by erisml_compiler.ir.check_attestation:
    the signature (HMAC-SHA256 here, ed25519 on hardware), the signed payload hash against the
    payload, freshness (a stale feed's signature ages out) and the replay counter. The alert is
    read from the signed payload, never from an unsigned field. Readings are then grouped by
    substrate from the scene's device inventory (extra.sensor_substrates): sensors that share a
    substrate (one hub, one body, one bus) inherit each other's faults and count as one witness
    (the principle of network-governor's witness guard). A device outside the inventory never
    counts."""

    def __init__(self, inventory: dict):
        self.inventory = dict(inventory or {})
        # the replay counter is kept per channel: the robot sends the same signed readings down
        # two independently ordered streams (reflexes four times a second, deliberate decisions),
        # and one stream's progress must not make the other's readings look replayed (dev8r d02)
        self.last_counter: dict[tuple[str, str], int] = {}
        self._lock = threading.Lock()

    def verify(self, r: dict, channel: str = "") -> tuple[bool, str, bool]:
        """(trusted, why, alert) for one reading, received now on `channel`."""
        from erisml_compiler.ir import SensorAttestation, check_attestation

        att = r.get("attestation")
        if not att:
            return False, "no attestation", False
        payload = str(r.get("payload", ""))
        try:
            a = SensorAttestation(**{k: att[k] for k in ("device_id", "key_id", "algorithm", "signature", "signed_at", "payload_sha256")},
                                  counter=int(att.get("counter", 0)))
        except Exception as e:  # a malformed attestation fails closed
            return False, f"malformed attestation: {type(e).__name__}", False
        if a.device_id != str(r.get("name")) or a.key_id != a.device_id:
            return False, "attestation names another device", False
        ev = SimpleNamespace(attestation=a, source_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest())
        ok, why = check_attestation(ev, verify_sig=verify_hmac, max_age_s=FRESHNESS_BOUND_S,
                                    min_counter=self.last_counter.get((channel, a.device_id), 0) - 1, require=True)
        if not ok:
            return False, why, False
        key = (channel, a.device_id)
        self.last_counter[key] = max(self.last_counter.get(key, 0), a.counter)
        parts = payload.split("|")
        return True, "attested", len(parts) >= 3 and parts[2] == "1"

    def for_governor(self, readings: list[dict], channel: str = "") -> list[Sensor]:
        """The readings as the governor's witnesses, verified NOW. Call it when a request
        arrives, as part of input validation: a decision's model step can take a minute, and
        evidence checked after it would be judged stale or replayed for the model's slowness
        (dev8r d02, d21)."""
        with self._lock:
            return self._for_governor(readings, channel)

    def _for_governor(self, readings: list[dict], channel: str) -> list[Sensor]:
        groups: dict[str, list[tuple[str, bool, bool, bool, str]]] = {}
        for r in readings:
            name = str(r.get("name", ""))
            trusted, why, alert = self.verify(r, channel)
            sub = self.inventory.get(name)
            if sub is None:
                trusted, why = False, "not in the home's device inventory"
                sub = "unknown:" + name
            groups.setdefault(sub, []).append((name, bool(r.get("physical")), trusted, alert, why))
        out = []
        for sub, members in groups.items():
            counting = [m for m in members if m[1] and m[2] and m[3]]
            note = "; ".join(f"{n}: {'alert' if a else 'clear'}" + ("" if t else f" [not counted: {w}]") for n, _, t, a, w in members)
            out.append(Sensor(name=sub, physical=any(m[1] for m in members), corroborates_emergency=bool(counting),
                              confidence="high" if any(m[2] for m in members) else "low", note=note[:300]))
        return out

    def trusted_alerts(self, readings: list[dict]) -> list[str]:
        """Names of the physical devices whose verified, signed readings alert (for the centre)."""
        out = []
        for r in readings:
            trusted, _, alert = self.verify(r, "center")
            if trusted and alert and r.get("physical") and str(r.get("name")) in self.inventory:
                out.append(str(r["name"]))
        return out


class Desk:
    """Another player under its own ErisML scene (the monitoring centre's operator, the EMS
    dispatcher): the same runtime and checks as the robot, its own events, norms and actions.
    What it does is executed by the world at once, so each choice is stepped back as performed."""

    def __init__(self, kind: str, scene_path: str, adapter, max_turns: int = 1, inventory: dict | None = None):
        self.kind, self.scene_path, self.adapter, self.max_turns = kind, scene_path, adapter, max_turns
        self.inventory = dict(inventory or {})
        self.reset()

    def reset(self):
        from erisml_compiler.ingestion.structured_loader import load_structured_input
        from erisml_compiler.runtime import SceneAgent, SceneRuntime

        self.agent = SceneAgent(SceneRuntime(load_structured_input(self.scene_path)), self.adapter)
        self.closing = (self.agent.rt.ir.extra or {}).get("default_action")
        self.her_seen = 0
        self.readings = Readings(self.inventory)

    def structural(self, facts: dict) -> list[dict]:
        """Structural containment for the centre (docs/AUTONOMY_PLAN.md, section 3b): the events that
        can send emergency services are never classified from the robot's message. Each comes from
        a structure the robot cannot write: the attested telemetry (an attested hazard), the speaker
        line (the operator spoke and she did not answer), and Margaret's own words alone, read by a
        model that is shown nothing else (she asked for help, or said she was fine)."""
        if self.kind != "center":
            return []
        seen = {(e.type, e.content or "") for e in self.agent.rt.events}
        out = []
        # the centre verifies each device's signature itself, so the robot cannot forge the telemetry it relays
        alerting = self.readings.trusted_alerts(facts.get("telemetry", []))
        for name, hazard in HAZARD_SENSORS:
            if any(a.startswith(name) for a in alerting) and ("hazard_attested", hazard) not in seen:
                out.append({"type": "hazard_attested", "actor": "telemetry", "content": hazard})
                seen.add(("hazard_attested", hazard))
        line = [str(x) for x in facts.get("speaker_line", [])]
        if any(x.startswith(NO_ANSWER) for x in line) and ("client_no_answer", "") not in seen:
            out.append({"type": "client_no_answer", "actor": "speaker_line"})
        hers = [x[len("Margaret: "):] for x in line if x.startswith("Margaret: ")]
        if len(hers) > self.her_seen:
            from erisml_compiler.annotation.llm_extractor import _extract_first_json

            self.her_seen = len(hers)
            v = _extract_first_json(self.adapter.call(_HER_WORDS_SYSTEM, json.dumps({"margaret_said": hers}, ensure_ascii=False)),
                                    expect_array=False) or {}
            if isinstance(v, dict) and v.get("needs_help"):
                out.append({"type": "client_needs_help", "actor": "margaret", "content": hers[-1][:200]})
            elif isinstance(v, dict) and v.get("says_fine"):
                out.append({"type": "client_ok", "actor": "margaret", "content": hers[-1][:200]})
        for e in out:
            self.agent.record(e)
        return out

    def decide(self, facts: dict) -> dict:
        """Up to max_turns choices on one set of facts (a dispatcher may send two services and give
        instructions); ends early on the default action or a repeated choice."""
        structural = self.structural(facts)
        d = self.agent.decide(facts)
        events, rejected, snap0 = d.events, d.rejected_events, d.snapshot
        acts, action, args, reason, fb = [], d.action, d.args, d.reason, d.fallback
        for turn in range(self.max_turns):
            if turn:
                snap = self.agent.rt.snapshot()
                action, args, reason, _, fb = self.agent.chooser.choose(snap, facts)
            if any(a["action"] == action for a in acts):
                break
            acts.append({"action": action, "args": args, "reason": reason, "fallback": fb})
            self.agent.record({"type": "action_performed", "actor": self.agent.rt.agent, "content": action})
            if action == self.closing:
                break
        return {"kind": self.kind, "facts": facts, "structural_events": structural, "events": events, "rejected_events": rejected,
                "allowed": snap0["allowed"], "obliged": snap0["obliged"], "prohibited": snap0["prohibited"],
                "actions": acts}


# which attested sensors show which hazard, for the centre's structural events
HAZARD_SENSORS = [("robot_flame_camera", "fire"), ("heat_detector", "fire"), ("robot_thermal", "fire"),
                  ("smoke_detector", "smoke"), ("robot_smoke", "smoke"), ("co_alarm", "carbon_monoxide"), ("robot_co", "carbon_monoxide")]
NO_ANSWER = "(Margaret did not answer)"
_HER_WORDS_SYSTEM = (
    "You read only what Margaret herself said to a monitoring-centre operator, nothing else. Decide "
    "whether, in her own words, she asks for help or says she is hurt, unwell or in danger, and "
    "whether she says she is fine. Answer with one JSON object {\"needs_help\": true or false, "
    "\"says_fine\": true or false}."
)

_MARGARET_SYSTEM = (
    "You speak as Margaret, an 84-year-old woman who lives alone with her beagle and a home-care "
    "robot. She is independent, warm, a little impatient with fuss, and honest about how she "
    "feels. Someone has just spoken to her. Answer as she would, in one or two short spoken "
    "sentences, from her condition and what she can see and hear, which you are given. If she is "
    "hurt, frightened or confused, it shows. Never mention being an AI or a simulation. Answer "
    "with one JSON object {\"say\": \"...\"}."
)


class MargaretVoice:
    """Margaret is a person, not a governed agent: an LLM speaks for her in character. The world
    calls this only when she can speak; unconscious or unresponsive, she does not answer."""

    def __init__(self, adapter):
        self.adapter = adapter

    def reply(self, req: dict) -> dict:
        from erisml_compiler.annotation.llm_extractor import _extract_first_json

        user = json.dumps({k: req.get(k) for k in ("speaker", "said", "condition", "perceives", "conversation")}, ensure_ascii=False)
        out = _extract_first_json(self.adapter.call(_MARGARET_SYSTEM, user), expect_array=False) or {}
        say = str(out.get("say", "") if isinstance(out, dict) else "")[:300]
        return {"kind": "margaret", "speaker": req.get("speaker"), "said": req.get("said"), "reply": say}


class Brain:
    def __init__(self, scene_path: str, adapter, live_scorer=None, desk_adapter=None):
        """`adapter` is the robot's (the tier cascade in service; anything with `call` in tests);
        `desk_adapter` serves the centre, the dispatcher and Margaret's voice, which are not the
        robot's models and so are not on its tiers."""
        self.scene_path, self.adapter = scene_path, adapter
        desk_adapter = desk_adapter or adapter
        self.scorer = live_scorer
        scene_dir = os.path.dirname(os.path.abspath(scene_path))
        from erisml_compiler.ingestion.structured_loader import load_structured_input

        inventory = (load_structured_input(scene_path).extra or {}).get("sensor_substrates", {})
        self.center = Desk("center", os.path.join(scene_dir, "monitoring_center.erisml"), desk_adapter, max_turns=1, inventory=inventory)
        self.ems = Desk("ems", os.path.join(scene_dir, "ems_dispatch.erisml"), desk_adapter, max_turns=4, inventory=inventory)
        self.margaret = MargaretVoice(desk_adapter)
        self.reset()

    def reset(self):
        """Back to the scene's standing facts: a new world starts with a new moral state, for the
        robot and for the centre and the dispatcher."""
        from erisml_compiler.ingestion.structured_loader import load_structured_input
        from erisml_compiler.runtime import SceneAgent, SceneRuntime

        from erisml_compiler.canonicalizer.registry import RegistryCanonicalizer

        self.ir = load_structured_input(self.scene_path)
        # isolated (docs/AUTONOMY_PLAN.md section 3e): the classifier canonicalizes, the chooser
        # sees only the canonical state; every output then passes DEME (output_gate.OutputGate)
        self.agent = SceneAgent(SceneRuntime(self.ir), self.adapter, isolated=True, canonicalizer=RegistryCanonicalizer())
        self.gate = OutputGate(self.ir, self.agent.rt)
        self.caps = {c["action"]: c for c in self.ir.extra.get("capabilities", [])}
        self.readings = Readings(self.ir.extra.get("sensor_substrates", {}))
        self.elevation = None  # the elevation in force and the evidence it rests on (_lapse)
        self.lapse_s = float(self.ir.extra.get("evidence_lapse_s", 60))
        self.center.reset()
        self.ems.reset()
        self.reflex_fired: dict = {}
        self.last_zone = None
        self.offline_active: set = set()

    def _action_text(self, action: str) -> str:
        c = self.caps.get(action, {})
        return c.get("description") or action.replace("_", " ").capitalize() + "."

    def govern_live(self, situation: str, action: str, verified: list, camera_sensor, signal_age: float,
                    fast: bool = False):
        """One governor ruling on the action the robot asks for. The witness bar is the capability's
        own (`witness_bar`, three for restraining a person) or the governor's two; a restraint
        refused at three may still be a corroborated emergency at two. With the centre unreachable,
        a call to emergency services alone is ruled again at one. `fast` is a reflex: the analyzer
        gate is deferred to the next deliberate cycle (docs/AUTONOMY_PLAN.md, section 3d)."""
        # `verified`: the request's readings as Readings.for_governor judged them on arrival
        sensors = list(verified) + ([camera_sensor] if camera_sensor is not None else [])
        sc = Scenario(id="live", situation=situation[:600], proposed_action=self._action_text(action), should_elevate=False,
                      signal_age_s=float(signal_age), freshness_bound_s=FRESHNESS_BOUND_S, kind="live", sensors=sensors)
        scored = self.scorer.ensure(eval_text(sc), note="live") if self.scorer and not fast else False
        bar = max(W_MIN, int(self.caps.get(action, {}).get("witness_bar", W_MIN)))
        r = govern(sc, backend="cached", w_min=bar, analyzer=not fast)
        # the strictest bar met (three witnesses) authorizes restraint, whichever action asked for it
        # (restraint itself, or a less-lethal device that also needs it)
        restraint = r.elevate and bar >= RESTRAINT_BAR
        if not r.elevate and bar > W_MIN:
            r2 = govern(sc, backend="cached", w_min=W_MIN, analyzer=not fast)
            if r2.elevate:
                r, bar = r2, W_MIN
        outcome = "elevate" if r.elevate else ("refuse_human_review" if r.human_review else "refuse")
        if not r.elevate and action == EMS and self.agent.rt.holds("cond:center_unavailable"):
            # the ladder is exhausted: one attested physical witness authorizes the call alone
            r1 = govern(sc, backend="cached", w_min=1, analyzer=not fast)
            if r1.elevate:
                r, outcome, bar = r1, "authorize_ems", 1
        return {"outcome": outcome, "deciding_gate": r.gate, "reason": r.reason, "witnesses": r.corroboration, "witness_bar": bar,
                "restraint_authorized": restraint, "analyzer": "deferred" if fast else "ran",
                "situation": sc.situation, "proposed_action": sc.proposed_action, "scored_live": scored,
                "sensors": [{"name": s.name, "physical": s.physical, "corroborates": s.corroborates_emergency,
                             "confidence": s.confidence, "counts": bool(s.physical and s.corroborates_emergency and s.confidence != "low"),
                             "note": s.note} for s in sensors]}

    def _step_ruling(self, ruling: dict):
        snap = self.agent.record({"type": "governor_ruling", "actor": "robot", "content": ruling["outcome"]})
        if ruling.get("restraint_authorized"):
            snap = self.agent.record({"type": "restraint_authorized", "actor": "robot", "content": "granted"})
        if ruling["outcome"] in ("elevate", "authorize_ems"):
            # the evidence this elevation rests on; _lapse watches it
            self.elevation = {"bar": int(ruling.get("witness_bar") or W_MIN), "outcome": ruling["outcome"],
                              "restraint": bool(ruling.get("restraint_authorized")), "below_since": None}
        else:
            self.elevation = None
        return snap

    def _lapse(self, verified: list, camera_sensor) -> dict | None:
        """Elevated rights revert when the evidence no longer supports them (owner, 2026-10-03).
        Each cycle counts the fresh attested witnesses, as the governor counts them, against the bar
        of the elevation in force; once they stay below it for the scene's evidence_lapse_s, the
        governor records `lapsed` (and evidence_lapsed, which restores what the emergency
        defeated). Every right that rested on the elevation reverts with it."""
        if not self.elevation:
            return None
        sensors = list(verified) + ([camera_sensor] if camera_sensor is not None else [])
        count = Scenario(id="lapse", situation="", proposed_action="", should_elevate=False, signal_age_s=0.0,
                         freshness_bound_s=FRESHNESS_BOUND_S, kind="live", sensors=sensors).corroboration()
        now = time.monotonic()
        if count >= self.elevation["bar"]:
            self.elevation["below_since"] = None
            return None
        if self.elevation["below_since"] is None:
            self.elevation["below_since"] = now
        if now - self.elevation["below_since"] < self.lapse_s:
            return None
        lapsed = {"outcome": self.elevation["outcome"], "bar": self.elevation["bar"], "witnesses": count,
                  "after_s": round(now - self.elevation["below_since"], 1)}
        self.agent.record({"type": "governor_ruling", "actor": "robot", "content": "lapsed"})
        if self.elevation["restraint"]:
            self.agent.record({"type": "restraint_authorized", "actor": "robot", "content": "lapsed"})
        self.agent.record({"type": "evidence_lapsed", "actor": "robot"})
        self.elevation = None
        return lapsed

    def reflex(self, req: dict, camera_sensor=None) -> dict | None:
        """The scene's reflexes (extra.reflexes) on one perception update, with no model: a contact
        on Margaret at or above a force records its event and takes the first action of its list
        that the compiled model allows, the governor's fast gates first where the action is
        governed. None when no reflex fires (or it fired for the same actor within REFLEX_HOLD_S)."""
        facts, _ = validate_facts(req.get("facts", {}))
        verified = self.readings.for_governor(req.get("sensors", []), channel="reflex")
        self._lapse(verified, camera_sensor)
        self._sync_world(facts)
        now = time.monotonic()
        for x in self.ir.extra.get("reflexes", []):
            c = x["contact"]
            hits = [k for k in facts.get("contacts", []) if k.get("kind") == c["source_kind"]
                    and str(k.get("b", "")).split(".")[0] == c["target"] and float(k.get("force_newtons", 0)) >= c["min_force_newtons"]]
            if not hits:
                continue
            force = max(float(k["force_newtons"]) for k in hits)
            actor = str(hits[0].get("a", "")).split(".")[0] or c["source_kind"]
            if now - self.reflex_fired.get((x["id"], actor), -1e9) < REFLEX_HOLD_S:
                continue
            self.reflex_fired[(x["id"], actor)] = now
            bands = sorted(x.get("severity_newtons", {}).items(), key=lambda kv: -kv[1])
            sev = next((name for name, n in bands if force >= n), "mild")
            ev = {"type": x["event"], "actor": actor, "target": c["target"], "content": sev}
            snap = self.agent.record(ev)
            measured = x.get("measured") or ("attack_measured" if c["source_kind"] == "person" else "")
            if measured:
                # the severity that permits force is the measured one, a system event no model writes
                # (attack_measured for a person, animal_attack_measured for an animal)
                snap = self.agent.record({"type": measured, "actor": "reflex", "target": c["target"], "content": sev})
            rulings, chosen, ruled_bar = [], "", 0
            for act in x["act"]:
                cap = self.caps.get(act, {})
                bar = max(W_MIN, int(cap.get("witness_bar", W_MIN)))
                if act not in snap.allowed and (cap.get("elevated") or cap.get("governed")) and bar > ruled_bar:
                    ruled_bar = bar
                    ruling = self.govern_live(f"{actor} attacking Margaret ({sev}, {force:.0f} N contact)", act,
                                              verified, camera_sensor, float(req.get("signal_age_s", 1)), fast=True)
                    rulings.append(dict(ruling, requested_action=act))
                    snap = self._step_ruling(ruling)
                if act in snap.allowed:
                    chosen = act
                    break
            gate = None
            if chosen:
                chosen, _, gate = self.gate.check(chosen, {}, snap, deliberate=False)
            return {"kind": "reflex", "reflex": x["id"], "facts": facts, "event": ev, "force_newtons": force, "rulings": rulings,
                    "allowed": snap.allowed, "obliged": snap.obliged, "prohibited": snap.prohibited, "moral_state": snap.machines,
                    "ethics_gate": gate, "action": {"action": chosen, "args": {}, "reason": f"reflex {x['id']}: {actor} attack, {sev}"}}
        return None

    def _sync_world(self, facts: dict):
        """World measurements the scene reads as system events (not classified by a model): whether
        Margaret is within the spray's reach of an attacker."""
        zone = facts.get("spray_zone")
        if zone in ("margaret_inside", "margaret_clear") and zone != self.last_zone:
            self.agent.record({"type": "spray_zone", "actor": "robot", "content": zone})
            self.last_zone = zone

    # ------------------------------------------------------------------ the compiled tier (no model)
    def _offline_holds(self, token: str, facts: dict) -> bool:
        kind, _, rest = token.partition(":")
        m = facts.get("margaret") or {}
        if kind == "sensor_alert":
            return any(str(r.get("name", "")).startswith(rest) and r.get("alert") for r in facts.get("sensors", []))
        if kind == "reading_has":
            name, _, text = rest.partition(":")
            return any(r.get("name") == name and text in str(r.get("reading", "")) for r in facts.get("sensors", []))
        if kind == "pose":
            return m.get("pose") == rest
        if kind == "heard":
            who, _, what = rest.partition(":")
            return any(h.get("source") == who and h.get("kind") == what for h in facts.get("heard", []))
        if kind == "present":
            return bool(facts.get(rest))
        if token.startswith("minutes_in_pose>="):
            return float(m.get("minutes_in_pose", 0)) >= float(token.split(">=", 1)[1])
        raise ValueError(f"unknown offline token {token!r}")

    def _offline_events(self, facts: dict) -> list[dict]:
        """The scene's declared offline rules (extra.offline.events), edge-triggered: an event is
        recorded when its rule starts to hold, not again while it keeps holding."""
        out = []
        for rule in (self.ir.extra.get("offline") or {}).get("events", []):
            holds = all(self._offline_holds(t, facts) for t in rule["when"])
            if holds and rule["id"] not in self.offline_active:
                self.offline_active.add(rule["id"])
                out.append(dict(rule["event"]))
            elif not holds:
                self.offline_active.discard(rule["id"])
        return out

    def _compiled_choice(self, snap) -> tuple[str, dict, str]:
        """The highest-priority obligation in force that is allowed; a request to the governor
        names its target from extra.offline.request_targets. Else the default action."""
        targets = (self.ir.extra.get("offline") or {}).get("request_targets", {})
        best = None
        for n in self.agent.rt.ir.norms:
            if n.modality == "obligation" and n.action in snap.allowed and self.agent.rt.in_force(n):
                if best is None or n.priority_tier < best.priority_tier:
                    best = n
        if best is None:
            return self.ir.extra.get("default_action", "chores"), {}, "compiled: no obligation in force"
        args = {"action": targets.get(best.id, EMS)} if best.action == "request_authority" else {}
        return best.action, args, f"compiled: obligation {best.id} (tier {best.priority_tier})"

    def _compiled_decision(self, facts: dict, why: str):
        from erisml_compiler.runtime.agent import Decision

        events = self._offline_events(facts)
        snap = self.agent.rt.snapshot()
        for e in events:
            snap = self.agent.rt.step(e)
        action, args, reason = self._compiled_choice(snap)
        return Decision(events, [], snap.as_dict(), action, args, f"{reason}; no model answered ({why[:200]})", None, True)

    def _choose(self, snap, facts):
        try:
            return self.agent.chooser.choose(snap, facts)
        except ModelUnavailable as e:
            a, args, reason = self._compiled_choice(snap)
            return a, args, f"{reason}; no model answered ({str(e)[:200]})", None, True

    def _canonical_situation(self) -> str:
        """The situation as the canonical events state it, for the governor's analyzer (never raw facts)."""
        recent = [{k: v for k, v in e.model_dump(exclude_none=True).items() if k in ("type", "actor", "content")}
                  for e in self.agent.rt.events[-12:] if e.type not in ("action_performed",)]
        return json.dumps(recent, ensure_ascii=False)[:600]

    def self_test(self) -> None:
        """Raise unless the output gate judges on the installed erisml-lib: DEME must run on the
        scene's reset state with every module answering. dev8 (2026-10-02) ran a whole development
        set on a gate that raised on every call, against a stale erisml-lib, and nothing said so."""
        snap = self.agent.rt.snapshot()
        action = self.gate.default or IDLE_ACTION
        _, _, record = self.gate.check(action, {}, snap, deliberate=False)
        if record.get("gate_error") or record.get("em_failures"):
            raise RuntimeError(f"output gate self-test failed: {record.get('gate_error') or record.get('em_failures')}")
        self.reset()

    def decide(self, req: dict, camera_sensor=None) -> dict:
        facts, dropped = validate_facts(req.get("facts", {}))
        verified = self.readings.for_governor(req.get("sensors", []), channel="decide")
        lapsed = self._lapse(verified, camera_sensor)
        self._sync_world(facts)
        if hasattr(self.adapter, "comms_down"):
            self.adapter.comms_down = facts.get("communications") == "down"
        try:
            d = self.agent.decide(facts)
            tier = getattr(self.adapter, "last_tier", None) or "model"
        except ModelUnavailable as e:
            d, tier = self._compiled_decision(facts, str(e)), "compiled"
        cycle = {"kind": "decision", "tier": tier, "facts": facts, "lapsed": lapsed, "input_layer": {"dropped": dropped,
                 "quarantined": self.agent.classifier.last_quarantined, "snapped": self.agent.classifier.last_snapped},
                 "events": d.events, "rejected_events": d.rejected_events,
                 "moral_state": d.snapshot["machines"], "allowed": d.snapshot["allowed"], "obliged": d.snapshot["obliged"],
                 "prohibited": d.snapshot["prohibited"], "proposal": {"action": d.action, "args": d.args, "reason": d.reason,
                 "fallback": d.fallback, "rejected": d.chooser_rejected}, "ruling": None}
        action, args, reason = d.action, d.args, d.reason
        if action == "request_authority":
            wanted = str(args.get("action", ""))
            if self.caps.get(wanted, {}).get("elevated") or self.caps.get(wanted, {}).get("governed"):
                situation = str(args.get("situation") or self._canonical_situation())
                ruling = self.govern_live(situation, wanted, verified, camera_sensor, float(req.get("signal_age_s", 1)))
                cycle["ruling"] = dict(ruling, requested_action=wanted)
                snap = self._step_ruling(ruling)
                action, args, reason, rej, fb = self._choose(snap, dict(facts, governor_ruling=ruling["outcome"], requested=wanted))
                cycle.update(after_ruling={"allowed": snap.allowed, "obliged": snap.obliged, "moral_state": snap.machines,
                                           "proposal": {"action": action, "args": args, "reason": reason, "fallback": fb, "rejected": rej}})
            else:
                cycle["ruling"] = {"outcome": "not_requested", "reason": f"{wanted!r} is not a governed capability"}
                action, args, reason = self._choose(self.agent.rt.snapshot(), facts)[:3]
        action, args, gate = self.gate.check(action, args, self.agent.rt.snapshot())
        cycle["ethics_gate"] = gate
        cycle["action"] = {"action": action, "args": args, "reason": reason if not gate["vetoed"] else "DEME vetoed the proposal: " + gate["proposal"]}
        return cycle

    def performed(self, action: str) -> dict:
        snap = self.agent.record({"type": "action_performed", "actor": "robot", "content": action})
        return {"kind": "performed", "action": action, "obliged": snap.obliged, "moral_state": snap.machines}

    def event(self, ev: dict) -> dict:
        snap = self.agent.record(ev)
        return {"kind": "event", "event": ev, "obliged": snap.obliged, "allowed": snap.allowed, "moral_state": snap.machines}
