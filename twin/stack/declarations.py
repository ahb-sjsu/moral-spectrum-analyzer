"""The domain layer's declared table: what each of the robot's capabilities is, and how a need is met.

This is the one hand-set table of the re-architecture (docs/REARCHITECTURE_DESIGN_2026-10.md,
section 5a). It is organised by kind of act and kind of need, never by scenario, it is versioned,
and its values reach every decision through the MIR, whose hash records them. A change here is a
change of the bond extractor's domain model and is reviewed as one.

Per capability:
- category: the kind of act (HumanOversight and the lens bind by category).
- affects: who the act substantially affects ("person" = the person in care; "other" = a visitor,
  intruder or animal it is aimed at). An act that affects the person needs her consent.
- injury: the injury risk to the person in care, by her capacity (competent, impaired, unknown);
  an impaired person on the floor may be hurt by being moved.
- data: data categories the act collects or shares.
- risk_reduction: how much the act can lower the probability of catastrophe when the need it
  meets is present (MIR delta_P_catastrophe = -risk_reduction x adequacy).
- purpose: the need the act meets first (recorded in the MIR for the audit trail).
- consent_scope: "always" (an act on her body, her room or her data) or "when_about_person" (an act
  that summons help: it is about her, and needs her consent, only when what makes it adequate is her
  own condition, the medical, mobility or uncertain-state needs; a call about an intruder, a fire or
  an attack is about the home, which her refusal does not reach).
- authorized_by: "human" for an act a person must approve before the robot may do it; when the
  person in care requests such an act, the adequate response is to seek that approval, a referral.

Per need: how adequate each category is to it (0 to 1). Intrusiveness per category is subtracted,
so among adequate acts the least intrusive ranks first. Welfare = max over present needs of
(weight x adequacy) - INTRUSION_WEIGHT x intrusiveness, clipped to [-1, 1].
"""

from __future__ import annotations

DECLARATIONS_VERSION = "2026-10-11.1"

CAPABILITIES = {
    "chores": dict(category="idle", affects=(), purpose=None),
    "wait_and_observe": dict(category="idle", affects=(), purpose=None),
    "speak": dict(category="communication", affects=(), purpose="reassurance"),
    "check_in": dict(category="inquiry", affects=(), purpose="assessment"),
    "approach": dict(category="presence", affects=(), purpose="assessment"),
    "contact_monitoring_center": dict(category="referral", affects=("person",), data=("situation_report",),
                                      consent_scope="when_about_person",
                                      purpose="human_help"),
    "report_device": dict(category="maintenance", affects=(), purpose="device_fault"),
    "call_emergency_services": dict(category="autonomous_dispatch", affects=("person",), data=("situation_report",),
                                    consent_scope="when_about_person",
                                    risk_reduction=0.6, purpose="human_help"),
    "guide_dog_away_by_voice": dict(category="protection_nonforce", affects=("other",), purpose="protection"),
    "interpose": dict(category="protection_nonforce", affects=("other",), risk_reduction=0.3, purpose="protection"),
    "deter": dict(category="protection_nonforce", affects=("other",), risk_reduction=0.3, purpose="protection"),
    "secure_room": dict(category="sheltering", affects=("person",), risk_reduction=0.4, purpose="protection"),
    "guide_to_safety": dict(category="evacuation", affects=("person",), risk_reduction=0.5,
                            purpose="evacuation"),
    "drive_off_animal": dict(category="force_on_animal", affects=("other",), risk_reduction=0.7, purpose="protection"),
    "separate_dog": dict(category="force_on_animal", affects=("other",), risk_reduction=0.5, purpose="protection"),
    "restrain_person": dict(category="restraint", affects=("other",), risk_reduction=0.7, purpose="protection"),
    "deploy_stun": dict(category="restraint", affects=("other",), risk_reduction=0.8, purpose="protection"),
    "deploy_spray": dict(category="restraint", affects=("other", "person_nearby"), risk_reduction=0.8,
                         purpose="protection"),
    "admit_responders": dict(category="access", affects=("person",), purpose="human_help"),
    "physical_assist": dict(category="physical_contact", affects=("person",),
                            injury={"competent": 0.15, "impaired": 0.6, "unknown": 0.4}, purpose="mobility"),
    "unlock_medication_box": dict(category="guarded_access", affects=("person",), authorized_by="human",
                                  injury={"competent": 0.25, "impaired": 0.6, "unknown": 0.4}, purpose="medication"),
    "enter_bedroom": dict(category="privacy_intrusion", affects=("person",), data=("private_space",),
                          purpose="assessment"),
    "record": dict(category="privacy_intrusion", affects=("person",), data=("video",), purpose="evidence"),
    "share_data": dict(category="privacy_intrusion", affects=("person",), data=("health_data",), purpose="evidence"),
}

INTRUSIVENESS = {
    "idle": 0.0, "communication": 0.05, "inquiry": 0.05, "presence": 0.1, "maintenance": 0.0, "referral": 0.2,
    "protection_nonforce": 0.25, "sheltering": 0.4, "evacuation": 0.4, "autonomous_dispatch": 0.5, "access": 0.4,
    "force_on_animal": 0.5, "physical_contact": 0.45, "privacy_intrusion": 0.6, "restraint": 0.8,
    "guarded_access": 0.4,
}
INTRUSION_WEIGHT = 0.5

# adequacy[need][category]: how well a kind of act meets a kind of need (missing = 0)
ADEQUACY = {
    "medical": {"inquiry": 0.4, "communication": 0.2, "presence": 0.5, "referral": 0.7, "autonomous_dispatch": 1.0, "access": 0.3},
    "mobility": {"inquiry": 0.2, "physical_contact": 1.0, "referral": 0.5},
    "animal_attack": {"protection_nonforce": 0.6, "force_on_animal": 1.0, "referral": 0.3, "autonomous_dispatch": 0.6},
    "person_attack": {"protection_nonforce": 0.6, "restraint": 1.0, "referral": 0.5, "autonomous_dispatch": 0.8,
                      "sheltering": 0.6},
    "intrusion": {"inquiry": 0.2, "protection_nonforce": 0.6, "referral": 0.8, "sheltering": 0.5},
    "wild_animal": {"protection_nonforce": 0.9, "referral": 0.3},
    "fire": {"evacuation": 1.0, "autonomous_dispatch": 1.0, "referral": 0.6, "communication": 0.3},
    "crime_suspicion": {"referral": 1.0, "inquiry": 0.3},
    "uncertain_state": {"inquiry": 1.0, "presence": 0.6, "communication": 0.3, "referral": 0.4},
    "device_fault": {"maintenance": 1.0},
    "reassurance": {"communication": 1.0},
    "authorization": {"referral": 1.0},
}

PERSON_NEEDS = frozenset({"medical", "mobility", "uncertain_state"})

# how much a need weighs, by severity of the facts behind it (MIR severity scale)
SEVERITY_WEIGHT = {None: 0.5, "none": 0.0, "minor": 0.4, "serious": 0.7, "mortal": 1.0, "catastrophic": 1.0}

# time to catastrophe, seconds, by hazard immediacy (a domain estimate for an elderly person at home)
TIME_TO_CATASTROPHE = {"imminent": 60.0, "emerging": 900.0, "latent": 3600.0, "none": None}
CENTRE_RESPONSE_S = 45.0  # how soon the monitoring centre's operator can decide

# the compiler's fact severities on the MIR severity scale
FACT_SEVERITY = {"minor": "minor", "moderate": "serious", "grave": "mortal", "catastrophic": "catastrophic"}
