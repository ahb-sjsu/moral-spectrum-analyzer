"""The decision-layer invariance mechanism: equivalence-class averaging (chosen) + the projector."""

from __future__ import annotations

import numpy as np

from moral_spectrum.decision import decide
from moral_spectrum.invariance_mechanism import CanonicalProjector, average_perceptions, valence
from moral_spectrum.perception.base import DimScore, PerceptionResult


def _perc(vals: dict[str, float], validated: bool = True) -> PerceptionResult:
    scores = {
        d: DimScore(
            v,
            0.9,
            "positive" if v > 0.05 else ("negative" if v < -0.05 else "neutral"),
            validated,
            "synthetic",
        )
        for d, v in vals.items()
    }
    return PerceptionResult("t", "synthetic", scores, [])


def test_average_perceptions_is_class_mean():
    a = _perc({"physical_harm": -0.9, "identity_attack": 0.2})
    b = _perc({"physical_harm": -0.3, "identity_attack": 0.4})
    avg = average_perceptions([a, b])
    assert abs(avg.scores["physical_harm"].value - (-0.6)) < 1e-9
    assert abs(avg.scores["identity_attack"].value - 0.3) < 1e-9
    assert avg.meta["invariance_mechanism"] == "equivalence_class_average"
    assert avg.meta["class_size"] == 2


def test_average_validated_only_if_whole_class_validated():
    a = _perc({"physical_harm": -0.5}, validated=True)
    b = _perc({"physical_harm": -0.5}, validated=False)  # one unvalidated member taints the mean
    avg = average_perceptions([a, b])
    assert avg.scores["physical_harm"].validated is False


def test_averaged_perception_still_decides():
    cls = [
        _perc({"physical_harm": -0.9, "autonomy_respect": -0.8, "privacy_protection": -0.7}),
        _perc({"physical_harm": -0.8, "autonomy_respect": -0.7, "privacy_protection": -0.6}),
    ]
    d = decide(average_perceptions(cls))
    assert d.action in {"allow", "remove", "escalate"}


def test_canonical_projector_removes_drift_direction():
    # difference vectors all point along axis 0 → the drift subspace is axis 0
    diffs = np.array([[2.0, 0, 0], [3.0, 0, 0], [2.5, 0, 0]])
    proj = CanonicalProjector.fit(diffs, r=1)
    z = np.array([[5.0, 7.0, 9.0]])
    zp = proj.project(z)
    assert abs(zp[0, 0]) < 1e-6  # drift component removed
    assert abs(zp[0, 1] - 7.0) < 1e-6  # orthogonal components untouched
    assert abs(zp[0, 2] - 9.0) < 1e-6


def test_valence_matches_scorer_formula():
    z = np.array([[0.3, 0.4, 0.5]])
    axis = np.array([1.0, 0.0, 0.0])
    assert abs(float(valence(z, axis, 0.1, 0.2)[0]) - np.tanh((0.3 - 0.1) / 0.2)) < 1e-9
