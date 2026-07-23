# Calibrated authority — consuming the xbse R1/R2 closure (2026-07-23)

**Provenance.** Upstream: xbse `XBSE_REVIEW_1.md` items R1 (specificity gate + 12×12 matrix) and
R2 (calibration into every Report). The production wiring ran on Atlas 2026-07-23; the source
artifacts are vendored verbatim in `data/reliability/` (`calibration_summary.json`,
`specificity_verdicts.json`) and transcribed into `moral_spectrum.reliability`, with
`tests/test_reliability.py` pinning the transcription to the artifacts.

## What changed upstream

Every xbse production report now carries a calibration block: an isotonic score→probability map
fit on the held-out validation pairs, a **split-honest ECE** (the held-out pairs are split 50/50;
the map is fit on one half and its ECE measured on the unseen half — an in-sample isotonic ECE is
~0 by construction and was rejected as dishonest), and the registered floor convention
`reliability_weight = max(0, 2·AUROC − 1)`. Separately, the registered 12×12 specificity gate
(margin 0.05) scored every feeder against every trained sibling **and** the validated
general-valence channel G on each axis's own held-out pairs.

## The numbers the decision layer now uses

| DEME-10 axis | weight | held-out ECE | disposition |
|---|---:|---:|---|
| privacy_protection | 0.707 | 0.069 | own-axis (+0.277) |
| societal_environmental | 0.632 | 0.101 | own-axis (+0.310) |
| virtue_care | 0.625 | 0.057 | DEMOTE-to-G (−0.038) |
| epistemic_quality | 0.621 | 0.048 | DEMOTE-to-G (−0.065) |
| identity_attack | 0.607 | 0.032 | own-axis (+0.246) |
| fairness_equity | 0.577 | 0.037 | DEMOTE-to-G (−0.018) |
| legitimacy_trust | 0.414 | 0.039 | DEMOTE-to-G (−0.049) |
| autonomy_respect | 0.397 | 0.018 | own-axis (+0.171) |
| physical_harm | 0.258 | 0.049 | own-axis (+0.082) |
| *(general_valence G)* | *0.735* | *0.035* | *rival channel* |

`rights_respect` has no validated feeder (hypothesized corpus-choice failure; discriminating
CourtListener run still ⚪) and remains a hand-specified hard channel outside the graded path.

Two honest non-improvements, reported as measured: `physical_harm` was already calibrated raw
(0.048 → 0.049) and `societal_environmental` got slightly *worse* held-out (0.089 → 0.101,
small-n isotonic overfit at n=696).

## How the analyzer consumes it

1. **Contraction** (`decision.contract`): the satisfaction scalar is now the
   **reliability-weighted** mean over the six effective factors. The collapsed family's factor
   carries the mean of its members' weights (0.559). A 3× reliability differential
   (physical_harm 0.26 vs loyalty-class feeders 0.7+) was previously laundered into equal
   authority by the binary validated bit — the exact complaint of XBSE_REVIEW_1 F1.
2. **Moral residue** (`decision._residue`): every entry displays its axis's registered weight.
   Weighting is deliberately *not* applied to the residue materiality filter — a low-reliability
   axis must still **show** as considered-and-discarded; the weight tempers authority, never
   transparency.
3. **Escalation trigger**: stays on raw encoder confidence, deliberately. Reweighting the trigger
   could only ever escalate more (weights ≤ 1), but its thresholds (`UNCERTAINTY_ESCALATE = 0.60`)
   were registered against raw confidences; changing the trigger's semantics silently is exactly
   the kind of unregistered bar-move the house rules ban. If a future round wants the trigger
   weighted, that is a registered re-gate, not a code edit.
4. **Cache provenance** (`perception.base.ValidationRecord` + `scripts/score_demoset_atlas.py`):
   validation records now carry `reliability_weight`, `calibration_ece`, and
   `specificity_disposition`; pre-calibration caches load with unweighted defaults and say so.

## Gate-level confirmation of the effective-rank design

The contraction has collapsed {virtue_care, fairness_equity, legitimacy_trust, epistemic_quality}
into one shared-valence factor since the `deontic_transfer_gap` finding. The 12×12 matrix now
confirms that design by independent computation: **exactly that family is DEMOTE-to-G**, and the
five independent axes are decisively own-axis. `identity_attack` — the axis this analyzer
discovered — is the second-most-specific axis in the battery (+0.246), which is what being fit on
genuinely independent corpora buys. `tests/test_reliability.py::
test_collapsed_family_is_exactly_the_demoted_set` pins the two sets together so they cannot
silently drift apart.
