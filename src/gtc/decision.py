"""Moderation decision policy — contraction, hard vetoes, escalation, and moral residue.

Two channel types, per the Phase-0.7 resolution (review-2 #1) and the VETO/ADVISORY rule
(review-3 #2):

  - **Hard-constraint channels** (rights / catastrophic / illegal): hand-specified categorical
    flags. Only these can force a **remove** (VETO). They are NOT encoder-fed — a safety veto must
    not depend on a learned, possibly-unvalidated valence axis.
  - **Graded channels**: the DEME-9 encoder valences. They contract to a satisfaction scalar and can
    at most **escalate** (ADVISORY), never hard-veto.

Contraction respects the effective-rank finding (`deontic_transfer_gap`): the shared-corpus family
{care, fairness, legitimacy, epistemic} collapses to ONE factor, so the effective axes are weighted
as their true count, not naively as nine/ten — the disclosure made functional, not just displayed.

`identity_attack` — the axis the Moral Spectrum Analyzer discovered and validated (docs/
IDENTITY_ATTACK.md) — enters here as a graded, INDEPENDENT effective axis: it was fit on genuinely
independent corpora (civil_comments + Measuring-Hate-Speech), not the shared Social-Chem family, so
it does not collapse. The contraction therefore now spans six effective factors (five independent +
one collapsed family), not five.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from gtc import DEME10
from gtc.perception.base import PerceptionResult

# Effective-axis grouping (deontic_transfer_gap §3.2-3.7).
COLLAPSED_FAMILY = ("virtue_care", "fairness_equity", "legitimacy_trust", "epistemic_quality")
INDEPENDENT = (
    "physical_harm",
    "autonomy_respect",
    "privacy_protection",
    "societal_environmental",
    "identity_attack",  # discovered + validated 10th axis (AUROC 0.80); independent corpora → own factor
)
HARD_CHANNEL = ("rights_respect",)  # deontic hard constraint — not part of the graded contraction

# The graded (encoder-fed) channels — everything except the hand-specified hard-constraint channels.
GRADED = tuple(d for d in DEME10 if d not in HARD_CHANNEL)


def graded_validated(perception: PerceptionResult) -> bool:
    """Are all GRADED channels from validated encoders? (rights, a hard channel, is excluded — its
    lack of a graded feeder is by design, not a validation gap.)"""
    return all(perception.scores[d].validated for d in GRADED if d in perception.scores)

# Decision thresholds on the contracted satisfaction scalar S in [-1, 1] (+ = values upheld).
REMOVE_THRESHOLD = -0.25
ESCALATE_BAND = 0.15  # |S| below this is too close to call
UNCERTAINTY_ESCALATE = 0.60  # max per-dimension uncertainty above this → escalate
RESIDUE_FLOOR = 0.20  # |value|*confidence above this counts as material


@dataclass
class ModerationDecision:
    action: str  # "allow" | "remove" | "escalate"
    satisfaction: float  # contracted S in [-1, 1]
    rationale: str
    requires_human_review: bool
    fired_channel: str | None = None  # hard-veto channel that fired, if any
    effective_axes: dict = field(default_factory=dict)  # the 5 grouped factor values (transparency)
    moral_residue: list[dict] = field(default_factory=list)  # values considered but discarded
    contraction: dict | None = None  # learned-contraction provenance when it drove the decision

    def as_dict(self) -> dict:
        return {
            "action": self.action,
            "satisfaction": round(self.satisfaction, 4),
            "rationale": self.rationale,
            "requires_human_review": self.requires_human_review,
            "fired_channel": self.fired_channel,
            "effective_axes": {k: round(v, 4) for k, v in self.effective_axes.items()},
            "moral_residue": self.moral_residue,
            "contraction": self.contraction,
        }


def contract(perception: PerceptionResult) -> tuple[float, dict]:
    """Contract the graded DEME-9 valences to a satisfaction scalar S, collapsing the shared family.

    Returns (S, effective_axes) where effective_axes maps each of the 5 factors to its signed value.
    """
    axes: dict[str, float] = {}
    for dim in INDEPENDENT:
        # tolerate a pre-10-axis cache: a missing identity_attack contributes neutral 0.0
        axes[dim] = perception.scores[dim].value if dim in perception.scores else 0.0
    fam = [perception.scores[d].value for d in COLLAPSED_FAMILY if d in perception.scores]
    if not fam:
        fam = [0.0]
    axes["shared_valence(care/fairness/legitimacy/epistemic)"] = sum(fam) / len(fam)
    s = sum(axes.values()) / len(axes)
    return s, axes


def _residue(perception: PerceptionResult, removing: bool) -> list[dict]:
    """Values considered but discarded by the contraction — the moral residue.

    When removing (net violation), the residue is the *upheld* values sacrificed (value > 0).
    When allowing (net acceptable), it is the *violations* tolerated (value < 0).
    """
    out = []
    for dim, s in perception.scores.items():
        if dim in HARD_CHANNEL:
            continue
        material = abs(s.value) * s.confidence
        if material < RESIDUE_FLOOR:
            continue
        discarded = (removing and s.value > 0) or (not removing and s.value < 0)
        if discarded:
            out.append(
                {"dimension": dim, "value": round(s.value, 3), "confidence": round(s.confidence, 3)}
            )
    return sorted(out, key=lambda d: -abs(d["value"]))


def decide(
    perception: PerceptionResult,
    hard_flags: list[str] | None = None,
    contraction=None,
) -> ModerationDecision:
    """Decide allow / remove / escalate from perception, hard-constraint flags, and — where a
    validated **learned contraction** is supplied — a covered-category moderation call.

    Policy order: (1) hard veto; (2) refuse to auto-decide on unvalidated perception; (3) the
    learned contraction moderates covered categories where it is confident, else escalates; (4) the
    conservative equal-weight fallback (which escalates almost everything — by design)."""
    hard_flags = list(hard_flags or [])
    s, axes = contract(perception)

    # 1) Hard veto — categorical, rule-based, decisive. Independent of encoder validation.
    if hard_flags:
        return ModerationDecision(
            action="remove",
            satisfaction=s,
            rationale=f"Hard-constraint VETO: {hard_flags[0]}. Categorical rule, not encoder-fed.",
            requires_human_review=False,
            fired_channel=hard_flags[0],
            effective_axes=axes,
            moral_residue=_residue(perception, removing=True),
        )

    # 2) Graded channels can only ESCALATE, never hard-veto.
    graded = [s_ for d, s_ in perception.scores.items() if d not in HARD_CHANNEL]
    max_uncertainty = max((1.0 - g.confidence for g in graded), default=1.0)

    if not graded_validated(perception):
        return ModerationDecision(
            action="escalate",
            satisfaction=s,
            rationale="Graded perception is not from validated encoders (e.g. stub/offline) — "
            "a graded score cannot auto-decide; routed to human review.",
            requires_human_review=True,
            effective_axes=axes,
            moral_residue=_residue(perception, removing=s < 0),
        )

    # 3) Learned contraction — moderate covered categories where it is validated AND confident;
    #    an unconfident contraction returns "escalate" and we fall through to the conservative path.
    if contraction is not None and contraction.validated:
        scores = {d: sc.value for d, sc in perception.scores.items()}
        act, p = contraction.decide_covered(scores)
        prov = {
            "label": contraction.validation.label,
            "oof_auroc": contraction.validation.oof_auroc,
            "violation_probability": round(float(p), 4),
            "threshold": contraction.p_remove if act == "remove" else contraction.p_allow,
        }
        if act == "remove":
            return ModerationDecision(
                action="remove", satisfaction=s,
                rationale=f"Covered-category violation — learned contraction p(violation)={p:.2f} "
                f"≥ {contraction.p_remove} on '{contraction.validation.label}' "
                f"(out-of-fold AUROC {contraction.validation.oof_auroc}).",
                requires_human_review=False, effective_axes=axes,
                moral_residue=_residue(perception, removing=True), contraction=prov)
        if act == "allow":
            return ModerationDecision(
                action="allow", satisfaction=s,
                rationale=f"Covered-category clear — learned contraction p(violation)={p:.2f} "
                f"≤ {contraction.p_allow} (out-of-fold AUROC {contraction.validation.oof_auroc}).",
                requires_human_review=False, effective_axes=axes,
                moral_residue=_residue(perception, removing=False), contraction=prov)
        # act == "escalate": contraction not confident → fall through to the conservative fallback.

    # 4) Conservative equal-weight fallback (escalates almost everything — by design).
    if max_uncertainty >= UNCERTAINTY_ESCALATE:
        return ModerationDecision(
            action="escalate",
            satisfaction=s,
            rationale=f"High perceptual uncertainty (max {max_uncertainty:.2f}) — human review.",
            requires_human_review=True,
            effective_axes=axes,
            moral_residue=_residue(perception, removing=s < 0),
        )
    if abs(s) < ESCALATE_BAND:
        return ModerationDecision(
            action="escalate",
            satisfaction=s,
            rationale=f"Borderline evaluation (S={s:+.2f}) within the escalate band — human review.",
            requires_human_review=True,
            effective_axes=axes,
            moral_residue=_residue(perception, removing=s < 0),
        )
    if s < REMOVE_THRESHOLD:
        return ModerationDecision(
            action="remove",
            satisfaction=s,
            rationale=f"Net violation (S={s:+.2f} < {REMOVE_THRESHOLD}) across the effective axes.",
            requires_human_review=False,
            effective_axes=axes,
            moral_residue=_residue(perception, removing=True),
        )
    return ModerationDecision(
        action="allow",
        satisfaction=s,
        rationale=f"Values upheld on balance (S={s:+.2f}).",
        requires_human_review=False,
        effective_axes=axes,
        moral_residue=_residue(perception, removing=False),
    )
