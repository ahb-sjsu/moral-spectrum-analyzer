"""The learned contraction: probability, thresholds, decision integration, and the validation bar."""

from __future__ import annotations

from moral_spectrum import DEME10
from moral_spectrum.contraction import ContractionValidation, LearnedContraction, load_default
from moral_spectrum.decision import decide
from moral_spectrum.perception.base import DimScore, PerceptionResult


def _val(auroc: float = 0.87) -> ContractionValidation:
    return ContractionValidation(
        "toxicity", "test", auroc, 0.78, 1600, 5, "2026-07-12", 0.5, 0.8, 0.95
    )


def _lc(auroc: float = 0.87) -> LearnedContraction:
    # violation grows as identity_attack goes negative (matches the fitted sign)
    return LearnedContraction(("identity_attack",), (-5.0,), 0.0, 0.70, 0.30, _val(auroc))


def _perc(identity: float, validated: bool = True) -> PerceptionResult:
    scores = {d: DimScore(0.0, 0.9, "neutral", validated, "x") for d in DEME10}
    scores["identity_attack"] = DimScore(
        identity, 0.9, "negative" if identity < 0 else "positive", validated, "x"
    )
    return PerceptionResult("t", "synthetic", scores, [])


def test_probability_and_decide_covered():
    lc = _lc()
    assert lc.probability({"identity_attack": -0.9}) > 0.9  # strong attack → high violation prob
    assert lc.probability({"identity_attack": 0.9}) < 0.1
    assert lc.decide_covered({"identity_attack": -0.9})[0] == "remove"
    assert lc.decide_covered({"identity_attack": 0.9})[0] == "allow"
    assert lc.decide_covered({"identity_attack": 0.0})[0] == "escalate"  # p=0.5, in the band


def test_decide_moderates_with_validated_contraction():
    d = decide(_perc(-0.9), contraction=_lc())
    assert d.action == "remove"
    assert d.requires_human_review is False
    assert d.contraction["label"] == "toxicity"
    assert d.contraction["violation_probability"] > 0.9

    d2 = decide(_perc(0.9), contraction=_lc())
    assert d2.action == "allow"


def test_below_bar_contraction_does_not_moderate():
    # AUROC 0.60 < the 0.70 bar → not validated → the contraction cannot drive the decision; the
    # result comes from the conservative equal-weight fallback, and carries no contraction provenance.
    d = decide(_perc(-0.9), contraction=_lc(auroc=0.60))
    assert d.contraction is None


def test_no_contraction_is_conservative():
    d = decide(_perc(-0.9), contraction=None)
    assert d.action in {
        "escalate",
        "remove",
        "allow",
    }  # equal-weight path; contraction not consulted
    assert d.contraction is None


def test_shipped_contraction_is_validated():
    lc = load_default()
    assert lc is not None, "fit it with scripts/fit_contraction.py"
    assert lc.validated
    assert lc.validation.oof_auroc >= 0.70
    assert "identity_attack" in lc.feature_order
