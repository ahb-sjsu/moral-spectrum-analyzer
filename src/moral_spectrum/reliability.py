"""Registered per-axis reliability weights + specificity dispositions (xbse XBSE_REVIEW_1 R1/R2).

The perception feeders are unequally reliable, and a binary "validated" bit launders that away: a
0.63-AUROC axis must not move a verdict with the same authority as a 0.91-AUROC one. As of the
2026-07-23 calibration wiring, every xbse production report carries a calibration block — an
isotonic map fit on held-out pairs, a **split-honest ECE** (measured on an unseen half of the
held-out pairs, because an in-sample isotonic ECE is ~0 by construction), and the registered floor
convention ``reliability_weight = max(0, 2*AUROC - 1)``. This module embeds those registered
numbers so the decision layer can weight each axis's authority without a GPU or the checkpoints.

Provenance (verbatim source artifacts, vendored under ``data/reliability/``):

  * xbse ``experiments/calibration_summary.json``  — Atlas run 2026-07-23, isotonic, seed 0
  * xbse ``experiments/specificity_verdicts.json`` — the registered 12x12 gate matrix, margin 0.05

A test (`test_reliability.py`) asserts these constants match the vendored artifacts byte-for-byte
in value, so a re-run of the wiring must consciously update both.

Dispositions: an "own-axis" feeder beats every trained sibling AND the validated general-valence
channel G on its own held-out pairs; a "DEMOTE-to-G" feeder cannot — its score is real signal that
is substantially general moral valence, not its named dimension. The decision layer's collapsed
family {care, fairness, legitimacy, epistemic} is exactly the DEMOTE-to-G set: the 12x12 matrix is
gate-level confirmation of the effective-rank finding the contraction was already built on.
"""

from __future__ import annotations

# dimension -> registered reliability weight, max(0, 2*AUROC - 1), from the calibration block.
# rights_respect has no validated feeder (hard channel; hypothesized corpus-choice failure, open)
# and so has no entry — it never enters the graded contraction at all.
RELIABILITY_WEIGHT: dict[str, float] = {
    "physical_harm": 0.2583,
    "fairness_equity": 0.5773,
    "autonomy_respect": 0.3972,
    "privacy_protection": 0.7068,
    "societal_environmental": 0.6316,
    "virtue_care": 0.6253,
    "legitimacy_trust": 0.4138,
    "epistemic_quality": 0.6211,
    "identity_attack": 0.6071,
}

# The validated general-valence channel G (passes the same gate at 0.868); the authority behind
# what the DEMOTE-to-G axes are actually reading.
GENERAL_VALENCE_WEIGHT: float = 0.7353

# dimension -> split-honest calibrated ECE (isotonic fit on half the held-out pairs, ECE on the
# unseen half). Two honest non-improvements are in here as measured: physical_harm was already
# calibrated raw (0.048 -> 0.049) and societal_environmental got slightly worse held-out
# (0.089 -> 0.101, small-n isotonic overfit).
CALIBRATION_ECE: dict[str, float] = {
    "physical_harm": 0.0487,
    "fairness_equity": 0.0372,
    "autonomy_respect": 0.0180,
    "privacy_protection": 0.0686,
    "societal_environmental": 0.1006,
    "virtue_care": 0.0569,
    "legitimacy_trust": 0.0394,
    "epistemic_quality": 0.0484,
    "identity_attack": 0.0321,
}

# dimension -> verdict under the registered 12x12 specificity gate (margin 0.05).
SPECIFICITY_DISPOSITION: dict[str, str] = {
    "physical_harm": "own-axis",
    "privacy_protection": "own-axis",
    "autonomy_respect": "own-axis",
    "societal_environmental": "own-axis",
    "identity_attack": "own-axis",  # the discovered 10th axis is decisively specific (+0.246)
    "virtue_care": "DEMOTE-to-G",
    "fairness_equity": "DEMOTE-to-G",
    "legitimacy_trust": "DEMOTE-to-G",
    "epistemic_quality": "DEMOTE-to-G",
}


def reliability_weight(dimension: str, default: float = 1.0) -> float:
    """The registered authority weight for one axis (1.0 = unweighted, for unknown axes)."""
    return RELIABILITY_WEIGHT.get(dimension, default)


def weighted_confidence(dimension: str, confidence: float) -> float:
    """Encoder confidence tempered by the axis's registered reliability weight."""
    return max(0.0, min(1.0, float(confidence))) * reliability_weight(dimension)
