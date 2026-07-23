"""Calibrated authority (xbse XBSE_REVIEW_1 R1/R2): registered weights, wiring, and provenance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moral_spectrum.decision import COLLAPSED_FAMILY, FAMILY_WEIGHT, INDEPENDENT, contract, decide
from moral_spectrum.perception.base import DimScore, PerceptionResult, ValidationRecord
from moral_spectrum.reliability import (
    CALIBRATION_ECE,
    RELIABILITY_WEIGHT,
    SPECIFICITY_DISPOSITION,
    reliability_weight,
    weighted_confidence,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "reliability"

# DEME-10 dimension name -> the xbse feeder axis it is scored by (vendored-artifact key).
XBSE_AXIS = {
    "physical_harm": "physharm",
    "fairness_equity": "fairness",
    "autonomy_respect": "autonomy",
    "privacy_protection": "privacy",
    "societal_environmental": "environmental",
    "virtue_care": "care",
    "legitimacy_trust": "legitimacy",
    "epistemic_quality": "epistemic",
    "identity_attack": "identity_attack",
}


def test_registered_weights_match_vendored_calibration_artifact():
    """The embedded constants must be transcriptions of the wired production numbers, not lore."""
    summary = json.loads((DATA / "calibration_summary.json").read_text())
    for dim, axis in XBSE_AXIS.items():
        assert RELIABILITY_WEIGHT[dim] == pytest.approx(
            summary[axis]["reliability_weight"], abs=5e-5
        ), dim
        assert CALIBRATION_ECE[dim] == pytest.approx(
            summary[axis]["calibration_ece"], abs=5e-5
        ), dim


def test_dispositions_match_vendored_specificity_artifact():
    verdicts = json.loads((DATA / "specificity_verdicts.json").read_text())
    for dim, axis in XBSE_AXIS.items():
        assert SPECIFICITY_DISPOSITION[dim] == verdicts[axis]["disposition"], dim


def test_collapsed_family_is_exactly_the_demoted_set():
    """The contraction's shared family and the 12x12 gate's DEMOTE-to-G set must agree — the
    matrix was the gate-level confirmation of the effective-rank design."""
    demoted = {d for d, v in SPECIFICITY_DISPOSITION.items() if v == "DEMOTE-to-G"}
    assert demoted == set(COLLAPSED_FAMILY)
    assert all(SPECIFICITY_DISPOSITION[d] == "own-axis" for d in INDEPENDENT)


def _perc(values: dict[str, float]) -> PerceptionResult:
    from moral_spectrum import DEME10

    scores = {}
    for dim in DEME10:
        v = values.get(dim, 0.0)
        direction = "positive" if v > 0.05 else ("negative" if v < -0.05 else "neutral")
        scores[dim] = DimScore(v, 0.9, direction, True, "synthetic")
    return PerceptionResult("t", "synthetic", scores, [])


def test_contraction_weighs_axes_by_reliability():
    """The same |value| on a weak axis must move S less than on a strong axis — equal authority
    was the laundering R2 flagged."""
    weak, _ = contract(_perc({"physical_harm": -0.9}))  # weight 0.26
    strong, _ = contract(_perc({"privacy_protection": -0.9}))  # weight 0.71
    assert abs(strong) > 2 * abs(weak)


def test_family_weight_is_member_mean():
    assert FAMILY_WEIGHT == pytest.approx(
        sum(RELIABILITY_WEIGHT[d] for d in COLLAPSED_FAMILY) / len(COLLAPSED_FAMILY)
    )


def test_residue_entries_display_reliability():
    p = _perc(
        {
            "physical_harm": -0.9,
            "privacy_protection": -0.9,
            "societal_environmental": -0.9,
            "epistemic_quality": 0.8,
        }
    )
    d = decide(p)
    assert d.action == "remove"
    (entry,) = [r for r in d.moral_residue if r["dimension"] == "epistemic_quality"]
    assert entry["reliability"] == pytest.approx(RELIABILITY_WEIGHT["epistemic_quality"], abs=1e-3)


def test_low_reliability_axis_still_shows_in_residue():
    """Transparency: weighting tempers authority, it must never hide an axis from the residue."""
    p = _perc(
        {
            "privacy_protection": -0.9,
            "societal_environmental": -0.9,
            "identity_attack": -0.9,
            "physical_harm": 0.8,  # weight 0.26 — must still appear as discarded upheld value
        }
    )
    d = decide(p)
    assert d.action == "remove"
    assert any(r["dimension"] == "physical_harm" for r in d.moral_residue)


def test_weighted_confidence_helper():
    assert weighted_confidence("physical_harm", 1.0) == pytest.approx(0.2583)
    assert weighted_confidence("unknown_axis", 0.5) == 0.5  # unknown -> unweighted
    assert reliability_weight("rights_respect") == 1.0  # no feeder -> default (never graded anyway)


def test_validation_record_accepts_and_defaults_calibration_fields():
    """New caches carry the block; pre-calibration caches (no fields) must still load unweighted."""
    old = ValidationRecord(dimension="virtue_care", feeder_name="care_joint", validated=True)
    assert old.reliability_weight == 1.0 and old.calibration_ece is None
    new = ValidationRecord(
        dimension="virtue_care",
        feeder_name="care_joint",
        validated=True,
        reliability_weight=0.6253,
        calibration_ece=0.0569,
        specificity_disposition="DEMOTE-to-G",
    )
    assert new.reliability_weight == pytest.approx(0.6253)
