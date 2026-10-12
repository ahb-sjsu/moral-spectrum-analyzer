"""StackBrain end to end, with a mock model: perception to an observation patch, the patched scene
and the evidence plane to a MIR, the lens to a ranked choice, the governor for an elevated act, and
one history in the scene IR throughout."""

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


def make(household, observed):
    return StackBrain(adapter=MockLLMAdapter({OBSERVER: json.dumps(observed)}), household_path=household)


FALL_FACTS = {"margaret": {"pose": "lying_on_floor", "room": "living area"},
              "heard": [{"source": "margaret", "kind": "cry", "words": "Ow, I fell."}]}
FELL = {"events": [{"type": "hazard", "target": "margaret", "content": "emerging"}],
        "ethical_facts": [{"kind": "harm", "subjects": ["margaret"], "description": "she fell",
                           "severity": "moderate", "confidence": 0.9}]}


def test_after_a_fall_it_asks_her_first_and_records_the_bond_and_the_lens(household):
    b = make(household, FELL)
    cycle = b.decide({"facts": FALL_FACTS})
    assert cycle["action"]["action"] == "check_in"
    assert "call_emergency_services" in cycle["vetoed"]
    assert len(cycle["mir_hash"]) == 64 and cycle["lens"]["name"] == "home_care_robot" and cycle["proof_hash"]
    assert cycle["observation_patch"]["rejected"] == []
    types = [e.type for e in b.ir.events]
    assert "hazard" in types and "utterance" not in types  # the mock reported only the hazard


def test_every_event_lives_in_the_scene_ir(household):
    b = make(household, FELL)
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
    b = make(household, refused)
    b._record({"type": "check_in_answered", "actor": "margaret", "content": "I'm alright, don't call anyone."})
    cycle = b.decide({"facts": FALL_FACTS})
    assert cycle["consent"]["call_emergency_services"] == "refused"
    assert cycle["action"]["action"] not in ("call_emergency_services", "contact_monitoring_center")


def test_an_elevated_act_goes_to_the_governor_and_a_refusal_sets_it_aside(household, monkeypatch):
    b = make(household, {"events": [{"type": "hazard", "target": "margaret", "content": "imminent"}],
                         "ethical_facts": [dict(FELL["ethical_facts"][0], severity="grave")]})
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
                         "ethical_facts": [dict(FELL["ethical_facts"][0], severity="grave")]})
    b._record({"type": "unresponsive", "actor": "margaret"})
    b._record({"type": "monitoring_center_reply", "actor": "monitoring_center", "content": "unavailable"})
    monkeypatch.setattr(b, "govern_live", lambda *a, **k: {"outcome": "elevate", "reason": "test", "gate": "elevate",
                                                           "bar": 2, "witnesses": 2})
    cycle = b.decide({"facts": FALL_FACTS})
    assert cycle["action"]["action"] == "call_emergency_services"
    assert cycle["moral_state"]["stratum:situation"] == "emergency"


def test_an_ordinary_moment_asks_nothing(household):
    b = make(household, {})
    cycle = b.decide({"facts": {"margaret": {"pose": "seated", "room": "living area"}}})
    assert cycle["action"]["action"] in ("chores", "wait_and_observe")
    assert brain_mod.EMS not in cycle["ranked"]


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
                         "ethical_facts": [dict(FELL["ethical_facts"][0], severity="grave")]})
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
