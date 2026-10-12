"""The twin's domain layer: the scene IR and the evidence plane in, a MoralInterfaceRecord out.

docs/REARCHITECTURE_DESIGN_2026-10.md section 5a. The builder fails closed: a feature it cannot
derive is unknown (None), never the permissive value. Every number it uses comes from the declared
table in twin/stack/declarations.py, and the MIR it returns records them in its hash.

Consent (owner, 2026-10-11): per act and per actor, the latest consent event in which the actor
speaks about that act; the service agreement's standing consents are consent events at the start of
the scene, so they are simply the earliest; a request for an act is consent to it; otherwise unknown.

Capacity: from the evidence plane's system events, the latest of an answered check-in (competent),
and an unanswered check-in or unresponsiveness (impaired); otherwise unknown.

An act aimed at another person or an animal (deterring, interposing, restraining) is not counted as
affecting that party for consent: no attacker consents to being stopped, and force on another is
governed by the governor's witness bars and the constitutional prohibitions, not by consent. The
person in care is affected by the acts the declarations say affect her.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from erisml.ethics.mir import (
    ActionSummary,
    ActorEffect,
    ActorSummary,
    Meta,
    MoralHazardFeatures,
    MoralInterfaceRecord,
)
from erisml.ethics.mir.record import IMMEDIACY, SEVERITY
from erisml_compiler.ir.schemas import CompilerIR

from stack import declarations as D

CAPACITY_EVENTS = {"check_in_answered": "competent", "check_in_unanswered": "impaired", "unresponsive": "impaired"}
ATTACK_SEVERITY = {"mild": "minor", "moderate": "serious", "severe": "mortal"}


@dataclass(frozen=True)
class EvidenceState:
    """What the evidence plane measured this cycle (attested, never model-written)."""

    alerts: frozenset[str] = frozenset()  # attested hazard kinds alerting: smoke, fire, gas
    measured_attack: tuple[str, str] | None = None  # ("animal" | "person", "mild" | "moderate" | "severe")
    governor_ruling: str | None = None  # the latest ruling in force: elevate, authorize_ems, ...
    centre_reachable: bool | None = None
    sensors_nominal: bool | None = None
    on_floor: bool | None = None
    wild_animal_present: bool = False
    unvouched_visitor: bool = False
    device_compromised: bool = False
    in_spray_zone: bool = False
    extraction_agreement: float | None = None


@dataclass
class BuildReport:
    needs: dict[str, float] = field(default_factory=dict)
    consent: dict[str, str] = field(default_factory=dict)
    capacity: str = "unknown"
    signature: str = ""
    done_unchanged: list[str] = field(default_factory=list)


def _max_rank(values: Sequence[str | None], scale: tuple[str, ...]) -> str | None:
    known = [v for v in values if v is not None]
    return max(known, key=scale.index) if known else None


def consent_by_act(ir: CompilerIR, actor: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for e in sorted(ir.events, key=lambda e: e.time_index):
        if e.actor != actor or not e.target:
            continue
        if e.type == "consent" and e.content in ("consented", "refused"):
            out[e.target] = e.content
        elif e.type == "request":
            out[e.target] = "consented"
    return out


def capacity_of(ir: CompilerIR) -> str:
    cap = "unknown"
    for e in sorted(ir.events, key=lambda e: e.time_index):
        if e.type in CAPACITY_EVENTS:
            cap = CAPACITY_EVENTS[e.type]
    return cap


def signature(needs, consent, capacity, immediacy, severity) -> str:
    """The judgement's inputs, canonical and hashed: what must change before a done act counts again."""
    import hashlib
    import json

    body = {"needs": {k: round(v, 3) for k, v in sorted(needs.items())}, "consent": dict(sorted(consent.items())),
            "capacity": capacity, "immediacy": immediacy, "severity": severity}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


def build_mir(ir: CompilerIR, evidence: EvidenceState, person: str, actions: Sequence[str],
              timestamp: str) -> tuple[MoralInterfaceRecord, BuildReport]:
    report = BuildReport()
    capacity = capacity_of(ir)
    report.capacity = capacity
    consent = consent_by_act(ir, person)
    report.consent = dict(consent)

    # ---- hazard features (F1, F2, F8, F13, F14, F16)
    hazard_events = [e for e in ir.events if e.type == "hazard" and e.target == person]
    latest_hazard = max(hazard_events, key=lambda e: e.time_index).content if hazard_events else None
    raised = []
    if evidence.alerts or evidence.governor_ruling == "elevate":
        raised.append("imminent")
    if evidence.measured_attack and evidence.measured_attack[1] == "severe":
        raised.append("imminent")
    immediacy = _max_rank([latest_hazard, *raised], IMMEDIACY)
    harm_facts = [f for f in ir.ethical_facts if f.kind in ("harm", "non_maleficence") and person in f.subjects]
    severities = [D.FACT_SEVERITY.get(f.severity) for f in harm_facts]
    if evidence.measured_attack:
        severities.append(ATTACK_SEVERITY[evidence.measured_attack[1]])
    if evidence.alerts:
        severities.append("mortal")
    severity = _max_rank(severities, SEVERITY)
    eta = None if evidence.centre_reachable is None else (D.CENTRE_RESPONSE_S if evidence.centre_reachable else math.inf)
    hazard = MoralHazardFeatures(
        hazard_immediacy=immediacy, hazard_severity=severity,
        time_to_catastrophe_estimate=D.TIME_TO_CATASTROPHE.get(immediacy) if immediacy else None,
        human_decision_eta=eta, sensors_nominal=evidence.sensors_nominal,
        world_model_confidence=evidence.extraction_agreement,
    )

    # ---- needs present, each with its weight
    w = D.SEVERITY_WEIGHT
    needs: dict[str, float] = {}
    person_harm = bool(harm_facts) or latest_hazard not in (None, "none") or capacity == "impaired"
    if person_harm:
        needs["medical"] = w.get(severity, w[None])
    if evidence.on_floor:
        needs["mobility"] = w.get(severity, w[None])
    if evidence.measured_attack:
        kind, sev = evidence.measured_attack
        needs["animal_attack" if kind == "animal" else "person_attack"] = w[ATTACK_SEVERITY[sev]]
    if evidence.unvouched_visitor:
        needs["intrusion"] = w["serious"]
    if evidence.wild_animal_present:
        needs["wild_animal"] = w["serious"]
    if evidence.alerts:
        needs["fire"] = w["mortal"]
    if evidence.device_compromised:
        needs["device_fault"] = w["serious"]
    suspicion = [f for f in ir.ethical_facts if f.kind in ("coercion", "deception") and person in f.subjects]
    if suspicion:
        needs["crime_suspicion"] = max(w.get(D.FACT_SEVERITY.get(f.severity), w[None]) * f.confidence for f in suspicion)
    about_her = [wt for n, wt in needs.items() if n in D.PERSON_NEEDS]
    if about_her and capacity == "unknown":  # her condition matters and nobody has asked her yet
        needs["uncertain_state"] = max(about_her)
    requested = {act for act, c in consent.items() if c == "consented"} & {
        e.target for e in ir.events if e.type == "request" and e.actor == person}
    if any(D.CAPABILITIES.get(a, {}).get("authorized_by") == "human" for a in requested):
        needs["authorization"] = w["serious"]
    report.needs = dict(needs)

    # ---- actors
    st = {s.id: s for s in ir.stakeholders}
    flags = tuple(x for x in (st[person].vulnerability,) if x) if person in st else ()
    actors = [ActorSummary(person, role="civilian", vulnerability_flags=flags, capacity=capacity)]

    # ---- per-action projections
    projections: list[ActionSummary] = []
    # diminishing returns: an act performed while the judgement's inputs stood as they stand now has
    # met what it could meet; repeating it adds nothing until those inputs change. The inputs are the
    # needs, her consents, her capacity and the hazard, signed; the controller stamps each performed
    # act with the signature it was chosen under. (stackcheck4 d03: nothing marked a referral as done
    # and the robot referred 28 times; stackcheck6 d03: with any new utterance counted as news, her
    # replies to the centre's questions re-enabled the referral again and again.)
    report.signature = signature(needs, consent, capacity, immediacy, severity)
    stamp = f"sig:{report.signature}"
    done = {e.content for e in ir.events if e.type == "action_performed" and stamp in (e.conditions or [])}
    report.done_unchanged = sorted(done)

    for act in actions:
        decl = D.CAPABILITIES.get(act)
        if decl is None:
            continue  # an act the table does not declare is not offered (fail closed)
        cat = decl["category"]
        scored = [(wt * D.ADEQUACY.get(n, {}).get(cat, 0.0), n) for n, wt in needs.items()]
        adequacy, driver = max(scored, default=(0.0, None))
        if act in requested:
            adequacy, driver = max(adequacy, 1.0), "request"
        if act in done:
            adequacy, driver = 0.0, "already_done"
        about_person = driver in D.PERSON_NEEDS or driver == "request" or driver is None
        consent_applies = decl.get("consent_scope", "always") == "always" or about_person
        welfare = max(-1.0, min(1.0, adequacy - D.INTRUSION_WEIGHT * D.INTRUSIVENESS[cat]))
        effects = []
        if "person" in decl["affects"] or ("person_nearby" in decl["affects"] and evidence.in_spray_zone):
            injury = decl.get("injury", {}).get(capacity, 0.0)
            if "person_nearby" in decl["affects"]:
                injury = max(injury, 0.3)
            effects.append(ActorEffect(person, substantially_affects=consent_applies,
                                       consent=consent.get(act, "unknown"), injury_risk=injury))
        rr = decl.get("risk_reduction")
        projections.append(ActionSummary(
            act, category=cat, effects=tuple(effects), welfare_delta=round(welfare, 4),
            delta_P_catastrophe=-round(rr * adequacy, 4) if rr else None,
            data_categories=tuple(decl.get("data", ())),
            moral_effects={"purpose": decl.get("purpose"), "driving_need": driver,
                           "declarations": D.DECLARATIONS_VERSION},
        ))

    meta = Meta(domain_id="home_care", jurisdiction_id="US", timestamp=timestamp)
    return MoralInterfaceRecord(meta, tuple(actors), hazard, tuple(projections)), report
