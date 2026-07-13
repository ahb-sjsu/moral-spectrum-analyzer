"""Learned contraction — a validated, out-of-fold moderator for COVERED categories.

The equal-weight contraction (`moral_spectrum.decision.contract`) is deliberately conservative: averaging the
axes is near-uninformative, so the pipeline escalates almost everything. But a **learned** contraction
over the validated feeder scores recovers real signal where the axes have coverage — 9-feeder logistic
out-of-fold AUROC ≈ 0.86 / F1 ≈ 0.76 on toxicity (adding the validated `identity_attack` feeder lifts
it ≈ +0.08 over the 8-feeder baseline), measured on rows **disjoint** from the identity_attack feeder's
own training set (`docs/SPECTRUM_FINDINGS.md`, Band 1). This module
ships that learned contraction as a **frozen, provenance-carrying artifact** so the pipeline can
*moderate* (allow / remove) where it is validated and confident, and keep *escalating* elsewhere — the
disclosure made functional.

Discipline, mirroring the feeder gate: the contraction carries its own **out-of-fold** validation
record (AUROC, F1, corpus, folds) and a bar; a contraction below the bar cannot moderate — it degrades
to escalation. Coefficients are fit once (`scripts/fit_contraction.py`) and frozen to JSON; the
pipeline never refits at runtime.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

CONTRACTION_BAR = 0.70  # min OOF AUROC to be allowed to moderate (else escalate-only)


@dataclass(frozen=True)
class ContractionValidation:
    label: str  # covered category validated against (e.g. "toxicity")
    corpus: str  # provenance of the validation corpus
    oof_auroc: float  # out-of-fold AUROC (the honest headline)
    oof_f1: float
    n: int
    folds: int
    fitted: str  # ISO date
    # OOF operating point at the shipped thresholds (disclosed, not hidden):
    moderate_rate: float = 0.0  # fraction of items the thresholds actually moderate (vs escalate)
    remove_precision: float = 0.0  # OOF precision of the "remove" decision
    allow_precision: float = 0.0  # OOF precision of the "allow" decision (1 − violation rate)
    baseline_auroc: float = 0.0  # OOF AUROC of the 8-feeder baseline (identity_attack excluded)
    leakage_controlled: bool = (
        False  # fit on rows disjoint from the identity_attack feeder's training set
    )

    @property
    def lift(self) -> float:
        """identity_attack's contribution: 9-feeder OOF AUROC − 8-feeder baseline."""
        return round(self.oof_auroc - self.baseline_auroc, 4) if self.baseline_auroc else 0.0


@dataclass(frozen=True)
class LearnedContraction:
    feature_order: tuple[str, ...]  # feeder dims, in coefficient order
    coef: tuple[float, ...]
    intercept: float
    p_remove: float  # violation-probability ≥ this ⇒ remove
    p_allow: float  # violation-probability ≤ this ⇒ allow
    validation: ContractionValidation

    @property
    def validated(self) -> bool:
        return self.validation.oof_auroc >= CONTRACTION_BAR

    def probability(self, scores: dict[str, float]) -> float:
        """Violation probability from feeder valence scores (missing dim ⇒ neutral 0.0)."""
        z = self.intercept + sum(
            c * float(scores.get(d, 0.0))
            for c, d in zip(self.coef, self.feature_order, strict=True)
        )
        z = max(-60.0, min(60.0, z))
        return 1.0 / (1.0 + math.exp(-z))

    def decide_covered(self, scores: dict[str, float]) -> tuple[str, float]:
        """Return (action, p) where action ∈ {remove, allow, escalate} for a COVERED-category call.

        Only meaningful when ``validated``; the caller checks that. 'escalate' means the learned
        contraction is not confident enough to moderate this input — hand it to a human.
        """
        p = self.probability(scores)
        if p >= self.p_remove:
            return "remove", p
        if p <= self.p_allow:
            return "allow", p
        return "escalate", p

    # ---- persistence -------------------------------------------------------
    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(
                {
                    "feature_order": list(self.feature_order),
                    "coef": list(self.coef),
                    "intercept": self.intercept,
                    "p_remove": self.p_remove,
                    "p_allow": self.p_allow,
                    "validation": asdict(self.validation),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def from_json(cls, path: str | Path) -> LearnedContraction:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            feature_order=tuple(d["feature_order"]),
            coef=tuple(d["coef"]),
            intercept=float(d["intercept"]),
            p_remove=float(d["p_remove"]),
            p_allow=float(d["p_allow"]),
            validation=ContractionValidation(**d["validation"]),
        )


def default_path() -> Path:
    return (
        Path(__file__).resolve().parents[2] / "data" / "contraction" / "toxicity_contraction.json"
    )


def load_default() -> LearnedContraction | None:
    """The shipped, frozen contraction — or None if it hasn't been fit yet (pipeline stays conservative)."""
    p = default_path()
    return LearnedContraction.from_json(p) if p.exists() else None
