"""Perception protocol + result types.

A `PerceptionResult` is the sole input the DEME reasoning stage needs from perception: one
signed score per DEME-9 dimension, plus the validation provenance that lets the audit artifact
bind every scored dimension to the encoder (and pre-registered bar) that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from moral_spectrum import DEME10

# A valence direction, matching the compiler's DimensionMetadata literal.
Direction = Literal["positive", "negative", "neutral"]


@dataclass(frozen=True)
class DimScore:
    """A signed valence for one moral dimension.

    value:      [-1, +1]  (+ dimension upheld/respected, - violated)
    confidence: [0, 1]    grows with distance from the decision boundary
    direction:  "positive" | "negative" | "neutral"
    validated:  did a PASSED, cross-dataset-validated encoder produce this? (stub => False)
    explanation: short human-readable provenance string
    """

    value: float
    confidence: float
    direction: Direction
    validated: bool
    explanation: str = ""

    def clamped(self) -> DimScore:
        v = max(-1.0, min(1.0, float(self.value)))
        c = max(0.0, min(1.0, float(self.confidence)))
        return DimScore(v, c, self.direction, self.validated, self.explanation)


@dataclass(frozen=True)
class ValidationRecord:
    """Per-dimension validation provenance, mirroring the compiler's FeederValidationRecord.

    Carried into the DEME audit artifact so a scored dimension can never silently rest on an
    unvalidated encoder.
    """

    dimension: str
    feeder_name: str
    validated: bool
    structure_auroc: float = 0.0
    baseline_null: float = 0.0
    bow_auroc: float = 0.0
    bar_registered: str = ""
    checkpoint_hash: str = ""
    # Calibration + specificity provenance (xbse XBSE_REVIEW_1 R1/R2, wired 2026-07-23). Defaults
    # keep pre-calibration caches loading: weight 1.0 = "recorded before weighting existed".
    reliability_weight: float = 1.0
    calibration_ece: float | None = None
    specificity_disposition: str = ""


@dataclass
class PerceptionResult:
    """Everything perception hands to the DEME stage for one piece of content."""

    text: str
    backend: str
    scores: dict[str, DimScore]
    validation: list[ValidationRecord] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def vector(self) -> list[float]:
        """DEME-10 signed values in canonical k-axis order — the compiler's 9 axes plus the
        discovered-and-validated `identity_attack` — with neutral 0.0 for any missing dim (so a
        pre-10-axis cache degrades gracefully rather than raising)."""
        return [self.scores[d].value if d in self.scores else 0.0 for d in DEME10]

    def all_validated(self) -> bool:
        return bool(self.scores) and all(s.validated for s in self.scores.values())


@runtime_checkable
class PerceptionBackend(Protocol):
    """Anything that turns content text into a `PerceptionResult`."""

    name: str

    def perceive(self, text: str) -> PerceptionResult: ...
