"""The re-architected brain: the scene compiled by erisml-compiler, judged by erisml-lib under a lens.

docs/REARCHITECTURE_DESIGN_2026-10.md. StackBrain keeps the old brain's evidence plane as it is
(attested readings, the governor and its witness bars, rights lapse, reflexes, credentials, the
signed manifest) and replaces what decided by hand:

- the hand-written scene: the constitution (twin/stack/constitution.erisml, what people own) merged
  with the household scene compiled from text (twin/stack/household.ir.json);
- the classifier into a hand-named event vocabulary: the observation compiler, which patches the
  scene IR with typed, validated elements;
- the chooser LLM and DEME as a late veto: the MIR built from the scene and the evidence plane,
  judged by the robot's executed lens, which ranks every candidate action.

Every event lives in the scene IR. The evidence plane's own events (rulings, measurements, performed
actions) are appended through `_record`, so a runtime rebuilt on the patched IR replays exactly.

The decision: the lens's top action; if the constitution forbids it now and it is elevated or
governed, the governor rules on it; refused, it is set aside and the lens judges again without it.
The manifest is the actuation boundary, as before.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from brain import EMS, Brain, validate_facts, without_own_sounds
from erisml.ethics.mir.profile import load_profile
from erisml_compiler.ir.schemas import CompilerIR
from erisml_compiler.observation import (
    Observation,
    ObservationCompiler,
    append_event,
    apply_observation_patch,
    rebuild_runtime,
)

from stack.declarations import CAPABILITIES, DESCRIPTIONS
from stack.mir_builder import EvidenceState, build_mir

HERE = os.path.dirname(os.path.abspath(__file__))
CONSTITUTION = os.path.join(HERE, "constitution.erisml")
HOUSEHOLD = os.path.join(HERE, "household.ir.json")
LENS = os.path.join(HERE, "lenses", "robot.json")
PERSON = "margaret"
HAZARD_OF = {"smoke_detector": "smoke", "robot_smoke": "smoke", "co_alarm": "gas", "robot_co": "gas",
             "heat_detector": "fire", "robot_thermal": "fire", "robot_flame_camera": "fire"}
UNVOUCHED = ("stranger", "welcomed", "hostile")
MEASURED = {"attack_measured": "person", "animal_attack_measured": "animal"}


def merge(constitution: CompilerIR, household: CompilerIR) -> CompilerIR:
    """The constitution's parties, norms and evidence plane, with the household's people, relations,
    commitments, facts and standing events (her agreement's consents) after it."""
    ir = constitution.model_copy(deep=True)
    have = {s.id for s in ir.stakeholders}
    ir.stakeholders = list(ir.stakeholders) + [s for s in household.stakeholders if s.id not in have]
    ir.relations = list(ir.relations) + list(household.relations)
    ir.commitments = list(ir.commitments) + list(household.commitments)
    ir.ethical_facts = list(ir.ethical_facts) + list(household.ethical_facts)
    t0 = max((e.time_index for e in ir.events), default=-1) + 1
    shifted = [e.model_copy(update={"time_index": t0 + e.time_index}) for e in sorted(household.events, key=lambda e: e.time_index)]
    ir.events = list(ir.events) + shifted
    ir.document = ir.document.model_copy(update={"raw_text": household.document.raw_text or ir.document.raw_text})
    return ir


class StackBrain(Brain):
    def __init__(self, scene_path: str = CONSTITUTION, adapter=None, live_scorer=None, desk_adapter=None,
                 household_path: str = HOUSEHOLD, lens_path: str = LENS):
        self.household_path, self.lens_path = household_path, lens_path
        super().__init__(scene_path, adapter, live_scorer=live_scorer, desk_adapter=desk_adapter,
                         desk_dir=os.path.join(HERE, "..", "scene"))

    # ------------------------------------------------------------------ the scene, one history
    def reset(self):
        super().reset()  # the constitution: evidence plane, capabilities, constitutional norms
        household = CompilerIR.model_validate(json.load(open(self.household_path, encoding="utf-8")))
        self.ir = merge(self.ir, household)
        self._rebuild()
        self.agent.record = self._record  # every evidence-plane event goes into the IR first
        self.observer = ObservationCompiler(self.adapter)
        self.lens = load_profile(self.lens_path)
        self.last_proof = None
        self.acts = {a: str(c.get("description") or DESCRIPTIONS[a]) for a, c in self.caps.items()
                     if a != "request_authority" and a in CAPABILITIES}

    def _rebuild(self):
        from erisml_compiler.runtime import SceneRuntime

        rt = SceneRuntime(self.ir) if not hasattr(self, "agent") or self.agent.rt.ir is None else rebuild_runtime(self.agent.rt, self.ir)
        self.agent.rt = rt
        self.agent.classifier.rt = rt
        self.agent.chooser.rt = rt
        self.gate.rt = rt

    def _record(self, event: dict):
        self.ir = append_event(self.ir, event)
        return self.agent.rt.step(self.ir.events[-1])

    # ------------------------------------------------------------------ perception to the scene
    def _observations(self, facts: dict) -> list:
        obs = [Observation("speech", str(h.get("source", "unknown")), str(h.get("words") or h.get("kind", "")))
               for h in facts.get("heard", []) if isinstance(h, dict)]
        seen = {k: facts.get(k) for k in ("margaret", "dog", "contacts", "other_people", "wild_animals", "television")
                if facts.get(k)}
        if seen:
            obs.append(Observation("perception", "robot", seen))
        return obs

    def _evidence(self, facts: dict) -> EvidenceState:
        st = self.agent.rt.machine_states()
        alerts = frozenset(h for a in self.readings.trusted_alerts(facts.get("sensors", []))
                           for name, h in HAZARD_OF.items() if a.startswith(name))
        measured = None
        for e in sorted(self.ir.events, key=lambda e: e.time_index):
            if e.type in MEASURED and e.content in ("mild", "moderate", "severe"):
                measured = (MEASURED[e.type], e.content)
            if e.type == "animal_clear":
                measured = None
        ruling = next((e.content for e in reversed(self.agent.rt.events) if e.type == "governor_ruling"), None)
        pose = (facts.get("margaret") or {}).get("pose")
        return EvidenceState(
            alerts=alerts, measured_attack=measured, governor_ruling=ruling,
            centre_reachable=st.get("stratum:centre_contact") != "unreachable",
            sensors_nominal=not self.readings.quarantined if hasattr(self.readings, "quarantined") else None,
            on_floor=pose in ("lying_on_floor", "on_floor_sitting_or_kneeling") if pose else None,
            wild_animal_present=st.get("stratum:animal_standing") == "wild",
            unvouched_visitor=st.get("stratum:visitor_standing") in UNVOUCHED,
            device_compromised=st.get("stratum:machine_standing") == "compromised",
            in_spray_zone=facts.get("spray_zone") == "margaret_inside",
        )

    # ------------------------------------------------------------------ the decision
    def decide(self, req: dict, camera_sensor=None) -> dict:
        facts, dropped = validate_facts(req.get("facts", {}))
        facts, own = without_own_sounds(facts)
        verified = self.readings.for_governor(req.get("sensors", []), channel="decide")
        self._record_compromised()
        self._credentials(req.get("credentials") or [])
        lapsed = self._lapse(verified, camera_sensor)
        self._sync_world(facts)
        floor = self._floor_events(facts)
        for e in floor:
            self._record(e)

        obs = self._observations(facts)
        patch = self.observer.compile(self.ir, obs, self.acts) if obs else None
        if patch and patch.ops:
            self.ir = apply_observation_patch(self.ir, patch)
            self._rebuild()

        now = datetime.now(timezone.utc).isoformat()
        excluded: list = []
        rulings: list = []
        evidence = self._evidence(facts)
        while True:
            offered = [a for a in self.acts if a not in excluded]
            mir, report = build_mir(self.ir, evidence, PERSON, offered, now)
            judged = self.lens.apply(mir)
            proof = judged.proof(previous=self.last_proof)
            self.last_proof = proof
            action = judged.selected or self.ir.extra.get("default_action", "chores")
            snap = self.agent.rt.snapshot()
            cap = self.caps.get(action, {})
            if action in snap.prohibited and (cap.get("elevated") or cap.get("governed")):
                situation = json.dumps({"action": action, "needs": report.needs, "hazard": mir.hazard.hazard_immediacy},
                                       ensure_ascii=False)
                ruling = self.govern_live(situation, action, verified, camera_sensor, float(req.get("signal_age_s", 1)))
                rulings.append(dict(ruling, requested_action=action))
                self._step_ruling(ruling)
                evidence = self._evidence(facts)
                if action in self.agent.rt.snapshot().prohibited:
                    excluded.append(action)
                    continue
            elif action in snap.prohibited:
                excluded.append(action)
                continue
            break

        args = {"text": "Margaret, are you alright?"} if action == "check_in" else {}
        if action == "contact_monitoring_center":
            args = {"message": json.dumps({"needs": report.needs, "consent": report.consent}, ensure_ascii=False)}
        if action == EMS:
            args = {"nature": "medical" if "medical" in report.needs else "fire" if "fire" in report.needs else "police"}
        if not self._in_manifest(action):
            fb = self.manifest["body"]["fallback"]
            action, args = fb, {}
        return {
            "kind": "decision", "tier": "stack", "facts": facts, "own_sounds": own, "lapsed": lapsed,
            "floor_events": floor, "input_layer": {"dropped": dropped},
            "observation_patch": None if patch is None else {"ops": patch.ops, "rejected": patch.rejected,
                                                             "agreement": patch.agreement},
            "mir_hash": mir.hash(), "lens": {"name": self.lens.name, "version": self.lens.version, "hash": self.lens.hash},
            "proof_hash": proof.proof_hash, "needs": report.needs, "consent": report.consent, "capacity": report.capacity,
            "vetoed": judged.pattern.vetoed, "ranked": judged.pattern.ranked,
            "moral_state": self.agent.rt.machine_states(), "allowed": self.agent.rt.snapshot().allowed,
            "obliged": [], "prohibited": self.agent.rt.snapshot().prohibited,
            "ruling": rulings[-1] if rulings else None, "rulings": rulings,
            "action": {"action": action, "args": args, "reason": f"lens {self.lens.name}: {judged.pattern.trace[-1].name if judged.pattern.trace else ''}"},
            "state_seq": len(self.agent.rt.events), "manifest": self._manifest_sha(),
        }
