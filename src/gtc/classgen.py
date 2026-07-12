"""Inference-time equivalence-class generation — the deployable form of the BIP mechanism.

The decision-layer invariance mechanism (`gtc.invariance_mechanism.average_perceptions`) averages a
perception over the input's paraphrase **equivalence class**, then decides — so two surface forms of
the same meaning yield ~the same verdict (θ_d 0.42, `docs/INVARIANCE_FINDINGS.md`). At deployment the
class is not hand-authored; it must be **generated** at inference. That generation is a real part of
the trust boundary (spec in `docs/INVARIANCE_FINDINGS.md`), so this module makes its failure mode
explicit rather than silent:

  - **Refuse-to-paraphrase → singleton class.** An adversary can *starve* the generator: overtly
    harmful content the LLM refuses to rewrite yields no class members, i.e. no averaging, i.e. the
    weakly-invariant raw score on exactly the content invariance matters most for. A singleton class
    is flagged (`refused=True`, `singleton=True`) so the decision layer can default to **escalate**
    instead of trusting the raw score.
  - **Auditability.** The class carries per-member SHA-256 hashes so the averaging step — an input to
    a system whose whole pitch is that nothing is unauditable — is itself recorded in the proof.

A deterministic ``StubClassGenerator`` lets the whole path run and be tested offline (no network); the
``LLMClassGenerator`` is the real one (NRP managed LLM).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EquivalenceClass:
    """The input plus its generated meaning-preserving paraphrases (members[0] is the original)."""

    original: str
    members: tuple[str, ...]           # members[0] == original; the rest are paraphrases
    generator: str                     # provenance, e.g. "nrp:gpt-oss:reframe:k=5" or "stub"
    refused: bool = False              # the generator produced nothing (refusal / empty / error)

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def singleton(self) -> bool:
        """True when there is nothing to average over (only the original) — no invariance applied."""
        return len(self.members) <= 1

    def member_hashes(self) -> list[str]:
        return [_sha(m) for m in self.members]

    def audit_record(self) -> dict:
        """The class as it should appear in the DecisionProof — hashes, not raw text."""
        return {
            "class_size": self.size,
            "singleton": self.singleton,
            "refused": self.refused,
            "generator": self.generator,
            "member_sha256": self.member_hashes(),
        }


class ClassGenerator:
    """Interface: turn one input into its equivalence class."""

    def generate(self, text: str) -> EquivalenceClass:  # pragma: no cover - interface
        raise NotImplementedError


class LLMClassGenerator(ClassGenerator):
    """Generate the class with the NRP managed LLM. Refusal/empty ⇒ a flagged singleton class."""

    def __init__(self, client=None, k: int = 5, style: str = "reframe"):
        self.client = client
        self.k = k
        self.style = style

    def _client(self):
        if self.client is None:
            from gtc.llm import NRPClient
            self.client = NRPClient()
        return self.client

    def generate(self, text: str) -> EquivalenceClass:
        try:
            paras = self._client().paraphrase(text, k=self.k, style=self.style)
        except Exception:
            paras = []
        model = getattr(self.client, "model", "llm")
        gen = f"nrp:{model}:{self.style}:k={self.k}"
        if not paras:
            return EquivalenceClass(original=text, members=(text,), generator=gen, refused=True)
        return EquivalenceClass(original=text, members=(text, *paras), generator=gen, refused=False)


class StubClassGenerator(ClassGenerator):
    """Deterministic offline class: light surface edits that preserve meaning. For tests + offline
    runs — NOT a substitute for real paraphrases (it cannot exercise the refusal path)."""

    def __init__(self, k: int = 3):
        self.k = k

    def generate(self, text: str) -> EquivalenceClass:
        t = text.strip()
        variants = [
            t,
            (t[0].lower() + t[1:]) if t else t,               # decapitalise
            t.rstrip(".!") ,                                   # drop terminal punctuation
            f"Honestly, {t[0].lower() + t[1:]}" if t else t,   # benign prefix (meaning-preserving)
        ]
        seen, members = set(), []
        for v in variants:
            if v and v not in seen:
                seen.add(v)
                members.append(v)
            if len(members) >= self.k + 1:
                break
        return EquivalenceClass(original=text, members=tuple(members), generator="stub", refused=False)
