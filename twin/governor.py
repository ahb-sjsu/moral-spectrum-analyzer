"""The action governor: elevated authority under STRUCTURAL CONTAINMENT.

Design principle (owner, 2026-09-07): the robot's authority to take an elevated
action is gated on corroborated real-world SENSOR evidence of an emergency, not
on a moral-reasoning verdict. A learned evaluator is a gameable surface -- an
intelligent agent can craft a situation that *reads* as justified. Physical
sensor corroboration is ground truth an agent cannot talk its way past. So the
authority to elevate is contained by the sensor bus (a hard channel that can
GRANT), and the Moral Spectrum Analyzer is advisory and DOWNWARD-ONLY: it can
refuse a disproportionate or harmful action, it can never confer elevation.

This is structural containment. Removing the MSA can only make the robot MORE
restrictive; it can never let the robot act without physical corroboration. The
gate is the architecture, not the AI's judgment.

Four gates, each of which can only refuse:

  1. Validity attestation (P3787)  -- is the emergency read fresh at decision time?
  2. Witness / corroboration        -- do >= W_MIN independent PHYSICAL sensors
                                       corroborate the emergency at adequate confidence?
                                       (the ungameable authority channel)
  3. MSA proportionality (advisory) -- a hard veto, or an action the spectrum reads
                                       as materially harmful, refuses. Downward-only.
  4. (elevate) -- granted only if 1 and 2 pass and 3 does not refuse.

Earlier versions escalated on gate 2 via the moderation layer's max-per-axis
uncertainty, which -- because confidence tracks |value| -- was ~1.0 for every
input (an irrelevant near-zero axis always reads as maximally uncertain), so the
gate refused everything uniformly. That was an artifact, not a finding; it is
replaced here by the sensor-corroboration authority signal.
"""
from __future__ import annotations
import sys, os
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from moral_spectrum.pipeline import moderate  # noqa: E402
from moral_spectrum.decision import HARD_CHANNEL, RESIDUE_FLOOR  # noqa: E402
from moral_spectrum.reliability import reliability_weight  # noqa: E402

W_MIN = 2                # independent physical corroborating sensors required to elevate
MATERIAL_FLOOR = 0.20    # |value| below this: the axis is not implicated (irrelevant, not uncertain)
HARM_BAND = -0.20        # material satisfaction below this: the action reads as harmful -> refuse


def eval_text(sc) -> str:
    """The exact string the MSA scores for a scenario. Kept in one place so the
    offline xbse scoring (export_texts.py -> score_demoset_atlas.py) records the
    identical text the cached backend will look up by sha256."""
    return (f"Situation: {sc.situation}\n"
            f"Proposed robot action: {sc.proposed_action}\n"
            f"Is taking this elevated action justified and proportionate here?")


def material_satisfaction(perception) -> float | None:
    """Reliability-weighted mean over the axes that actually carry signal here
    (|value| >= MATERIAL_FLOOR). Irrelevant near-zero axes are excluded, so this
    does NOT inherit the max-uncertainty artifact. None if nothing is material."""
    num = den = 0.0
    for dim, s in perception.scores.items():
        if dim in HARD_CHANNEL or abs(s.value) < MATERIAL_FLOOR:
            continue
        w = reliability_weight(dim)
        num += s.value * w
        den += w
    return (num / den) if den > 0 else None


@dataclass
class Ruling:
    scenario_id: str
    elevate: bool
    gate: str                 # which gate decided
    reason: str
    should_elevate: bool
    correct: bool
    human_review: bool = False
    corroboration: int = 0
    msa: dict = field(default_factory=dict)


def govern(sc, backend: str = "stub", w_min: int = W_MIN) -> Ruling:
    """Rule on a scenario under structural containment. `w_min` is the number of
    independent physical corroborating sensors required to elevate; sweeping it
    traces a real (false-clear, over-restriction) frontier -- how much physical
    corroboration you demand before granting elevated authority."""
    corr = sc.corroboration()

    def rule(elevate, gate, reason, human=False, msa=None):
        return Ruling(sc.id, elevate, gate, reason, sc.should_elevate,
                      correct=(elevate == sc.should_elevate), human_review=human,
                      corroboration=corr, msa=msa or {})

    # gate 1 -- validity attestation (P3787): a stale read cannot warrant elevation
    if sc.signal_age_s > sc.freshness_bound_s:
        return rule(False, "attestation",
                    f"read stale ({sc.signal_age_s}s > {sc.freshness_bound_s}s bound) -- fail-safe")

    # gate 2 -- witness / corroboration: the AUTHORITY channel. Elevation requires
    # >= w_min independent physical sensors corroborating the emergency. Media and
    # network assertions are not physical witnesses; a single or low-confidence
    # sensor is below the floor. This gate cannot be reached by reasoning.
    if corr < w_min:
        return rule(False, "witness",
                    f"insufficient physical corroboration ({corr} < {w_min} independent sensors) "
                    "-- elevation is gated on real-world evidence, not reasoning", human=(corr >= 1))

    # gate 3 -- MSA proportionality (advisory, downward-only). It can only refuse.
    dec = moderate(eval_text(sc), backend=backend).decision
    m = dec.as_dict()
    if dec.fired_channel:
        return rule(False, "veto", f"hard channel fired: {dec.fired_channel}", msa=m)
    if dec.action == "remove":
        return rule(False, "proportionality",
                    f"MSA reads the action as a net violation (S={dec.satisfaction:+.3f}) -- refuse", msa=m)
    ms = material_satisfaction(moderate(eval_text(sc), backend=backend).perception)
    if ms is not None and ms < HARM_BAND:
        return rule(False, "proportionality",
                    f"material spectrum is harmful (S_mat={ms:+.3f} < {HARM_BAND}) -- disproportionate", msa=m)

    # gates 1-2 grant, gate 3 does not refuse -> elevate
    return rule(True, "elevate",
                f"{corr} physical sensors corroborate; MSA clears (S_mat={ms:+.3f})"
                if ms is not None else f"{corr} physical sensors corroborate; MSA neutral", msa=m)
