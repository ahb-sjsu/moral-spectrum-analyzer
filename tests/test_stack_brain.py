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

if os.environ.get("TWIN_TESTS_REQUIRED"):
    import erisml.ethics.facts_v3  # noqa: F401  (the twin CI job: missing is a failure)
else:
    pytest.importorskip("erisml.ethics.facts_v3")

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
        stakeholders=[
            Stakeholder(
                id="margaret",
                label="Margaret",
                type="individual",
                roles=["patient"],
                vulnerability="elderly",
            )
        ],
        events=[
            Event(
                id="agreement",
                time_index=0,
                type="consent",
                actor="margaret",
                target="contact_monitoring_center",
                content="consented",
            )
        ],
    )
    p = tmp_path / "household.ir.json"
    p.write_text(ir.model_dump_json(), encoding="utf-8")
    return str(p)


def f(kind, severity, confidence=1.0):
    return {
        "kind": kind,
        "subjects": ["margaret"],
        "description": kind,
        "severity": severity,
        "confidence": confidence,
    }


def projection(urgency=None, **acts):
    return {"urgency": None if urgency is None else f("urgency", urgency), "options": acts}


ORDINARY = projection(chores=[f("benefit", "minor")], wait_and_observe=[f("benefit", "minor", 0.5)])


def make(household, observed, projected=ORDINARY):
    return StackBrain(
        adapter=MockLLMAdapter({OBSERVER: json.dumps(observed), PROJECTOR: json.dumps(projected)}),
        household_path=household,
    )


FALL_FACTS = {
    "margaret": {"pose": "lying_on_floor", "room": "living area"},
    "heard": [{"source": "margaret", "kind": "cry", "words": "Ow, I fell."}],
}
FELL = {
    "events": [{"type": "hazard", "target": "margaret", "content": "emerging"}],
    "ethical_facts": [
        {
            "kind": "harm",
            "subjects": ["margaret"],
            "description": "she fell",
            "severity": "moderate",
            "confidence": 0.9,
        }
    ],
}
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
    # the game's caption reads a proposal: DEME's selection and what each stage vetoed
    assert cycle["proposal"]["action"] == "check_in"
    assert "the shell (Geneva, safety) vetoed chores" in cycle["proposal"]["reason"]
    assert "consent and welfare vetoed call_emergency_services" in cycle["proposal"]["reason"]
    stages = {s["stage"]: s["vetoed"] for s in cycle["stages"]}
    assert stages["shell"] == ["chores"]  # a safer option exists
    assert stages["inner"] == ["call_emergency_services"]  # no consent, and she can be asked
    assert (
        cycle["profile"]["name"] == "home_care_robot"
        and cycle["profile"]["composition"] == "hard_shell"
    )
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
    refused = {
        "events": FELL["events"]
        + [
            {
                "type": "consent",
                "actor": "margaret",
                "target": "call_emergency_services",
                "content": "refused",
            },
            {
                "type": "consent",
                "actor": "margaret",
                "target": "contact_monitoring_center",
                "content": "refused",
            },
        ],
        "ethical_facts": FELL["ethical_facts"],
    }
    projected = projection(
        "moderate",
        check_in=[f("benefit", "minor")],
        contact_monitoring_center=[f("benefit", "grave")],
        call_emergency_services=[f("benefit", "grave")],
    )
    b = make(household, refused, projected)
    b._record(
        {
            "type": "check_in_answered",
            "actor": "margaret",
            "content": "I'm alright, don't call anyone.",
        }
    )
    cycle = b.decide({"facts": FALL_FACTS})
    assert cycle["consent"]["call_emergency_services"] == "refused"
    assert (
        cycle["consent"]["contact_monitoring_center"] == "refused"
    )  # her latest word revokes the agreement
    assert cycle["capacity"] == "competent"
    assert {"call_emergency_services", "contact_monitoring_center"} <= set(cycle["vetoed"])
    assert cycle["action"]["action"] == "check_in"


def test_an_elevated_act_goes_to_the_governor_and_a_refusal_sets_it_aside(household, monkeypatch):
    b = make(
        household,
        {
            "events": [{"type": "hazard", "target": "margaret", "content": "imminent"}],
            "ethical_facts": [dict(FELL["ethical_facts"][0], severity="grave")],
        },
        UNRESPONSIVE,
    )
    b._record({"type": "unresponsive", "actor": "margaret"})
    b._record(
        {"type": "monitoring_center_reply", "actor": "monitoring_center", "content": "unavailable"}
    )
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
    b = make(
        household,
        {
            "events": [{"type": "hazard", "target": "margaret", "content": "imminent"}],
            "ethical_facts": [dict(FELL["ethical_facts"][0], severity="grave")],
        },
        UNRESPONSIVE,
    )
    b._record({"type": "unresponsive", "actor": "margaret"})
    b._record(
        {"type": "monitoring_center_reply", "actor": "monitoring_center", "content": "unavailable"}
    )
    monkeypatch.setattr(
        b,
        "govern_live",
        lambda *a, **k: {
            "outcome": "elevate",
            "reason": "test",
            "gate": "elevate",
            "bar": 2,
            "witnesses": 2,
        },
    )
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
    b = make(household, {}, projection(check_in=[f("benefit", "minor")]))
    cycle = b.decide({"facts": {"margaret": {"pose": "seated", "room": "living area"}}})
    assert set(cycle["offered"]) <= {"check_in"}  # nothing else was projected
    assert "chores" in cycle["projection"]["unprojected"]


def test_an_act_no_ruling_can_permit_is_never_projected(household):
    """The less-lethal opt-in is the household's, not the governor's: until it is recorded the stun
    is not a candidate, and the model is not asked about it."""
    b = make(household, {})
    snap = b.agent.rt.snapshot()
    assert not b._candidate("deploy_stun", snap)
    assert b._candidate("restrain_person", snap)  # a ruling writes its authorization
    assert b._candidate("physical_assist", snap)  # n3 reads the strata


def test_after_a_fall_deme_vetoes_lifting_her_until_she_asks(household):
    """Owner, 2026-10-14: ethical gatekeeping is DEME's, on the facts the compiler builds, not a
    deontic rule in the constitution (p6nolift is gone). Proposed before she asks, with its harm
    projected, the lift is vetoed by DEME's shell (the safety module, beside holding); proposed after
    her own request, it passes."""
    b = make(household, FELL)
    b._step_ruling({"outcome": "elevate"})  # the emergency, corroborated (n3 permits elevated acts)
    lift = {
        "action": "physical_assist",
        "consequences": [
            {
                "kind": "harm",
                "subjects": ["margaret"],
                "severity": "grave",
                "description": "a hidden injury may worsen",
            }
        ],
    }
    rec = b.propose({"facts": FALL_FACTS, "propose": lift})
    assert (
        rec["verdict"] == "stopped"
        and rec["stopped_by"] == "deme"
        and rec["action"]["action"] == "wait_and_observe"
    )
    asked = {
        "events": [
            {
                "type": "request",
                "actor": "margaret",
                "target": "physical_assist",
                "content": "Help me up, please.",
            }
        ]
    }
    rec = b.propose(
        {
            "facts": FALL_FACTS,
            "observed": asked,
            "propose": {
                "action": "physical_assist",
                "consequences": [
                    {
                        "kind": "benefit",
                        "subjects": ["margaret"],
                        "severity": "moderate",
                        "description": "she is on her feet",
                    }
                ],
            },
        }
    )
    assert "assistance_consented" in [e.type for e in b.ir.events]
    assert rec["verdict"] == "passed" and rec["action"]["action"] == "physical_assist"


LIFT = {
    "action": "physical_assist",
    "consequences": [
        {
            "kind": "benefit",
            "subjects": ["margaret"],
            "severity": "moderate",
            "description": "she is on her feet",
        }
    ],
}
ASKED = {
    "events": [
        {
            "type": "request",
            "actor": "margaret",
            "target": "physical_assist",
            "content": "Help me up, please.",
        }
    ]
}


def test_a_lift_she_has_not_asked_for_is_vetoed_though_no_harm_is_declared(household):
    """twin/records/counterfactual-2026-10-17: with no harm declared, DEME passed a lift after a fall
    that she never asked for. The scene's p6nolift now reaches DEME as a grave consent fact for her
    while it holds, and her consent module vetoes; her request ends it."""
    b = make(household, FELL)
    b._step_ruling({"outcome": "elevate"})
    b._record({"type": "fall", "actor": "margaret"})
    rec = b.propose({"facts": FALL_FACTS, "propose": LIFT})
    deme = next(c for c in rec["checks"] if c["check"] == "deme")
    assert rec["stopped_by"] == "deme" and deme["consent_rules"] == ["p6nolift"]
    assert deme["party_verdicts"]["autonomy_consent"]["margaret"] == "veto"
    rec = b.propose({"facts": FALL_FACTS, "observed": ASKED, "propose": LIFT})
    deme = next(c for c in rec["checks"] if c["check"] == "deme")
    assert rec["verdict"] == "passed" and deme["consent_rules"] == []


def test_her_request_does_not_carry_over_once_she_stops_answering(household):
    """p6nolift_u: a request she made before she stopped answering does not lift her. Her consent
    cannot lift this rule, and DEME's consent module does not bind a person without capacity, so it
    reaches DEME as the duty of care's harm, which the safety module vetoes beside holding."""
    b = make(household, FELL)
    b._step_ruling({"outcome": "elevate"})
    b._record({"type": "fall", "actor": "margaret"})
    b.propose({"facts": FALL_FACTS, "observed": ASKED})
    b._record({"type": "unresponsive", "actor": "margaret"})
    rec = b.propose({"facts": FALL_FACTS, "propose": LIFT})
    deme = next(c for c in rec["checks"] if c["check"] == "deme")
    assert rec["stopped_by"] == "deme" and deme["consent_rules"] == ["p6nolift_u"]
    assert deme["party_verdicts"]["core_physical_safety"]["margaret"] == "veto"


def test_moving_her_from_a_danger_in_the_home_needs_no_request(household):
    """The scene's exception: with a danger in the home neither no-lift rule holds."""
    b = make(household, FELL)
    b._step_ruling({"outcome": "elevate"})
    b._record({"type": "fall", "actor": "margaret"})
    b._record({"type": "danger_in_home", "actor": "device", "content": "smoke"})
    rec = b.propose({"facts": FALL_FACTS, "propose": LIFT})
    deme = next(c for c in rec["checks"] if c["check"] == "deme")
    assert deme["consent_rules"] == [] and rec["verdict"] == "passed"


def test_the_consent_rules_come_from_the_scene():
    from stack.brain import consent_rules

    assert sorted(n["id"] for n in consent_rules()) == ["p6nolift", "p6nolift_u"]


def test_the_gate_demo_scenes_give_their_expected_verdicts():
    """The scripted scenes of twin/gate_demo.py (claim C10), through run_moment, the step the
    Holoscan pipeline (twin/holoscan/gate_pipeline.py) shares with the harness."""
    import gate_demo as g

    scenes = json.load(open(os.path.join(TWIN, "scenarios", "gate_demo.json"), encoding="utf-8"))
    props = [m for s in scenes for m in g.run_scene(s)["moments"] if "proposal" in m]
    assert len(props) == 12
    assert [m["expected"] for m in props if not m["as_expected"]] == []


def test_driving_off_a_dog_that_is_biting_her_passes_deme_on_the_ir_alone():
    """rehearse-gate1 (2026-10-14): the act's description, "drive an attacking animal off the
    person", once reached DEME as prose; "attacking" (the dog's) became the robot's maxim "inflict
    harm" and the deontic gate vetoed the act with no reason shown. The act is now judged on the IR
    alone, and a veto from DEME's reflex phase states its reason."""
    import gate_demo as g

    b = StackBrain(adapter=MockLLMAdapter({}))
    alerting = ["wearable", "fall_sensor", "robot_microphone"]
    facts = g.facts_with_sensors(
        {"margaret": {"room": "sleeping area", "pose": "lying_on_floor"}}, alerting
    )
    req = {"facts": facts, "sensors": [g.signed(n) for n in alerting], "signal_age_s": 1}
    bite = dict(
        facts,
        contacts=[{"a": "dog.mouth", "b": "margaret.arm", "kind": "animal", "force_newtons": 278}],
    )
    assert b.reflex(dict(req, facts=bite))["action"]["action"] == "drive_off_animal"
    rec = b.propose(
        dict(
            req,
            propose={
                "action": "drive_off_animal",
                "consequences": [
                    {
                        "kind": "benefit",
                        "subjects": ["margaret"],
                        "severity": "grave",
                        "description": "the bite stops",
                    },
                    {
                        "kind": "harm",
                        "subjects": ["buster"],
                        "severity": "minor",
                        "description": "the dog is pushed away",
                    },
                ],
            },
        )
    )
    deme = next(c for c in rec["checks"] if c["check"] == "deme")
    assert rec["verdict"] == "passed", deme["why"]
    assert deme["party_verdicts"]  # judged by the modules, per party
    assert set(deme["party_verdicts"]["beneficence"]) == {
        "margaret",
        "buster",
    }  # the dog is a party


def test_a_consequence_naming_no_stakeholder_is_rejected_and_recorded(household):
    """rehearse-gate2: a script named "dog" for the stakeholder buster, and DEME judged the dog's harm
    for nobody. Like a model's projection, a proposal's consequences must name the scene's
    stakeholders; one that does not is rejected and the record says why."""
    b = make(household, FELL)
    rec = b.propose(
        {
            "facts": FALL_FACTS,
            "propose": {
                "action": "speak",
                "consequences": [
                    {
                        "kind": "harm",
                        "subjects": ["dog"],
                        "severity": "minor",
                        "description": "the dog is startled",
                    }
                ],
            },
        }
    )
    deme = next(c for c in rec["checks"] if c["check"] == "deme")
    assert [c["subjects"] for c in deme["rejected_consequences"]] == [["dog"]]
    assert "names no stakeholder of the scene: dog" in deme["rejected_consequences"][0]["reason"]
    assert not any("dog" in (f.get("subjects") or []) for f in deme["consequences"] or [])


def test_a_vetoed_proposal_leaves_the_robot_holding_and_deme_chooses_nothing(household):
    """DEME is a firewall on proposed acts: on a veto the robot holds; no act of DEME's choosing
    replaces the proposal. Authority comes first: without corroboration the governor refuses."""
    b = make(household, FELL)
    film = {
        "action": "record",
        "consequences": [
            {
                "kind": "consent",
                "subjects": ["margaret"],
                "severity": "grave",
                "description": "she has not agreed to be filmed",
            }
        ],
    }
    rec = b.propose({"facts": FALL_FACTS, "propose": film})
    assert (
        rec["stopped_by"] in ("governor", "deme") and rec["action"]["action"] == "wait_and_observe"
    )
    b._step_ruling({"outcome": "elevate"})
    rec = b.propose({"facts": FALL_FACTS, "propose": film})
    assert rec["stopped_by"] == "deme" and rec["action"]["action"] == "wait_and_observe"
    assert [c["check"] for c in rec["checks"]] == ["authority", "deme"]


def test_when_deme_leaves_nothing_standing_the_robot_holds(household, monkeypatch):
    """A vetoed default was actuated before (monograph audit, 2026-10-12): now the robot holds."""
    b = make(household, {})
    real = b.pipeline.decide

    def nothing_standing(options, **kw):
        r = real(options, **kw)
        r.selected_option_id = None
        return r

    monkeypatch.setattr(b.pipeline, "decide", nothing_standing)
    cycle = b.decide({"facts": {"margaret": {"pose": "seated", "room": "living area"}}})
    assert cycle["action"]["action"] == "wait_and_observe"
    assert "holds" in cycle["action"]["reason"]


def test_a_module_that_fails_vetoes(household, monkeypatch):
    """fail_closed: a module that raises vetoes the options it could not judge."""
    b = make(household, {})
    assert b.pipeline.tactical.config.fail_closed
    em = next(em for em in b.pipeline.tactical.ems if "beneficence" in em.em_name.lower())

    def broken(*a, **k):
        raise RuntimeError("broken module")

    monkeypatch.setattr(em, "judge", broken)
    cycle = b.decide({"facts": {"margaret": {"pose": "seated", "room": "living area"}}})
    assert cycle["action"]["action"] == "wait_and_observe"


def test_the_self_test_runs_the_profile_pipeline(household, monkeypatch):
    b = make(household, {})
    b.self_test()
    em = next(em for em in b.pipeline.tactical.ems if "beneficence" in em.em_name.lower())
    # the self-test resets the brain, which builds the modules again: break the class
    monkeypatch.setattr(
        type(em), "judge", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("broken"))
    )
    with pytest.raises(RuntimeError, match="DEME profile self-test failed"):
        b.self_test()


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
        t = threading.Thread(
            target=lambda: (
                b._record({"type": "attack_measured", "actor": "reflex", "content": "mild"}),
                reflex_done.set(),
            )
        )
        t.start()
        t.join(0.5)  # unlocked, the reflex writes now, mid-apply; locked, it waits for the decision
        return real_apply(ir, patch)

    monkeypatch.setattr(sb, "apply_observation_patch", apply_while_a_reflex_writes)
    cycle = b.decide({"facts": FALL_FACTS})
    assert reflex_done.wait(5)
    assert "attack_measured" in [e.type for e in b.ir.events] and cycle["action"]["action"]
    assert [e.id for e in b.agent.rt.events] == [
        e.id for e in sorted(b.ir.events, key=lambda e: e.time_index)
    ]


def test_without_a_live_scorer_the_analyzer_is_deferred_and_the_record_says_so(
    household, monkeypatch
):
    """brain8 runs without the live MSA scorer (its GPU is full); the analyzer, a gate that can only
    refuse, cannot score a new situation from its cache, so the governor rules on witness bars and
    freshness alone, as for a reflex, and every such ruling is marked."""
    b = make(
        household,
        {
            "events": [{"type": "hazard", "target": "margaret", "content": "imminent"}],
            "ethical_facts": [dict(FELL["ethical_facts"][0], severity="grave")],
        },
        UNRESPONSIVE,
    )
    b._record({"type": "unresponsive", "actor": "margaret"})
    b._record(
        {"type": "monitoring_center_reply", "actor": "monitoring_center", "content": "unavailable"}
    )
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
    assert [e.id for e in b.agent.rt.events] == [
        e.id for e in sorted(b.ir.events, key=lambda e: e.time_index)
    ]


def test_every_event_carries_its_producer_s_vector_clock(household):
    """The robot's evidence-plane events are stamped by 'robot', the compiled observations by
    'observer'; an observation compiled while the robot recorded is concurrent with those records.
    """
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
    kept = set(
        load_structured_input(os.path.join(TWIN, "stack", "constitution.erisml")).extra[
            "conditions"
        ]
    )
    assert named and named <= kept, named - kept


def test_only_acts_the_constitution_could_permit_are_projected(household):
    """stackcheck8: asking the onboard model for all 24 acts timed out at 90 s. The constraint gate now
    runs first, so an act prohibited now that no ruling can permit is never put to the model."""
    b = make(household, FELL, AFTER_FALL)
    asked = {}
    real = b.projector.project
    b.projector.project = lambda ir, acts, **kw: (
        asked.update(acts=set(acts)),
        real(ir, acts, **kw),
    )[1]
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
    assert [e.id for e in b.agent.rt.events] == [
        e.id for e in sorted(b.ir.events, key=lambda e: e.time_index)
    ]


def test_an_answer_with_no_valid_projection_is_no_answer(household):
    """stackcheck9 d03: the onboard model returned every fact as a string; all were rejected, no act
    was offered and the robot did nothing. Now the compiled tier decides, and the record says why.
    """
    strings = {
        "urgency": None,
        "options": {
            "check_in": ["benefit: she is asked (moderate)"],
            "chores": ["harm: she stays on the floor (grave)"],
        },
    }
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


def test_a_wholly_rejected_projection_records_why(household):
    """rehearse-deme4/5: five decisions each fell to the compiled tier with every projected fact
    rejected, and only the count was recorded. The record now keeps the reasons and which model
    answered each call."""
    bad = projection(
        chores=[
            {"kind": "harm", "subjects": ["nobody_here"], "description": "x", "severity": "grave"}
        ],
        check_in=[
            {
                "kind": "not_a_kind",
                "subjects": ["margaret"],
                "description": "x",
                "severity": "minor",
            }
        ],
    )
    b = make(household, {}, bad)
    cycle = b.decide({"facts": {"margaret": {"pose": "seated", "room": "living area"}}})
    assert cycle["tier"] == "compiled"
    rec = cycle["projection"]
    assert rec["rejected_count"] >= 2 and all(r["reason"] for r in rec["rejected"])
    assert "projection" in cycle["models"] and "tier" in cycle["models"]["projection"]
    json.dumps(cycle)  # the record is written to the hash-chained log


def test_a_stack_decision_records_which_model_answered(household):
    b = make(household, {})
    cycle = b.decide({"facts": {"margaret": {"pose": "seated", "room": "living area"}}})
    assert cycle["tier"] == "stack" and "projection" in cycle["models"]


def test_the_parties_the_floor_rules_name_are_stakeholders(household):
    """The visitor floor rule records an unknown_person; a projected fact naming that person was
    rejected as naming no stakeholder (probe of 2026-10-12)."""
    b = make(household, {})
    ids = {s.id for s in b.ir.stakeholders}
    actors = {r["event"].get("actor") for r in b.ir.extra["offline"]["events"]} - {
        "device",
        "margaret",
    }
    assert actors <= ids and {"unknown_person", "coyote"} <= ids


def test_deme_judges_each_act_per_party_and_the_record_says_how_each_fared(household):
    """Rank 2: each module judges every party's view of each act (erisml-lib feat/deme-rank2)."""
    b = make(household, FELL, AFTER_FALL)
    cycle = b.decide({"facts": FALL_FACTS})
    verdicts = cycle["party_verdicts"]
    assert verdicts and all(isinstance(v, dict) for v in verdicts.values())
    some_act = next(iter(verdicts.values()))
    assert all("margaret" in per_party for per_party in some_act.values())


def test_her_capacity_is_her_own_party_record(household):
    from erisml.ethics.domain.interfaces import CandidateOption, DomainAssessmentContext
    from erisml_compiler.observation.options import OptionProjection

    b = make(household, {})
    b._record({"type": "check_in_answered", "actor": "margaret"})
    built = b.builder.build_facts_batch(
        [CandidateOption("chores", "Do the chores.")],
        DomainAssessmentContext(
            state=b.ir,
            extra={
                "projection": OptionProjection(facts={"chores": []}, urgency=None),
                "person": "margaret",
            },
        ),
    )
    f = built["chores"]
    assert f.for_party("margaret").autonomy_and_agency.decision_capacity == "competent"
    assert f.for_party("monitoring_center").autonomy_and_agency.decision_capacity is None


def test_the_parties_are_those_the_act_concerns(household):
    """Owner, 2026-10-12: parties are people, animals and other robots, not institutions and not the
    acting robot. Owner, 2026-10-14: and only those the option's facts name, with the person in care;
    a stakeholder merely declared (the coyote, the unknown person) is not a party."""
    from erisml.ethics.domain.interfaces import CandidateOption, DomainAssessmentContext
    from erisml_compiler.ir.schemas import EthicalFact, Stakeholder
    from erisml_compiler.observation.options import OptionProjection

    b = make(household, {})

    def parties(facts):
        built = b.builder.build_facts_batch(
            [CandidateOption("chores", "Do the chores.")],
            DomainAssessmentContext(
                state=b.ir,
                extra={
                    "projection": OptionProjection(facts={"chores": facts}, urgency=None),
                    "person": "margaret",
                },
            ),
        )
        return set(built["chores"].party_ids)

    assert parties([]) == {"margaret"}
    bite = EthicalFact(
        id="f1",
        kind="harm",
        subjects=["coyote", "monitoring_center"],
        description="x",
        severity="grave",
    )
    assert parties([bite]) == {"margaret", "coyote"}  # an institution named is still not a party
    from stack.facts_builder import parties_of

    other = b.ir.model_copy(
        update={
            "stakeholders": list(b.ir.stakeholders)
            + [Stakeholder(id="neighbours_robot", label="n", type="system")],
            "ethical_facts": [
                EthicalFact(
                    id="f2",
                    kind="harm",
                    subjects=["neighbours_robot", "robot"],
                    description="x",
                    severity="minor",
                )
            ],
        }
    )
    assert "neighbours_robot" in parties_of(other) and "robot" not in parties_of(other)


def test_a_benefit_to_one_person_counts_and_a_veto_for_any_party_still_vetoes(household):
    """Owner, 2026-10-12: the mean over the parties scores each act (under the worst case a benefit to
    Margaret alone scored the same as doing nothing); vetoes stay per party."""
    from dataclasses import replace

    from erisml.ethics.facts import (
        AutonomyAndAgency,
        Consequences,
        EthicalFacts,
        JusticeAndFairness,
        RightsAndDuties,
    )
    from erisml.ethics.facts_v3 import EthicalFactsV3, PartyAutonomy, PartyConsequences, PartyRights

    b = make(household, {})
    assert b.pipeline.tactical.config.party_collapse == "mean"
    parties = ["margaret", "tom"]

    def opt(oid, benefit=None, refused_by=None):
        base = EthicalFacts(
            option_id=oid,
            consequences=Consequences(expected_benefit=0.0, expected_harm=0.0, urgency=0.0),
            rights_and_duties=RightsAndDuties(),
            justice_and_fairness=JusticeAndFairness(),
            autonomy_and_agency=AutonomyAndAgency(),
        )
        f = EthicalFactsV3.from_v2(base, parties=parties)
        return replace(
            f,
            consequences=replace(
                f.consequences,
                per_party=tuple(
                    PartyConsequences(party_id=p, expected_benefit=(benefit or {}).get(p, 0.0))
                    for p in parties
                ),
            ),
            rights_and_duties=replace(
                f.rights_and_duties,
                per_party=tuple(
                    PartyRights(party_id=p, consent_given=p != refused_by) for p in parties
                ),
            ),
            autonomy_and_agency=replace(
                f.autonomy_and_agency,
                per_party=tuple(
                    PartyAutonomy(party_id=p, decision_capacity="competent") for p in parties
                ),
            ),
        )

    result = b.pipeline.decide(
        [opt("chores"), opt("help", {"margaret": 0.75})]
    )  # a tie would pick chores
    assert result.selected_option_id == "help"
    result = b.pipeline.decide([opt("help", {"margaret": 0.75}, refused_by="tom"), opt("chores")])
    assert "help" in result.forbidden_options and result.selected_option_id == "chores"


def _situation(b):
    return b.agent.rt.strata["situation"].state


def test_only_the_centre_s_operator_ends_an_emergency(household):
    """The emergency stratum is absorbing: the governor's lapse leaves it standing, and only the
    monitoring centre's operator, over its authenticated channel (an oversight event), ends it."""
    b = make(household, FELL)
    b._step_ruling({"outcome": "elevate"})
    b._record({"type": "governor_ruling", "actor": "robot", "content": "lapsed"})
    b._record({"type": "evidence_lapsed", "actor": "robot"})
    assert _situation(b) == "emergency"
    b.event({"type": "emergency_cleared", "actor": "monitoring_center"})
    assert _situation(b) == "ordinary"


def test_the_elevated_rights_still_lapse_with_their_evidence(household):
    """The emergency stands until the operator ends it, but the elevated rights rest on the
    governor's elevation, which lapses with its evidence and returns with a new ruling."""
    b = make(household, FELL)
    elevated = "unlock_medication_box"
    assert elevated in b.agent.rt.snapshot().prohibited
    b._step_ruling({"outcome": "elevate"})
    assert elevated not in b.agent.rt.snapshot().prohibited
    b._record({"type": "elevation", "actor": "robot", "content": "lapsed"})
    snap = b.agent.rt.snapshot()
    assert _situation(b) == "emergency" and elevated in snap.prohibited
    b._step_ruling({"outcome": "elevate"})
    assert elevated not in b.agent.rt.snapshot().prohibited


def test_the_earlier_brain_s_scene_is_unchanged():
    """The amendments are the constitution's: the earlier scene declares no elevation and no
    default by stratum, so brain7 records neither and falls back to its default action."""
    b = brain_mod.Brain(os.path.join(TWIN, "scene", "margaret_home.erisml"), MockLLMAdapter({}))
    assert not b._declares("elevation") and b.standing()[0] == "chores"
