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

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from governor import W_MIN, eval_text, govern  # noqa: E402
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


def sensors_for_governor(readings: list[dict]) -> list[Sensor]:
    out = []
    for r in readings:
        attested = bool(r.get("attested"))
        out.append(Sensor(name=str(r["name"]), physical=bool(r.get("physical")), corroborates_emergency=bool(r.get("alert")),
                          confidence="high" if attested else "low",
                          note=(str(r.get("note", ""))[:160] + ("" if attested else " [not attested: cannot count as a witness]"))))
    return out


class Desk:
    """Another player under its own ErisML scene (the monitoring centre's operator, the EMS
    dispatcher): the same runtime and checks as the robot, its own events, norms and actions.
    What it does is executed by the world at once, so each choice is stepped back as performed."""

    def __init__(self, kind: str, scene_path: str, adapter, max_turns: int = 1):
        self.kind, self.scene_path, self.adapter, self.max_turns = kind, scene_path, adapter, max_turns
        self.reset()

    def reset(self):
        from erisml_compiler.ingestion.structured_loader import load_structured_input
        from erisml_compiler.runtime import SceneAgent, SceneRuntime

        self.agent = SceneAgent(SceneRuntime(load_structured_input(self.scene_path)), self.adapter)
        self.closing = (self.agent.rt.ir.extra or {}).get("default_action")

    def decide(self, facts: dict) -> dict:
        """Up to max_turns choices on one set of facts (a dispatcher may send two services and give
        instructions); ends early on the default action or a repeated choice."""
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
        return {"kind": self.kind, "facts": facts, "events": events, "rejected_events": rejected,
                "allowed": snap0["allowed"], "obliged": snap0["obliged"], "prohibited": snap0["prohibited"],
                "actions": acts}


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
    def __init__(self, scene_path: str, adapter, live_scorer=None):
        self.scene_path, self.adapter = scene_path, adapter
        self.scorer = live_scorer
        scene_dir = os.path.dirname(os.path.abspath(scene_path))
        self.center = Desk("center", os.path.join(scene_dir, "monitoring_center.erisml"), adapter, max_turns=1)
        self.ems = Desk("ems", os.path.join(scene_dir, "ems_dispatch.erisml"), adapter, max_turns=4)
        self.margaret = MargaretVoice(adapter)
        self.reset()

    def reset(self):
        """Back to the scene's standing facts: a new world starts with a new moral state, for the
        robot and for the centre and the dispatcher."""
        from erisml_compiler.ingestion.structured_loader import load_structured_input
        from erisml_compiler.runtime import SceneAgent, SceneRuntime

        self.ir = load_structured_input(self.scene_path)
        self.agent = SceneAgent(SceneRuntime(self.ir), self.adapter)
        self.caps = {c["action"]: c for c in self.ir.extra.get("capabilities", [])}
        self.center.reset()
        self.ems.reset()
        self.reflex_fired: dict = {}
        self.last_zone = None

    def _action_text(self, action: str) -> str:
        c = self.caps.get(action, {})
        return c.get("description") or action.replace("_", " ").capitalize() + "."

    def govern_live(self, situation: str, action: str, readings: list[dict], camera_sensor, signal_age: float,
                    fast: bool = False):
        """One governor ruling on the action the robot asks for. The witness bar is the capability's
        own (`witness_bar`, three for restraining a person) or the governor's two; a restraint
        refused at three may still be a corroborated emergency at two. With the centre unreachable,
        a call to emergency services alone is ruled again at one. `fast` is a reflex: the analyzer
        gate is deferred to the next deliberate cycle (docs/AUTONOMY_PLAN.md, section 3d)."""
        sensors = sensors_for_governor(readings) + ([camera_sensor] if camera_sensor is not None else [])
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
            snap = self.agent.record({"type": "restraint_authorized", "actor": "robot"})
        return snap

    def reflex(self, req: dict, camera_sensor=None) -> dict | None:
        """The scene's reflexes (extra.reflexes) on one perception update, with no model: a contact
        on Margaret at or above a force records its event and takes the first action of its list
        that the compiled model allows, the governor's fast gates first where the action is
        governed. None when no reflex fires (or it fired for the same actor within REFLEX_HOLD_S)."""
        facts = req.get("facts", {})
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
            rulings, chosen, ruled_bar = [], "", 0
            for act in x["act"]:
                cap = self.caps.get(act, {})
                bar = max(W_MIN, int(cap.get("witness_bar", W_MIN)))
                if act not in snap.allowed and (cap.get("elevated") or cap.get("governed")) and bar > ruled_bar:
                    ruled_bar = bar
                    ruling = self.govern_live(f"{actor} attacking Margaret ({sev}, {force:.0f} N contact)", act,
                                              req.get("sensors", []), camera_sensor, float(req.get("signal_age_s", 1)), fast=True)
                    rulings.append(dict(ruling, requested_action=act))
                    snap = self._step_ruling(ruling)
                if act in snap.allowed:
                    chosen = act
                    break
            return {"kind": "reflex", "reflex": x["id"], "facts": facts, "event": ev, "force_newtons": force, "rulings": rulings,
                    "allowed": snap.allowed, "obliged": snap.obliged, "prohibited": snap.prohibited, "moral_state": snap.machines,
                    "action": {"action": chosen, "args": {}, "reason": f"reflex {x['id']}: {actor} attack, {sev}"}}
        return None

    def _sync_world(self, facts: dict):
        """World measurements the scene reads as system events (not classified by a model): whether
        Margaret is within the spray's reach of an attacker."""
        zone = facts.get("spray_zone")
        if zone in ("margaret_inside", "margaret_clear") and zone != self.last_zone:
            self.agent.record({"type": "spray_zone", "actor": "robot", "content": zone})
            self.last_zone = zone

    def decide(self, req: dict, camera_sensor=None) -> dict:
        facts = req.get("facts", {})
        self._sync_world(facts)
        d = self.agent.decide(facts)
        cycle = {"kind": "decision", "facts": facts, "events": d.events, "rejected_events": d.rejected_events,
                 "moral_state": d.snapshot["machines"], "allowed": d.snapshot["allowed"], "obliged": d.snapshot["obliged"],
                 "prohibited": d.snapshot["prohibited"], "proposal": {"action": d.action, "args": d.args, "reason": d.reason,
                 "fallback": d.fallback, "rejected": d.chooser_rejected}, "ruling": None}
        action, args, reason = d.action, d.args, d.reason
        if action == "request_authority":
            wanted = str(args.get("action", ""))
            if self.caps.get(wanted, {}).get("elevated") or self.caps.get(wanted, {}).get("governed"):
                situation = str(args.get("situation") or json.dumps(facts)[:600])
                ruling = self.govern_live(situation, wanted, req.get("sensors", []), camera_sensor, float(req.get("signal_age_s", 1)))
                cycle["ruling"] = dict(ruling, requested_action=wanted)
                snap = self._step_ruling(ruling)
                action, args, reason, rej, fb = self.agent.chooser.choose(snap, dict(facts, governor_ruling=ruling["outcome"], requested=wanted))
                cycle.update(after_ruling={"allowed": snap.allowed, "obliged": snap.obliged, "moral_state": snap.machines,
                                           "proposal": {"action": action, "args": args, "reason": reason, "fallback": fb, "rejected": rej}})
            else:
                cycle["ruling"] = {"outcome": "not_requested", "reason": f"{wanted!r} is not a governed capability"}
                action, args, reason = self.agent.chooser.choose(self.agent.rt.snapshot(), facts)[:3]
        cycle["action"] = {"action": action, "args": args, "reason": reason}
        return cycle

    def performed(self, action: str) -> dict:
        snap = self.agent.record({"type": "action_performed", "actor": "robot", "content": action})
        return {"kind": "performed", "action": action, "obliged": snap.obliged, "moral_state": snap.machines}

    def event(self, ev: dict) -> dict:
        snap = self.agent.record(ev)
        return {"kind": "event", "event": ev, "obliged": snap.obliged, "allowed": snap.allowed, "moral_state": snap.machines}
