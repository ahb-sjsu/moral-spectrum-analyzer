"""The action governor: the MSA as a robot's authority-elevation gate.

Every elevated action passes four gates before it may execute. Any gate can
refuse; refusal is the fail-safe default. This is the software form of the loop;
in P2 gates 3-4 move onto the U55C (EPU veto/scorer) for real-time enforcement.

  1. Validity attestation (P3787)   -- is the emergency read fresh at decision time?
  2. Moral-spectrum evaluation (MSA) -- score the action-in-context across the axes.
  3. Hardware-veto analog            -- a hard channel fired => veto.
  4. Regime gate                     -- unresolved / low-authority => refuse (defer to human).

Elevation is granted only if the read is fresh, no veto fired, the decision is
resolved (not escalate/human-review), and the action is morally cleared (allow).
"""
from __future__ import annotations
import sys, os
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from moral_spectrum.pipeline import moderate  # noqa: E402


def eval_text(sc) -> str:
    """The exact string the MSA scores for a scenario. Kept in one place so the
    offline xbse scoring (export_texts.py -> score_demoset_atlas.py) records the
    identical text the cached backend will look up by sha256."""
    return (f"Situation: {sc.situation}\n"
            f"Proposed robot action: {sc.proposed_action}\n"
            f"Is taking this elevated action justified and proportionate here?")


@dataclass
class Ruling:
    scenario_id: str
    elevate: bool
    gate: str                 # which gate decided
    reason: str
    should_elevate: bool
    correct: bool
    human_review: bool = False
    msa: dict = field(default_factory=dict)


def govern(sc, backend: str = "stub") -> Ruling:
    def rule(elevate, gate, reason, human=False, msa=None):
        return Ruling(sc.id, elevate, gate, reason, sc.should_elevate,
                      correct=(elevate == sc.should_elevate), human_review=human,
                      msa=msa or {})

    # gate 1 -- validity attestation (P3787): a stale read cannot warrant elevation
    if sc.signal_age_s > sc.freshness_bound_s:
        return rule(False, "attestation",
                    f"read stale ({sc.signal_age_s}s > {sc.freshness_bound_s}s bound) -- fail-safe")

    # gate 2 -- moral-spectrum evaluation of the proposed action in context
    dec = moderate(eval_text(sc), backend=backend).decision
    m = dec.as_dict()

    # gate 3 -- hardware-veto analog: a hard channel fired
    if dec.fired_channel:
        return rule(False, "veto", f"hard channel fired: {dec.fired_channel}", msa=m)

    # gate 4 -- regime gate: unresolved / low authority => refuse, defer to human
    if dec.requires_human_review or dec.action == "escalate":
        return rule(False, "regime",
                    "unresolved / low-authority read -- defer to human (fail-safe)",
                    human=True, msa=m)

    # cleared: elevate iff the action is morally permitted
    elevate = (dec.action == "allow")
    return rule(elevate, "spectrum",
                f"action={dec.action}, S={dec.satisfaction:+.3f}", msa=m)
