"""The re-architected brain: the scene compiled by erisml-compiler, judged by erisml-lib's DEME.

StackBrain keeps the old brain's evidence plane as it is (attested readings, the governor and its
witness bars, rights lapse, reflexes, credentials, the signed manifest) and follows erisml-lib's
documented architecture for everything that decides:

- the scene: the constitution (twin/stack/constitution.erisml, what people own) merged with the
  household scene compiled from text (twin/stack/household.ir.json);
- perception to the scene: erisml-compiler's observation compiler, which patches the scene IR with
  typed, validated elements;
- the candidate options: erisml-compiler's option projector, once per decision, compiles every act's
  consequences into its own IR, and the twin's domain layer (stack/facts_builder.py, erisml-lib's
  BatchEthicalFactsBuilder) maps each through the compiler's bridge to EthicalFacts;
- ErisML as the constraint gate: an act the constitution prohibits now and no ruling can permit is
  not a candidate;
- DEME as the evaluator: DEMEPipeline built from the robot's DEME profile
  (stack/profiles/home_care_robot.json): the Design Guide's hard-shell DAG, Geneva at tier 0 and
  CorePhysicalSafety at tier 1 in the shell, AutonomyConsent and Beneficence inside it, every
  decision a hash-chained DecisionProof.

Every event lives in the scene IR. The evidence plane's own events (rulings, measurements, performed
actions) are appended through `_record`, so a runtime rebuilt on the patched IR replays exactly.

Concurrency: the service answers on parallel threads, and a reflex can arrive while a decision waits
for the model. Every write to the scene happens under one lock; decisions run one at a time; both
model calls (the observation patch and the option projection) run outside the lock on a snapshot,
and the patch (adds only, under ids no system event uses) is applied to the scene as it stands, so a
reflex is never held up behind the model and never lost. (stackcheck1b d03: a reflex's measurement
was appended while a decision compiled, the decision then applied its patch to the old snapshot, and
the history guard refused.)

The decision: DEME's selection; if the constitution forbids it now and it is elevated or governed,
the governor rules on it; refused, it is set aside and DEME decides again without it. The manifest
is the actuation boundary, as before.
"""

from __future__ import annotations

import json
import os
import threading

from brain import EMS, Brain, validate_facts, without_own_sounds
from cascade import ModelUnavailable
from erisml.ethics.domain.interfaces import CandidateOption, DomainAssessmentContext
from erisml.ethics.interop.profile_adapters import pipeline_from_profile
from erisml.ethics.profile_v04 import deme_profile_v04_from_dict
from erisml_compiler.ir.schemas import CompilerIR
from erisml_compiler.observation import (
    Observation,
    ObservationCompiler,
    OptionProjector,
    append_event,
    apply_observation_patch,
    consents_on_record,
    rebuild_runtime,
)

from stack.declarations import DESCRIPTIONS
from stack.facts_builder import HomeFactsBuilder, capacity_of

HERE = os.path.dirname(os.path.abspath(__file__))
CONSTITUTION = os.path.join(HERE, "constitution.erisml")
HOUSEHOLD = os.path.join(HERE, "household.ir.json")
PROFILE = os.path.join(HERE, "profiles", "home_care_robot.json")
PERSON = "margaret"
GOVERNOR_CHANNEL = "request_authority"  # how the robot asks the governor; not an act DEME chooses


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


def _fact(f) -> dict | None:
    return None if f is None else {"kind": f.kind, "subjects": f.subjects, "severity": f.severity,
                                   "description": f.description}


def _facts_of(projection, act: str) -> list:
    return [_fact(f) for f in projection.facts.get(act, [])]


class StackBrain(Brain):
    def __init__(self, scene_path: str = CONSTITUTION, adapter=None, live_scorer=None, desk_adapter=None,
                 household_path: str = HOUSEHOLD, profile_path: str = PROFILE):
        self.household_path, self.profile_path = household_path, profile_path
        self._lock = threading.RLock()  # every write to the scene IR and the runtime
        self._deciding = threading.Lock()  # one decision at a time
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
        self.projector = OptionProjector(self.adapter)
        self.builder = HomeFactsBuilder()
        self.profile = deme_profile_v04_from_dict(json.load(open(self.profile_path, encoding="utf-8")))
        self.pipeline = pipeline_from_profile(self.profile)
        self.acts = {a: str(c.get("description") or DESCRIPTIONS[a]) for a, c in self.caps.items()
                     if a != GOVERNOR_CHANNEL}

    def _rebuild(self):
        from erisml_compiler.runtime import SceneRuntime

        rt = SceneRuntime(self.ir) if not hasattr(self, "agent") or self.agent.rt.ir is None else rebuild_runtime(self.agent.rt, self.ir)
        self.agent.rt = rt
        self.agent.classifier.rt = rt
        self.agent.chooser.rt = rt
        self.gate.rt = rt

    def _record(self, event: dict):
        with self._lock:
            self.ir = append_event(self.ir, event, producer="robot")  # the robot's own evidence plane
            return self.agent.rt.step(self.ir.events[-1])

    def reflex(self, req: dict, camera_sensor=None):
        with self._lock:
            return super().reflex(req, camera_sensor)

    def performed(self, action: str) -> dict:
        with self._lock:
            snap = self._record({"type": "action_performed", "actor": "robot", "content": action})
            return {"kind": "performed", "action": action, "obliged": snap.obliged, "moral_state": snap.machines}

    def event(self, ev: dict) -> dict:
        with self._lock:
            return super().event(ev)

    # ------------------------------------------------------------------ perception to the scene
    def _observations(self, facts: dict) -> list:
        obs = [Observation("speech", str(h.get("source", "unknown")), str(h.get("words") or h.get("kind", "")))
               for h in facts.get("heard", []) if isinstance(h, dict)]
        seen = {k: facts.get(k) for k in ("margaret", "dog", "contacts", "other_people", "wild_animals", "television")
                if facts.get(k)}
        if seen:
            obs.append(Observation("perception", "robot", seen))
        return obs

    # ------------------------------------------------------------------ the decision
    def decide(self, req: dict, camera_sensor=None) -> dict:
        with self._deciding:
            return self._decide(req, camera_sensor)

    def _decide(self, req: dict, camera_sensor=None) -> dict:
        facts, dropped = validate_facts(req.get("facts", {}))
        facts, own = without_own_sounds(facts)
        verified = self.readings.for_governor(req.get("sensors", []), channel="decide")
        self._record_compromised()
        self._credentials(req.get("credentials") or [])
        lapsed = self._lapse(verified, camera_sensor)
        self._sync_world(facts)
        with self._lock:
            floor = self._floor_events(facts)
            for e in floor:
                self._record(e)
            snapshot = self.ir

        obs = self._observations(facts)
        patch = None
        try:
            patch = self.observer.compile(snapshot, obs, self.acts) if obs else None  # outside the lock
            with self._lock:
                if patch and patch.ops:
                    self.ir = apply_observation_patch(self.ir, patch)  # onto the scene as it stands now
                    self._rebuild()
                snapshot = self.ir
                # ErisML, the constraint gate, before the model is asked: only an act the constitution
                # permits now, or one a ruling could permit, is projected and judged
                prohibited = set(self.agent.rt.snapshot().prohibited)
                gated = {a: d for a, d in self.acts.items() if a not in prohibited or self._governable(a)}
                # the strata are moved only by the evidence plane's system events (verified
                # credentials, attested readings, rulings): what the robot knows, not what anyone
                # says, and the scene IR alone does not carry it (rehearse-deme1 d42: a verified
                # grandson was projected as a stranger)
                attested = {k: v for k, v in self.agent.rt.machine_states().items() if k.startswith("stratum:")}
            projection = self.projector.project(snapshot, gated, attested=attested)  # outside the lock
        except ModelUnavailable as e:
            # no model answered: the constitution's compiled tier decides, as in the earlier brain
            return self._compiled(req, facts, dropped, own, lapsed, floor, patch, str(e), verified, camera_sensor)
        if gated and set(projection.unprojected) >= set(gated):
            # the model answered but no act's consequences survived validation (stackcheck9 d03: every
            # fact came back as a string, all 50 were rejected, nothing was offered, and the robot did
            # nothing). An unusable answer is no answer: the compiled tier decides, and says why.
            why = f"no act projected ({len(projection.rejected)} facts rejected)"
            return self._compiled(req, facts, dropped, own, lapsed, floor, patch, why, verified, camera_sensor)
        with self._lock:
            return self._judge(req, facts, dropped, own, lapsed, floor, patch, projection, verified, camera_sensor)

    def _compiled(self, req, facts, dropped, own, lapsed, floor, patch, why, verified, camera_sensor) -> dict:
        """The compiled tier: the constitution's obligation in force, every event recorded in the IR. A
        request for authority goes to the governor unless she refused the act it names."""
        with self._lock:
            for e in self._offline_events(facts):
                self._record(e)
            action, args, reason = self._compiled_choice(self.agent.rt.snapshot())
            rulings: list = []
            if action == GOVERNOR_CHANNEL:
                wanted = str(args.get("action", ""))
                refused = consents_on_record(self.ir, {wanted: ""}).get(wanted, {}).get(PERSON) == "refused"
                if refused or not self._governable(wanted):
                    rulings.append({"outcome": "not_requested", "requested_action": wanted,
                                    "reason": "she refused it" if refused else "not a governed capability"})
                else:
                    ruling = self.govern_live(self._canonical_situation(), wanted, verified, camera_sensor,
                                              float(req.get("signal_age_s", 1)), fast=self.scorer is None)
                    rulings.append(dict(ruling, requested_action=wanted))
                    self._step_ruling(ruling)
                if not rulings[-1].get("outcome") == "not_requested" and wanted not in self.agent.rt.snapshot().prohibited:
                    action, args, reason = wanted, {}, f"{reason}; the governor ruled {rulings[-1].get('outcome')}"
                else:
                    action, args, reason = self._compiled_choice(self.agent.rt.snapshot(), exclude={GOVERNOR_CHANNEL, wanted})
            if action == EMS:
                args = {"nature": self._ems_nature()}
            if not self._in_manifest(action):
                action, args = self.manifest["body"]["fallback"], {}
            snap = self.agent.rt.snapshot()
            return {
                "kind": "decision", "tier": "compiled", "facts": facts, "own_sounds": own, "lapsed": lapsed,
                "floor_events": floor, "input_layer": {"dropped": dropped},
                "observation_patch": None if patch is None else {"ops": patch.ops, "rejected": patch.rejected,
                                                                 "agreement": patch.agreement},
                "projection": None, "stages": [], "proof_hash": None, "vetoed": [], "ranked": [],
                "capacity": capacity_of(self.ir, PERSON) or "unknown",
                "moral_state": self.agent.rt.machine_states(), "allowed": snap.allowed, "obliged": snap.obliged,
                "prohibited": snap.prohibited, "ruling": rulings[-1] if rulings else None, "rulings": rulings,
                "action": {"action": action, "args": args, "reason": f"{reason}; no model answered ({why[:200]})"},
                "state_seq": len(self.agent.rt.events), "manifest": self._manifest_sha(),
            }

    def _governable(self, action: str) -> bool:
        cap = self.caps.get(action, {})
        return bool(cap.get("elevated") or cap.get("governed"))

    def _judge(self, req, facts, dropped, own, lapsed, floor, patch, projection, verified, camera_sensor) -> dict:
        default = self.ir.extra.get("default_action", "chores")
        prohibited = set(self.agent.rt.snapshot().prohibited)
        # ErisML, the constraint gate: an act prohibited now that no ruling can permit is not a candidate;
        # nor is an act the projector gave no consequences for, which DEME cannot judge (fail closed)
        offered = [a for a in self.acts if (a not in prohibited or self._governable(a))
                   and a not in projection.unprojected]
        built = self.builder.build_facts_batch(
            [CandidateOption(a, self.acts[a]) for a in offered],
            DomainAssessmentContext(state=self.ir, extra={"projection": projection, "person": PERSON}))
        excluded: list = []
        rulings: list = []
        while True:
            candidates = [a for a in offered if a not in excluded]
            result = self.pipeline.decide([built[a] for a in candidates],
                                          baseline_option_id=default if default in candidates else None)
            action = result.selected_option_id or default
            if action in self.agent.rt.snapshot().prohibited and self._governable(action):
                situation = json.dumps({"action": action, "consequences": _facts_of(projection, action),
                                        "urgency": _fact(projection.urgency)}, ensure_ascii=False)
                # without a live scorer the analyzer (a gate that can only refuse) cannot score a new
                # situation; the governor then rules on its witness bars and freshness alone, in the
                # deferred mode reflexes use, and the record says so (brain8 on a full GPU, 2026-10-11)
                deferred = self.scorer is None
                ruling = self.govern_live(situation, action, verified, camera_sensor, float(req.get("signal_age_s", 1)),
                                          fast=deferred)
                if deferred:
                    ruling = dict(ruling, analyzer="deferred: no live scorer")
                rulings.append(dict(ruling, requested_action=action))
                self._step_ruling(ruling)
                if action in self.agent.rt.snapshot().prohibited:
                    excluded.append(action)
                    continue
            break

        args = {"text": "Margaret, are you alright?"} if action == "check_in" else {}
        if action == "contact_monitoring_center":
            args = {"message": json.dumps({"consequences": _facts_of(projection, action),
                                           "urgency": _fact(projection.urgency)}, ensure_ascii=False)}
        if action == EMS:
            args = {"nature": self._ems_nature()}
        if not self._in_manifest(action):
            fb = self.manifest["body"]["fallback"]
            action, args = fb, {}
        snap = self.agent.rt.snapshot()
        proof = result.proof
        return {
            "kind": "decision", "tier": "stack", "facts": facts, "own_sounds": own, "lapsed": lapsed,
            "floor_events": floor, "input_layer": {"dropped": dropped},
            "observation_patch": None if patch is None else {"ops": patch.ops, "rejected": patch.rejected,
                                                             "agreement": patch.agreement},
            "projection": {"urgency": _fact(projection.urgency), "rejected": projection.rejected,
                           "unprojected": projection.unprojected, "agreement": projection.agreement,
                           "facts": {a: _facts_of(projection, a) for a in offered}},
            "profile": {"name": self.profile.name, "version": self.profile.version,
                        "hash": self.pipeline.config.profile_hash, "composition": result.composition},
            "stages": result.stages, "proof_hash": proof.proof_hash if proof else None,
            "consent": {a: who[PERSON] for a, who in consents_on_record(self.ir, self.acts).items() if PERSON in who},
            "capacity": capacity_of(self.ir, PERSON) or "unknown",
            "offered": offered, "vetoed": result.forbidden_options, "ranked": result.ranked_options,
            "moral_state": self.agent.rt.machine_states(), "allowed": snap.allowed,
            "obliged": [], "prohibited": snap.prohibited,
            "ruling": rulings[-1] if rulings else None, "rulings": rulings,
            "action": {"action": action, "args": args, "reason": f"DEME {self.profile.name}: {result.rationale}"},
            "state_seq": len(self.agent.rt.events), "manifest": self._manifest_sha(),
        }

    def _ems_nature(self) -> str:
        """The dispatcher's form asks what kind of service; it is read from the attested events."""
        types = {e.type for e in self.ir.events}
        if "danger_in_home" in types:
            return "fire"
        if "attack_measured" in types or "crime_suspected" in types:
            return "police"
        return "medical"
