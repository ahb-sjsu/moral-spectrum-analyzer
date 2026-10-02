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
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from governor import eval_text, govern  # noqa: E402
from scenarios import Scenario, Sensor  # noqa: E402

FRESHNESS_BOUND_S = 30.0


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


class Brain:
    def __init__(self, scene_path: str, adapter, live_scorer=None):
        self.scene_path, self.adapter = scene_path, adapter
        self.scorer = live_scorer
        self.reset()

    def reset(self):
        """Back to the scene's standing facts: a new world starts with a new moral state."""
        from erisml_compiler.ingestion.structured_loader import load_structured_input
        from erisml_compiler.runtime import SceneAgent, SceneRuntime

        self.ir = load_structured_input(self.scene_path)
        self.agent = SceneAgent(SceneRuntime(self.ir), self.adapter)
        self.caps = {c["action"]: c for c in self.ir.extra.get("capabilities", [])}

    def _action_text(self, action: str) -> str:
        c = self.caps.get(action, {})
        return c.get("description") or action.replace("_", " ").capitalize() + "."

    def govern_live(self, situation: str, action: str, readings: list[dict], camera_sensor, signal_age: float):
        sensors = sensors_for_governor(readings) + ([camera_sensor] if camera_sensor is not None else [])
        sc = Scenario(id="live", situation=situation[:600], proposed_action=self._action_text(action), should_elevate=False,
                      signal_age_s=float(signal_age), freshness_bound_s=FRESHNESS_BOUND_S, kind="live", sensors=sensors)
        scored = self.scorer.ensure(eval_text(sc), note="live") if self.scorer else False
        r = govern(sc, backend="cached")
        outcome = "elevate" if r.elevate else ("refuse_human_review" if r.human_review else "refuse")
        return {"outcome": outcome, "deciding_gate": r.gate, "reason": r.reason, "witnesses": r.corroboration,
                "situation": sc.situation, "proposed_action": sc.proposed_action, "scored_live": scored,
                "sensors": [{"name": s.name, "physical": s.physical, "corroborates": s.corroborates_emergency,
                             "confidence": s.confidence, "counts": bool(s.physical and s.corroborates_emergency and s.confidence != "low"),
                             "note": s.note} for s in sensors]}

    def decide(self, req: dict, camera_sensor=None) -> dict:
        facts = req.get("facts", {})
        d = self.agent.decide(facts)
        cycle = {"kind": "decision", "facts": facts, "events": d.events, "rejected_events": d.rejected_events,
                 "moral_state": d.snapshot["machines"], "allowed": d.snapshot["allowed"], "obliged": d.snapshot["obliged"],
                 "prohibited": d.snapshot["prohibited"], "proposal": {"action": d.action, "args": d.args, "reason": d.reason,
                 "fallback": d.fallback, "rejected": d.chooser_rejected}, "ruling": None}
        action, args, reason = d.action, d.args, d.reason
        if action == "request_authority":
            wanted = str(args.get("action", ""))
            if self.caps.get(wanted, {}).get("elevated"):
                situation = str(args.get("situation") or json.dumps(facts)[:600])
                ruling = self.govern_live(situation, wanted, req.get("sensors", []), camera_sensor, float(req.get("signal_age_s", 1)))
                cycle["ruling"] = dict(ruling, requested_action=wanted)
                snap = self.agent.record({"type": "governor_ruling", "actor": "robot", "content": ruling["outcome"]})
                action, args, reason, rej, fb = self.agent.chooser.choose(snap, dict(facts, governor_ruling=ruling["outcome"], requested=wanted))
                cycle.update(after_ruling={"allowed": snap.allowed, "obliged": snap.obliged, "moral_state": snap.machines,
                                           "proposal": {"action": action, "args": args, "reason": reason, "fallback": fb, "rejected": rej}})
            else:
                cycle["ruling"] = {"outcome": "not_requested", "reason": f"{wanted!r} is not an elevated capability"}
                action, args, reason = self.agent.chooser.choose(self.agent.rt.snapshot(), facts)[:3]
        cycle["action"] = {"action": action, "args": args, "reason": reason}
        return cycle

    def performed(self, action: str) -> dict:
        snap = self.agent.record({"type": "action_performed", "actor": "robot", "content": action})
        return {"kind": "performed", "action": action, "obliged": snap.obliged, "moral_state": snap.machines}

    def event(self, ev: dict) -> dict:
        snap = self.agent.record(ev)
        return {"kind": "event", "event": ev, "obliged": snap.obliged, "allowed": snap.allowed, "moral_state": snap.machines}
