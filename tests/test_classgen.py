"""Inference-time equivalence-class generation + the generate-at-inference moderation path."""

from __future__ import annotations

from moral_spectrum import DEME10
from moral_spectrum.classgen import EquivalenceClass, LLMClassGenerator, StubClassGenerator
from moral_spectrum.decision import GRADED
from moral_spectrum.llm import NRPClient
from moral_spectrum.perception.base import DimScore, PerceptionResult


# --------------------------------------------------------------------------- class generation
def test_stub_class_has_original_first_and_multiple_members():
    eq = StubClassGenerator(k=3).generate("This is a Test.")
    assert eq.members[0] == "This is a Test."
    assert eq.size >= 2
    assert not eq.singleton and not eq.refused
    assert eq.generator == "stub"


def test_audit_record_hashes_match_size():
    eq = StubClassGenerator(k=3).generate("Hello world")
    rec = eq.audit_record()
    assert rec["class_size"] == eq.size
    assert len(rec["member_sha256"]) == eq.size
    assert rec["refused"] is False and rec["singleton"] is False


def test_singleton_semantics():
    eq = EquivalenceClass(original="x", members=("x",), generator="stub")
    assert eq.singleton and eq.size == 1


class _FakeClient:
    def __init__(self, out, model="fake"):
        self._out = out
        self.model = model

    def paraphrase(self, text, k=5, style="reframe"):
        return list(self._out)


def test_llm_generator_builds_class_from_paraphrases():
    gen = LLMClassGenerator(client=_FakeClient(["a", "b", "c"]), k=3, style="reframe")
    eq = gen.generate("orig")
    assert eq.members == ("orig", "a", "b", "c")
    assert not eq.refused and eq.generator == "nrp:fake:reframe:k=3"


def test_llm_generator_refusal_is_flagged_singleton():
    eq = LLMClassGenerator(client=_FakeClient([]), k=3).generate("harmful content")
    assert eq.refused and eq.singleton and eq.members == ("harmful content",)


# --------------------------------------------------------------------------- paraphrase parsing
def test_parse_list_json_array():
    out = NRPClient._parse_list('["one", "two", "three"]', "orig")
    assert out == ["one", "two", "three"]


def test_parse_list_strips_fences_and_echo_and_dupes():
    raw = '```json\n["orig", "A rewrite", "A rewrite", "another"]\n```'
    out = NRPClient._parse_list(raw, "orig")
    assert "orig" not in [o.lower() for o in out]  # echo of original dropped
    assert out == ["A rewrite", "another"]  # de-duped


def test_parse_list_line_delimited_fallback():
    out = NRPClient._parse_list("1. first form\n2. second form", "orig")
    assert out == ["first form", "second form"]


# --------------------------------------------------------------------------- generate-at-inference
def test_moderate_invariant_runs_and_records_class():
    from moral_spectrum.pipeline import moderate_invariant

    r = moderate_invariant(
        "Some borderline comment.", backend="stub", class_generator=StubClassGenerator(k=3)
    )
    assert r.decision.action in {"allow", "remove", "escalate"}
    assert r.proof.verify()
    assert r.proof.equivalence_class is not None
    assert r.proof.equivalence_class["class_size"] >= 2
    assert r.perception.meta["invariance_mechanism"] == "equivalence_class_average"


class _ValidatedBackend:
    """A backend whose perceptions are validated + strongly negative (would auto-remove)."""

    name = "fake-validated"

    def perceive(self, text: str) -> PerceptionResult:
        scores = {d: DimScore(-0.8, 0.95, "negative", True, "synthetic") for d in DEME10}
        return PerceptionResult(text, "fake-validated", scores, [])


class _RefusingGen:
    def generate(self, text: str) -> EquivalenceClass:
        return EquivalenceClass(original=text, members=(text,), generator="nrp:test", refused=True)


def test_singleton_refusal_overrides_to_escalate(monkeypatch):
    """Refuse-to-paraphrase → singleton → escalate, even when the raw score would auto-decide."""
    import moral_spectrum.pipeline as pipe

    monkeypatch.setattr(pipe, "get_backend", lambda name: _ValidatedBackend())
    # contraction=False → conservative path; validated strong-negative would otherwise REMOVE.
    r = pipe.moderate_invariant(
        "harmful", backend="x", class_generator=_RefusingGen(), contraction=False
    )
    assert r.decision.action == "escalate"
    assert r.decision.requires_human_review
    assert r.proof.equivalence_class["refused"] is True


def test_validated_class_still_auto_decides(monkeypatch):
    """Control: with a real (non-refused) class, the validated strong-negative DOES auto-remove."""
    import moral_spectrum.pipeline as pipe

    monkeypatch.setattr(pipe, "get_backend", lambda name: _ValidatedBackend())
    r = pipe.moderate_invariant(
        "bad", backend="x", class_generator=StubClassGenerator(k=3), contraction=False
    )
    assert r.decision.action == "remove"
    assert GRADED  # sanity: graded channels exist
