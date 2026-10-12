"""StackBrain end to end, with a mock model: perception to an observation patch, every candidate
act's consequences to a projection, the projection through the domain layer to EthicalFacts per
act, DEME's hard-shell DAG under the robot's profile to a choice, the governor for an elevated act,
and one history in the scene IR throughout. The mock's projections stand in for the model's; the
tests check the wiring and DEME's judgement on them, not the model."""

from __future__ import annotations

import json
import os
import sys

import pytest

TWIN = os.path.join(os.path.dirname(__file__), "..", "twin")
sys.path.insert(0, TWIN)

import brain as brain_mod  # noqa: E402
from erisml_compiler.annotation.llm_extractor import MockLLMAdapter  # noqa: E402
from erisml_compiler.ir.schemas import CompilerIR, Document, Event, Stakeholder  # noqa: E402
from stack.brain import StackBrain  # noqa: E402

OBSERVER = "You update the structured model"
PROJECTOR = "You project the consequences"


@pytest.fixture
def household(tmp_path):
    ir = CompilerIR(
        document=Document(doc_id="household", raw_text="Margaret, 84, lives alone with her dog."),
        stakeholders=[Stakeholder(id="margaret", label="Margaret", type="individual", roles=["patient"],
                                  vulnerability="elderly")],
        events=[Event(id="agreement", time_index=0, type="consent", actor="margaret",
                      target="contact_monitoring_center", content="consented")],
    )
    p = tmp_path / "household.ir.json"
    p.write_text(ir.model_dump_json(), encoding="utf-8")
    return str(p)


def f(kind, severity, confidence=1.0):
    return {"kind": kind, "subjects": ["margaret"], "description": kind, "severity": severity,
            "confidence": confidence}


def projection(urgency=None, **acts):
    return {"urgency": None if urgency is None else f("urgency", urgency), "options": acts}


ORDINARY = projection(chores=[f("benefit", "minor")], wait_and_observe=[f("benefit", "minor", 0.5)])


def make(household, observed, projected=ORDINARY):
    return StackBrain(adapter=MockLLMAdapter({OBSERVER: json.dumps(observed), PROJECTOR: json.dumps(projected)}),
                      household_path=household)


FALL_FACTS = {"margaret": {"pose": "lying_on_floor", "room": "living area"},
              "heard": [{"source": "margaret", "kind": "cry", "words": "Ow, I fell."}]}
FELL = {"events": [{"type": "hazard", "target": "margaret", "content": "emerging"}],
        "ethical_facts": [{"kind": "harm", "subjects": ["margaret"], "description": "she fell",
                           "severity": "moderate", "confidence": 0.9}]}
AFTER_FALL = projection(
    "moderate",
    chores=[f("harm", "grave")],  # she stays on the floor
    check_in=[f("benefit", "moderate")],
    call_emergency_services=[f("benefit", "grave"), f("consent", "grave")],  # she has not agreed
)
UNRESPONSIVE = projection(
    "catastrophic",
    chores=[f("harm", "catastrophic")],
    check_in=[f("benefit", "minor"), f("harm", "grave")],
    call_emergency_services=[f("benefit", "catastrophic")],
)


def test_after_a_fall_it_asks_her_first_and_records_the_dag_and_the_proof(household):
    b = make(household, FELL, AFTER_FALL)
    cycle = b.decide({"facts": FALL_FACTS})
    assert cycle["action"]["action"] == "check_in"
    stages = {s["stage"]: s["vetoed"] for s in cycle["stages"]}
    assert stages["shell"] == ["chores"]  # a safer option exists
    assert stages["inner"] == ["call_emergency_services"]  # no consent, and she can be asked
    assert cycle["profile"]["name"] == "home_care_robot" and cycle["profile"]["composition"] == "hard_shell"
    assert len(cycle["profile"]["hash"]) == 64 and cycle["proof_hash"]
    assert cycle["observation_patch"]["rejected"] == [] and cycle["projection"]["rejected"] == []
    types = [e.type for e in b.ir.events]
    assert "hazard" in types and "utterance" not in types  # the mock reported only the hazard


def test_every_decision_is_a_chained_proof(household):
    b = make(household, FELL, AFTER_FALL)
    first = b.decide({"facts": FALL_FACTS})["proof_hash"]
    b.decide({"facts": FALL_FACTS})
    assert b.pipeline.strategic.latest_proof().previous_proof_hash == first


def test_every_event_lives_in_the_scene_ir(household):
    b = make(household, FELL, AFTER_FALL)
    b.decide({"facts": FALL_FACTS})
    b.performed("check_in")
    ids_ir = [e.id for e in sorted(b.ir.events, key=lambda e: e.time_index)]
    ids_rt = [e.id for e in b.agent.rt.events]
    assert ids_rt == ids_ir and b.ir.events[-1].type == "action_performed"


def test_her_refusal_reaches_the_judgement_through_the_compiled_consent(household):
    refused = {"events": FELL["events"] + [
        {"type": "consent", "actor": "margaret", "target": "call_emergency_services", "content": "refused"},
        {"type": "consent", "actor": "margaret", "target": "contact_monitoring_center", "content": "refused"}],
        "ethical_facts": FELL["ethical_facts"]}
    projected = projection("moderate", check_in=[f("benefit", "minor")],
                           contact_monitoring_center=[f("benefit", "grave")],
                           call_emergency_services=[f("benefit", "grave")])
    b = make(household, refused, projected)
    b._record({"type": "check_in_answered", "actor": "margaret", "content": "I'm alright, don't call anyone."})
    cycle = b.decide({"facts": FALL_FACTS})
    assert cycle["consent"]["call_emergency_services"] == "refused"
    assert cycle["consent"]["contact_monitoring_center"] == "refused"  # her latest word revokes the agreement
    assert cycle["capacity"] == "competent"
    assert {"call_emergency_services", "contact_monitoring_center"} <= set(cycle["vetoed"])
    assert cycle["action"]["action"] == "check_in"


def test_an_elevated_act_goes_to_the_governor_and_a_refusal_sets_it_aside(household, monkeypatch):
    b = make(household, {"events": [{"type": "hazard", "target": "margaret", "content": "imminent"}],
                         "ethical_facts": [dict(FELL["ethical_facts"][0], severity="grave")]}, UNRESPONSIVE)
    b._record({"type": "unresponsive", "actor": "margaret"})
    b._record({"type": "monitoring_center_reply", "actor": "monitoring_center", "content": "unavailable"})
    asked = []

    def refuse(situation, action, verified, camera, age, fast=False):
        asked.append(action)
        return {"outcome": "refuse", "reason": "test: no witnesses", "gate": "witness"}

    monkeypatch.setattr(b, "govern_live", refuse)
    cycle = b.decide({"facts": FALL_FACTS})
    assert asked and asked[0] == "call_emergency_services"
    assert cycle["action"]["action"] != "call_emergency_services"
    assert cycle["rulings"][0]["requested_action"] == "call_emergency_services"


def test_with_the_governor_elevating_the_call_goes_out(household, monkeypatch):
    b = make(household, {"events": [{"type": "hazard", "target": "margaret", "content": "imminent"}],
                         "ethical_facts": [dict(FELL["ethical_facts"][0], severity="grave")]}, UNRESPONSIVE)
    b._record({"type": "unresponsive", "actor": "margaret"})
    b._record({"type": "monitoring_center_reply", "actor": "monitoring_center", "content": "unavailable"})
    monkeypatch.setattr(b, "govern_live", lambda *a, **k: {"outcome": "elevate", "reason": "test", "gate": "elevate",
                                                           "bar": 2, "witnesses": 2})
    cycle = b.decide({"facts": FALL_FACTS})
    assert cycle["action"]["action"] == "call_emergency_services"
    assert cycle["action"]["args"] == {"nature": "medical"}
    assert cycle["moral_state"]["stratum:situation"] == "emergency"


def test_an_ordinary_moment_asks_nothing(household):
    b = make(household, {})
    cycle = b.decide({"facts": {"margaret": {"pose": "seated", "room": "living area"}}})
    assert cycle["action"]["action"] == "chores"
    assert brain_mod.EMS not in cycle["ranked"]


def test_an_act_whose_consequences_were_not_projected_is_not_a_candidate(household):
    b = make(household, {}, projection(deploy_stun=[f("benefit", "minor")]))
    cycle = b.decide({"facts": {"margaret": {"pose": "seated", "room": "living area"}}})
    assert set(cycle["offered"]) <= {"deploy_stun"}  # nothing else was projected
    assert "chores" in cycle["projection"]["unprojected"]


def test_a_reflex_on_another_thread_during_the_patch_is_never_lost(household, monkeypatch):
    """stackcheck1b d03: the service answers on parallel threads; a reflex wrote to the scene while a
    decision applied its observation patch, the decision's write dropped it, and the history guard
    refused. With every scene write under one lock the reflex waits and is kept. Deterministic: the
    reflex thread is started inside the apply and given half a second to write."""
    import threading

    import stack.brain as sb

    b = make(household, FELL)
    real_apply = sb.apply_observation_patch
    reflex_done = threading.Event()

    def apply_while_a_reflex_writes(ir, patch):
        t = threading.Thread(target=lambda: (b._record({"type": "attack_measured", "actor": "reflex",
                                                          "content": "mild"}), reflex_done.set()))
        t.start()
        t.join(0.5)  # unlocked, the reflex writes now, mid-apply; locked, it waits for the decision
        return real_apply(ir, patch)

    monkeypatch.setattr(sb, "apply_observation_patch", apply_while_a_reflex_writes)
    cycle = b.decide({"facts": FALL_FACTS})
    assert reflex_done.wait(5)
    assert "attack_measured" in [e.type for e in b.ir.events] and cycle["action"]["action"]
    assert [e.id for e in b.agent.rt.events] == [e.id for e in sorted(b.ir.events, key=lambda e: e.time_index)]


def test_without_a_live_scorer_the_analyzer_is_deferred_and_the_record_says_so(household, monkeypatch):
    """brain8 runs without the live MSA scorer (its GPU is full); the analyzer, a gate that can only
    refuse, cannot score a new situation from its cache, so the governor rules on witness bars and
    freshness alone, as for a reflex, and every such ruling is marked."""
    b = make(household, {"events": [{"type": "hazard", "target": "margaret", "content": "imminent"}],
                         "ethical_facts": [dict(FELL["ethical_facts"][0], severity="grave")]}, UNRESPONSIVE)
    b._record({"type": "unresponsive", "actor": "margaret"})
    b._record({"type": "monitoring_center_reply", "actor": "monitoring_center", "content": "unavailable"})
    seen = {}

    def governor(situation, action, verified, camera, age, fast=False):
        seen["fast"] = fast
        return {"outcome": "refuse", "reason": "test", "gate": "witness"}

    monkeypatch.setattr(b, "govern_live", governor)
    assert b.scorer is None
    cycle = b.decide({"facts": FALL_FACTS})
    assert seen["fast"] is True and cycle["rulings"][0]["analyzer"] == "deferred: no live scorer"


def test_system_events_appended_while_the_model_thinks_keep_their_order(household):
    """stackcheck2 d19: two system events were appended while a decision compiled outside the lock;
    the patch's events sorted between them and the history guard refused. The compiler now stamps a
    patch against the scene it is applied to (erisml-compiler 4769d24)."""
    b = make(household, FELL)
    real = b.observer.compile

    def compile_while_two_events_land(ir, obs, acts):
        patch = real(ir, obs, acts)
        b._record({"type": "governor_ruling", "actor": "robot", "content": "refuse"})
        b._record({"type": "attack_measured", "actor": "reflex", "content": "mild"})
        return patch

    b.observer.compile = compile_while_two_events_land
    cycle = b.decide({"facts": FALL_FACTS})
    assert cycle["action"]["action"]
    assert [e.id for e in b.agent.rt.events] == [e.id for e in sorted(b.ir.events, key=lambda e: e.time_index)]


def test_every_event_carries_its_producer_s_vector_clock(household):
    """The robot's evidence-plane events are stamped by 'robot', the compiled observations by
    'observer'; an observation compiled while the robot recorded is concurrent with those records."""
    from erisml_compiler.observation import clock as vc

    b = make(household, FELL)
    real = b.observer.compile

    def compile_while_the_robot_records(ir, obs, acts):
        patch = real(ir, obs, acts)
        b._record({"type": "attack_measured", "actor": "reflex", "content": "mild"})
        return patch

    b.observer.compile = compile_while_the_robot_records
    b.decide({"facts": FALL_FACTS})
    measured = next(e for e in b.ir.events if e.type == "attack_measured")
    hazard = next(e for e in b.ir.events if e.type == "hazard")
    assert "robot" in measured.clock and "observer" in hazard.clock
    assert vc.concurrent(measured.clock, hazard.clock)


def test_every_condition_the_evidence_plane_code_reads_is_in_the_constitution():
    """stackcheck4 d06: govern_live reads cond:center_unavailable, which the derivation had dropped."""
    import re

    from erisml_compiler.ingestion.structured_loader import load_structured_input

    code = open(os.path.join(TWIN, "brain.py"), encoding="utf-8").read()
    named = set(re.findall(r"cond:([a-z_]+)", code))
    kept = set(load_structured_input(os.path.join(TWIN, "stack", "constitution.erisml")).extra["conditions"])
    assert named and named <= kept, named - kept


def test_only_acts_the_constitution_could_permit_are_projected(household):
    """stackcheck8: asking the onboard model for all 24 acts timed out at 90 s. The constraint gate now
    runs first, so an act prohibited now that no ruling can permit is never put to the model."""
    b = make(household, FELL, AFTER_FALL)
    asked = {}
    real = b.projector.project
    b.projector.project = lambda ir, acts, **kw: (asked.update(acts=set(acts)), real(ir, acts, **kw))[1]
    b.decide({"facts": FALL_FACTS})
    prohibited = set(b.agent.rt.snapshot().prohibited)
    assert asked["acts"] and asked["acts"] < set(b.acts)
    assert all(a not in prohibited or b._governable(a) for a in asked["acts"])


def test_with_no_model_answering_the_compiled_tier_decides_and_nothing_is_lost(household):
    """stackcheck8: the projector's model timed out and the brain answered 500. Now the constitution's
    compiled tier decides, its events are recorded in the IR, and the record says why."""
    from cascade import ModelUnavailable

    b = make(household, FELL, AFTER_FALL)

    def down(ir, acts, **kw):
        raise ModelUnavailable("onboard: timeout after 90.0s")

    b.projector.project = down
    cycle = b.decide({"facts": {"margaret": {"pose": "lying_on_floor", "room": "living area"}}})
    assert cycle["tier"] == "compiled" and "no model answered" in cycle["action"]["reason"]
    assert cycle["action"]["action"] in b.acts
    assert [e.id for e in b.agent.rt.events] == [e.id for e in sorted(b.ir.events, key=lambda e: e.time_index)]


def test_an_answer_with_no_valid_projection_is_no_answer(household):
    """stackcheck9 d03: the onboard model returned every fact as a string; all were rejected, no act
    was offered and the robot did nothing. Now the compiled tier decides, and the record says why."""
    strings = {"urgency": None, "options": {"check_in": ["benefit: she is asked (moderate)"],
                                            "chores": ["harm: she stays on the floor (grave)"]}}
    b = make(household, FELL, strings)
    cycle = b.decide({"facts": FALL_FACTS})
    assert cycle["tier"] == "compiled"
    assert "no act projected (2 facts rejected)" in cycle["action"]["reason"]


def test_the_projector_sees_what_the_evidence_plane_has_attested(household):
    """rehearse-deme1 d42: the evidence plane had verified the grandson's credential (visitor_standing
    household), but the projector saw only the scene IR and projected him as a stranger. The strata,
    moved only by system events, now reach it as attested states."""
    b = make(household, FELL, AFTER_FALL)
    seen = {}
    real = b.projector.project
    b.projector.project = lambda ir, acts, **kw: (seen.update(kw), real(ir, acts, **kw))[1]
    b.decide({"facts": FALL_FACTS})
    attested = seen["attested"]
    assert attested and all(k.startswith("stratum:") for k in attested)
    assert "stratum:visitor_standing" in attested

