"""Perception layer: content text -> DEME-9 signed moral scores (+ validation provenance).

Backends share one protocol (`PerceptionBackend`) and return a `PerceptionResult`:
  - stub   : deterministic, labeled, offline — CI + local dev ONLY (never a judged number).
  - cached : replays REAL Atlas xbse outputs recorded to a jsonl cache — the offline web demo.
  - atlas  : runs the real validated xbse feeders on Atlas GPU 1 (the ground truth).
"""

from __future__ import annotations

from .base import DimScore, PerceptionBackend, PerceptionResult, ValidationRecord
from .stub import StubPerception

__all__ = [
    "DimScore",
    "PerceptionBackend",
    "PerceptionResult",
    "ValidationRecord",
    "StubPerception",
    "get_backend",
]


def get_backend(name: str, **kw) -> PerceptionBackend:
    """Resolve a perception backend by name. `cached`/`atlas` import lazily (heavy deps)."""
    if name == "stub":
        return StubPerception(**kw)
    if name == "cached":
        from .cached import CachedPerception

        return CachedPerception(**kw)
    if name == "atlas":
        # Live GPU perception (the xbse feeders) runs on a GPU host, not in this package.
        # The pip install ships the `stub` and `cached` (replay-real-outputs) backends; the
        # live backend is invoked via the GPU-host scripts, which write the cache this reads.
        raise NotImplementedError(
            "the 'atlas' live-perception backend is not bundled in the pip package; run the "
            "xbse feeders on the GPU host and replay via the 'cached' backend"
        )
    raise ValueError(f"unknown perception backend {name!r} (expected stub/cached/atlas)")
