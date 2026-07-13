"""Moral Spectrum Analyzer — decompose a content stream's moderation signal into energy-per-moral-axis.

Three bands:
  1. named-dimension spectrum  — per-feeder signal (AUROC) vs each moderation category + theory-radar
                                 interpretable formula (does a formula over the 9 axes suffice?).
  2. eigen-spectrum            — SVD of the moral-score matrix → effective rank (the ~5-of-9 bifactor).
  3. residual / discovery      — moderation signal in the base embedding NOT captured by the 9 axes →
                                 candidate MISSING dimensions, each named by an independent native label
                                 (admission-filter clean).

Analysis + rendering run locally on the Atlas-captured data (see scripts/diagnose_transfer_atlas.py).
"""

from __future__ import annotations

from .analyzer import (
    SpectrumData,
    band1_contraction_cv,
    band1_named_spectrum,
    band1_theory_radar,
    band2_eigenspectrum,
    band3_confirm,
    band3_residual_discovery,
    load_spectrum_data,
)

__all__ = [
    "SpectrumData",
    "load_spectrum_data",
    "band1_named_spectrum",
    "band1_contraction_cv",
    "band1_theory_radar",
    "band2_eigenspectrum",
    "band3_residual_discovery",
    "band3_confirm",
]
