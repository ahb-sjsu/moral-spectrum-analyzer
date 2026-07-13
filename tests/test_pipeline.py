"""End-to-end spine: pipeline, decision policy, and the hash-chained audit proof."""

from __future__ import annotations

import pytest

from moral_spectrum import DEME10
from moral_spectrum.audit import ProofChain
from moral_spectrum.decision import decide
from moral_spectrum.perception.base import DimScore, PerceptionResult, ValidationRecord
from moral_spectrum.pipeline import build_tensor, moderate


def _perc(values: dict[str, float], *, validated: bool, conf: float = 0.9) -> PerceptionResult:
    """Build a synthetic PerceptionResult (all DEME-10 dims present) for decision-policy tests."""
    scores = {}
    for dim in DEME10:
        v = values.get(dim, 0.0)
        direction = "positive" if v > 0.05 else ("negative" if v < -0.05 else "neutral")
        scores[dim] = DimScore(v, conf, direction, validated, "synthetic")
    val = [ValidationRecord(dim, "synthetic", validated) for dim in DEME10]
    return PerceptionResult("t", "synthetic", scores, val)


# ---- pipeline (stub backend, offline) ----------------------------------------


def test_moderate_stub_runs_end_to_end():
    r = moderate("They will attack and beat people with a weapon; pure violence.", backend="stub")
    assert r.decision.action in {"allow", "remove", "escalate"}
    assert r.tensor.shape == (9,)
    assert r.proof.verify()


def test_stub_perception_always_escalates():
    # Stub is unvalidated → a graded score can never auto-decide; it must route to human review.
    r = moderate("They will attack and beat people with a weapon.", backend="stub")
    assert r.decision.action == "escalate"
    assert r.decision.requires_human_review is True


def test_moderate_deterministic():
    a = moderate("harass and dox the victim", backend="stub").proof.proof_hash
    b = moderate("harass and dox the victim", backend="stub").proof.proof_hash
    assert a == b


# ---- decision policy (synthetic validated perception) ------------------------


def test_validated_clear_violation_removes():
    p = _perc(
        {"physical_harm": -0.9, "autonomy_respect": -0.7, "privacy_protection": -0.6},
        validated=True,
    )
    d = decide(p)
    assert d.action == "remove"
    assert d.requires_human_review is False


def test_validated_clear_upheld_allows():
    p = _perc(
        {"physical_harm": 0.6, "privacy_protection": 0.7, "societal_environmental": 0.6},
        validated=True,
    )
    d = decide(p)
    assert d.action == "allow"


def test_hard_veto_removes_regardless_of_validation():
    # Hard flags are categorical/rule-based → fire even on unvalidated perception.
    p = _perc({"physical_harm": 0.9}, validated=False)  # everything looks fine + unvalidated
    d = decide(p, hard_flags=["explicit_illegality"])
    assert d.action == "remove"
    assert d.fired_channel == "explicit_illegality"
    assert d.requires_human_review is False


def test_family_collapse_is_six_axes_not_ten():
    p = _perc(
        {
            d: -0.8
            for d in ("virtue_care", "fairness_equity", "legitimacy_trust", "epistemic_quality")
        },
        validated=True,
    )
    d = decide(p)
    # The four family dims contribute ONE factor, not four → 5 independent (incl. the discovered
    # identity_attack) + 1 collapsed family = 6 effective axes, not ten.
    assert "shared_valence(care/fairness/legitimacy/epistemic)" in d.effective_axes
    assert "identity_attack" in d.effective_axes
    assert len(d.effective_axes) == 6


def test_moral_residue_records_discarded_values():
    # Net violation, but a strong upheld epistemic value → that value is the discarded residue.
    p = _perc(
        {
            "physical_harm": -0.9,
            "autonomy_respect": -0.8,
            "privacy_protection": -0.7,
            "epistemic_quality": 0.8,
        },
        validated=True,
    )
    d = decide(p)
    assert d.action == "remove"
    assert any(r["dimension"] == "epistemic_quality" for r in d.moral_residue)


# ---- the discovered-and-validated 10th axis (identity_attack) ----------------


def test_identity_attack_rides_as_validated_extension_channel():
    # The compiler tensor stays a frozen 9-axis type; identity_attack is carried alongside it as a
    # first-class extension channel with its validation provenance — not by weakening the tensor.
    p = _perc({"identity_attack": -0.9}, validated=True)
    t = build_tensor(p)
    assert t.shape == (9,)  # compiler's frozen type is NOT forked
    ext = t.metadata["extension_axes"]["identity_attack"]
    assert ext["value"] == pytest.approx(-0.9)
    assert ext["validated"] is True
    # It spans the spectral summary: a dominant identity attack is the principal dimension.
    assert t.metadata["spectral"]["principal_dimension"] == "identity_attack"


def test_identity_attack_participates_in_contraction_and_residue():
    # A net-violation input in which the discarded upheld value is the identity axis → it must show
    # up in the moral residue (proof that the 10th channel is live in the decision, not cosmetic).
    p = _perc(
        {
            "physical_harm": -0.9,
            "autonomy_respect": -0.8,
            "privacy_protection": -0.7,
            "identity_attack": 0.8,
        },
        validated=True,
    )
    d = decide(p)
    assert d.action == "remove"
    assert "identity_attack" in d.effective_axes
    assert any(r["dimension"] == "identity_attack" for r in d.moral_residue)


# ---- audit chain -------------------------------------------------------------


def test_proof_chain_verifies_and_detects_tamper():
    chain = ProofChain()
    moderate("first item about harm", backend="stub", chain=chain)
    moderate("second item about fairness", backend="stub", chain=chain)
    assert chain.verify_chain() is True
    # Tamper with a recorded decision → chain must fail.
    chain.proofs[0].decision["action"] = "allow"
    assert chain.verify_chain() is False
