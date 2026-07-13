"""CachedPerception — replay REAL Atlas xbse outputs offline.

The validated feeders live on a GPU host; the web demo and reproducible runs must not require GPU
access, yet must not fabricate numbers either. So we run the real feeders once on Atlas
(`scripts/score_demoset_atlas.py`), record their exact outputs to a JSONL cache, and replay them
here. A cache miss is a hard error — never a silent fallback to the stub — so a cached run can only
ever show numbers a validated encoder actually produced.
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import DimScore, PerceptionResult, ValidationRecord


class CacheMiss(KeyError):
    """Raised when a text has no recorded real-perception entry — no silent stub fallback."""


class CachedPerception:
    name = "cached"

    def __init__(self, cache_path: str | Path | None = None):
        from moral_spectrum.config import Settings

        self.cache_path = Path(cache_path or Settings().cache_path)
        self._by_sha: dict[str, dict] = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                self._by_sha[rec["text_sha256"]] = rec

    def __len__(self) -> int:
        return len(self._by_sha)

    def perceive(self, text: str) -> PerceptionResult:
        from moral_spectrum.audit import sha256_text

        rec = self._by_sha.get(sha256_text(text))
        if rec is None:
            raise CacheMiss(
                f"no real-perception entry for this text (cache: {self.cache_path}). "
                f"Run scripts/score_demoset_atlas.py on the GPU host to record it. "
                f"The cached backend never falls back to the stub."
            )
        scores = {
            dim: DimScore(
                value=s["value"],
                confidence=s["confidence"],
                direction=s["direction"],
                validated=s["validated"],
                explanation=s.get("explanation", ""),
            )
            for dim, s in rec["scores"].items()
        }
        validation = [ValidationRecord(**v) for v in rec.get("validation", [])]
        return PerceptionResult(
            text=text,
            backend=self.name,
            scores=scores,
            validation=validation,
            meta={
                "recorded_on": rec.get("recorded_on", "atlas"),
                "source": "cached real perception",
            },
        )
