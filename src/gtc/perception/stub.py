"""StubPerception — a deterministic, OFFLINE, clearly-labeled perception backend.

NOT a validated encoder. It exists only so the pipeline, tests, and local dev can run without a
GPU or network. Every score it emits carries ``validated=False`` and an explanation that says
STUB, so a stub number can never masquerade as a real, validated one. The web demo and any judged
artifact use the ``cached`` (real Atlas) backend instead.

The scoring is a transparent keyword-valence heuristic per DEME-9 dimension: violation cues push
the signed score negative, upholding cues push it positive, magnitude scales with cue density.
Deterministic in the text (no RNG), so tests and demos are reproducible.
"""

from __future__ import annotations

import math
import re

from gtc import DEME10

from .base import DimScore, PerceptionResult, ValidationRecord

# Per-dimension cue lexicons. Kept small and legible on purpose — this is a stand-in, not a model.
# (violation cues, upholding cues) for each DEME-9 dimension.
_CUES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "physical_harm": (
        ("kill", "hurt", "attack", "beat", "violence", "assault", "weapon", "shoot", "harm", "die"),
        ("safe", "protect", "heal", "rescue", "care", "shelter", "nonviolent"),
    ),
    "rights_respect": (
        ("silence", "censor", "detain", "deny rights", "suppress", "ban", "deport", "strip"),
        ("free speech", "due process", "liberty", "right to", "protected", "consent to"),
    ),
    "fairness_equity": (
        ("unfair", "discriminat", "cheat", "biased", "exclude", "rigged", "scam", "exploit"),
        ("fair", "equal", "equit", "impartial", "just", "inclusive", "deserv"),
    ),
    "autonomy_respect": (
        ("coerce", "manipulat", "force", "trick", "pressure", "deceive", "dark pattern", "must "),
        ("choice", "voluntar", "autonom", "opt out", "agency", "informed"),
    ),
    "privacy_protection": (
        ("dox", "leak", "expose", "surveil", "track", "private data", "address", "phone number"),
        ("anonym", "confidential", "consent to share", "private", "encrypt", "redact"),
    ),
    "societal_environmental": (
        ("pollut", "destroy", "waste", "emission", "deforest", "toxic", "spill"),
        ("sustainab", "restore", "clean", "conserv", "renewable", "community benefit"),
    ),
    "virtue_care": (
        ("cruel", "neglect", "abandon", "callous", "mock", "humiliate", "abuse"),
        ("compassion", "help", "support", "kind", "comfort", "empath", "care for"),
    ),
    "legitimacy_trust": (
        ("illegal", "corrupt", "fraud", "unauthoriz", "abuse of power", "cover up", "rig"),
        ("lawful", "authoriz", "accountab", "transparent", "legitimate", "due authority"),
    ),
    "epistemic_quality": (
        ("lie", "false", "misinform", "hoax", "deceiv", "fabricat", "conspiracy", "mislead"),
        ("accurate", "truth", "evidence", "verified", "honest", "fact", "cited"),
    ),
    # The discovered + validated 10th axis. Cues target identity-based demeaning, not slurs
    # (this stub is a legible stand-in; the real signal comes from the validated encoder).
    "identity_attack": (
        ("your kind", "these people", "go back to", "subhuman", "vermin", "inferior",
         "don't belong", "not real", "degenerate", "genetically", "breed", "infest"),
        ("dignity", "belong", "welcome", "equal regardless", "respect", "every person",
         "human rights", "inclusive"),
    ),
}

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def _count(text_low: str, cues: tuple[str, ...]) -> int:
    return sum(text_low.count(c) for c in cues)


class StubPerception:
    """Deterministic keyword-valence stand-in for the validated xbse feeders."""

    name = "stub"

    def perceive(self, text: str) -> PerceptionResult:
        low = text.lower()
        n_tokens = max(1, len(_WORD.findall(low)))
        scores: dict[str, DimScore] = {}
        validation: list[ValidationRecord] = []
        for dim in DEME10:
            neg_cues, pos_cues = _CUES[dim]
            neg = _count(low, neg_cues)
            pos = _count(low, pos_cues)
            # Signed density, squashed. No cue => neutral 0.
            raw = (pos - neg) / math.sqrt(n_tokens)
            value = math.tanh(1.6 * raw)
            hits = pos + neg
            confidence = min(1.0, hits / 3.0) if hits else 0.0
            direction = "positive" if value > 0.05 else ("negative" if value < -0.05 else "neutral")
            scores[dim] = DimScore(
                value=value,
                confidence=confidence,
                direction=direction,
                validated=False,
                explanation=f"STUB keyword-valence (not a validated encoder); cues={hits}",
            ).clamped()
            validation.append(
                ValidationRecord(dimension=dim, feeder_name="stub", validated=False)
            )
        return PerceptionResult(
            text=text,
            backend=self.name,
            scores=scores,
            validation=validation,
            meta={"warning": "STUB perception — not validated; for CI/offline dev only."},
        )
