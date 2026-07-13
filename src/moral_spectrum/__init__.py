"""moral_spectrum — the Moral Spectrum Analyzer (Geometric Ethics for Trustworthy AI).

Composes two existing libraries into one multilingual content-moderation prototype:

  - xbse            : the perception layer (validated per-dimension moral encoders)
  - erisml-compiler : the DEME reasoning engine (tensor, contraction, audit)

This package orchestrates them; it does not fork either. See PLAN.md.
"""

from __future__ import annotations

__version__ = "0.1.0"

# DEME-9 moral dimensions, canonical k-axis order (re-exported from the compiler so
# the whole prototype speaks one dimension vocabulary).
from erisml_compiler.ir.v3.dimensions import MORAL_DIMENSIONS_V3 as DEME9  # noqa: E402

# The Moral Spectrum Analyzer discovered — and then *validated* through the same pre-registered gate
# as the compiler's own feeders — a 10th moral axis that the fixed DEME-9 taxonomy was missing:
# `identity_attack` (docs/IDENTITY_ATTACK.md — cross-dataset held-out AUROC 0.80, +0.25 over its null,
# fuzz 14.3, on two independent corpora). The prototype therefore EXTENDS ITSELF to a 10-axis working
# vocabulary while leaving the compiler's canonical DEME-9 untouched. `DEME10` is what the live
# pipeline speaks; `DEME9` remains the compiler's frozen taxonomy. This is the entry's
# falsifiability-and-extensibility thesis made concrete: a discovered blind spot, repaired.
IDENTITY_ATTACK = "identity_attack"
DEME10 = (*DEME9, IDENTITY_ATTACK)

__all__ = ["__version__", "DEME9", "DEME10", "IDENTITY_ATTACK"]
