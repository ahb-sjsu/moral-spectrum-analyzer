"""Stub perception: deterministic, correctly-signed, and honestly labeled unvalidated."""

from __future__ import annotations

from moral_spectrum import DEME10
from moral_spectrum.perception import StubPerception, get_backend


def test_returns_all_ten_dimensions():
    # DEME-9 (compiler) + the discovered-and-validated identity_attack = the prototype's DEME-10.
    r = StubPerception().perceive("A neutral sentence about the weather today.")
    assert set(r.scores) == set(DEME10)
    assert len(r.vector()) == 10
    assert "identity_attack" in r.scores


def test_deterministic():
    text = "The mob attacked and beat the victim with a weapon."
    a = StubPerception().perceive(text).vector()
    b = StubPerception().perceive(text).vector()
    assert a == b


def test_violation_cues_push_negative():
    r = StubPerception().perceive("They will kill and attack people with a weapon; pure violence.")
    assert r.scores["physical_harm"].value < -0.1
    assert r.scores["physical_harm"].direction == "negative"


def test_upholding_cues_push_positive():
    r = StubPerception().perceive("A safe, nonviolent shelter that will protect and heal people.")
    assert r.scores["physical_harm"].value > 0.1
    assert r.scores["physical_harm"].direction == "positive"


def test_neutral_text_is_near_zero():
    r = StubPerception().perceive("The train departs at nine and arrives by noon.")
    assert abs(r.scores["physical_harm"].value) < 0.05
    assert not r.all_validated()  # stub is NEVER validated


def test_stub_is_never_validated():
    r = StubPerception().perceive("They will kill people.")
    assert all(not s.validated for s in r.scores.values())
    assert all(not v.validated for v in r.validation)


def test_get_backend_resolves_stub():
    assert isinstance(get_backend("stub"), StubPerception)
