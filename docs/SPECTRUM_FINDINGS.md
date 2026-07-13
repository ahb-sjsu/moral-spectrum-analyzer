# Moral Spectrum Analyzer — findings (living document)

**Changelog.** 2026-07-11 first findings (bands 1–3, discovery gaps, `identity_attack` validated +
wired). 2026-07-12 learned contraction shipped/wired; θ_d mechanism decided; contraction number
re-measured **leakage-controlled** (rows disjoint from the `identity_attack` feeder's training set).

Data: 1600 balanced `civil_comments` comments (an honest zero-shot transfer test — NOT a feeder
training corpus), scored by the 8 validated DEME feeders + base BGE-M3 embeddings. Three bands.

## Band 2 — effective rank ≈ 5.19 of 8 (independent confirmation)
SVD of the **8 validated feeders'** score matrix (rights excluded per `require_pass`) gives effective
rank (participation ratio) **5.19 of 8**; explained ratio
`[0.354, 0.145, 0.121, 0.116, 0.090, 0.067, 0.059, 0.048]` — one dominant factor + ~4 more. This
**reproduces `deontic_transfer_gap`'s "~5 axes / bifactor" finding on independent moderation data via
a different method** — a strong convergence. **This is a property of the deployed representation and
its training corpora, NOT of moral space** — `deontic_transfer_gap` §3.7 shows the collapse is
*causally removable* (independent corpora decouple the collapsed axes). Claim the data property, not
the ontological one.

## Band 3 — discovery of coverage gaps outside the nine axes
Per category: AUROC reachable from the 8 feeders vs. from the raw base embedding; the gap = signal the
current axes miss. The higher-dim embedding always carries *some* extra signal, so the
**covered-category gap ~0.08–0.12 is the empirical noise floor** — a real missing dimension must clear
it. *(A first unbalanced pass — 18/51/33 positives on the rare categories — is **superseded** by the
balanced + CI result below, retained only in git history to show what balanced sampling corrected: it
both overstated the gaps and understated feeder coverage, e.g. sexual 0.46→0.75, threat 0.67→0.88.)*

**Confirmed — balanced resample (3001 items, 250–300 positives / rare category) + bootstrap 95% CI:**

| category | 8 feeders | embedding | gap | 95% CI | n_pos |
|---|---:|---:|---:|---|---:|
| **identity_attack** | 0.750 | 0.987 | **+0.237** | [0.20, 0.28] | 289 |
| **sexual_explicit** | 0.752 | 0.955 | **+0.204** | [0.17, 0.25] | 297 |
| toxicity | 0.790 | 0.909 | +0.119 | [0.10, 0.13] | 1413 |
| threat | 0.878 | 0.971 | +0.093 | [0.07, 0.13] | 259 |
| insult | 0.824 | 0.916 | +0.092 | [0.07, 0.11] | 694 |
| obscene | 0.818 | 0.899 | +0.081 | [0.06, 0.11] | 351 |

**Two gaps clear the floor decisively (2–3×): identity_attack (+0.237) and sexual_explicit (+0.204)** —
the eight validated feeders reach only 0.75 while the embedding nearly saturates. What is *confirmed* is **signal
outside the current axes**; whether each is a *moral dimension* is a separate admission question:
- **`identity_attack` — VALIDATED new moral dimension (2026-07-11).** A dignity / discrimination
  concept, built into a real encoder and passed through the **same pre-registered gate** as the 8
  feeders: cross-dataset held-out **AUROC 0.80, +0.25 over its null, fuzz 14.3**, on two independent
  corpora (Jigsaw civil_comments + Berkeley Measuring-Hate-Speech). The discovery→validation loop is
  closed — the taxonomy was genuinely missing this axis. Record: `docs/IDENTITY_ATTACK.md`.
- **`sexual_explicit` — assessed 2026-07-11: DECLINED as a moral dimension; it is a policy-norms
  signal** (`docs/SEXUAL_CONTENT_ADMISSION.md`). Evidence: in civil_comments explicit content is
  87.7% toxic / 1.4% non-toxic (`corr` with toxicity 0.285) — its moral weight is *harassment*
  (already-covered axes), and the corpus holds almost no non-harassing explicit content to carry an
  independent sexual-moral valence. The only moral-valence corpus (Social-Chem, −2273/+405) scores
  sexual *conduct/consent* — autonomy/care/fairness, not "is-explicit." Verdict: consensual
  explicitness isn't a moral violation, so the sign isn't moral; route it as a separate,
  platform-configurable **policy-classifier channel** outside the moral tensor.
- **`threat` — RETRACTED as missing.** At +0.093 it sits *at* the floor and the feeders reach 0.88 —
  largely covered (fairness / harm). The first pass (n_pos=18) overstated it; **the confirmation
  protocol caught its own false positive** — discovery *and* honest retraction.

**Protocol (verification-ready).** Per category: all positives + an equal random sample of *clean*
negatives (all native labels 0); features = the 8 validated feeder scores vs. the base BGE-M3 embedding
reduced to 50 PCA components (unsupervised — no label leakage). Out-of-fold probabilities from 5-fold
`cross_val_predict` with L2 logistic regression (`max_iter=1000`); AUROC on the OOF predictions; 95% CI
from 500 bootstrap resamples of the balanced set; seed 0. Capture `scripts/confirm_dims_atlas.py`;
analysis `scripts/confirm_dims.py` → `moral_spectrum.spectrum.analyzer.band3_confirm`.

## Band 1 — coverage vs. contraction
Per-feeder AUROC is weak individually (many axes near or below 0.5; several anti-correlated). But a
model over the axes reaches **F1 ≈ 0.72 on toxicity** — *out-of-fold 5-fold CV* — so where the axes
have coverage, the near-zero *equal-weight average* was the problem, not the features: a **learned
contraction** recovers usable signal. **Now shipped + wired (2026-07-12):** the 9-feeder learned
contraction (adding the validated `identity_attack` feeder) reaches **OOF AUROC 0.863 / F1 0.76** —
a **+0.084 lift** over the 8-feeder baseline (0.779) — **both measured on the identical 1523-row
disjoint sample** — because `identity_attack` carries the **largest weight** (−2.69). It is frozen to `data/contraction/toxicity_contraction.json` with its OOF validation
record and consumed by `moral_spectrum.decision.decide`, so the pipeline now **moderates** covered categories
(allow/remove where confident) instead of escalating everything. Fit: `scripts/fit_contraction.py`.

**Leakage control (the number is measured on rows the feeder never saw).** The `identity_attack`
feeder trained on civil_comments rows, and it is the contraction's dominant feature — so a spectrum row
inside that training set carries a memorization-inflated `identity_attack` score. We measured the
overlap directly (**77 of 1600 spectrum rows, 4.8%**) and refit on the **1523 disjoint rows**
(matched + excluded by SHA-256 of the normalized text, `data/spectrum/feeder_train_hashes.json`). The
result barely moves: AUROC **0.872 → 0.863**, lift **+0.089 → +0.084**, weight **−2.78 → −2.69** — so
the "the new axis measurably improves the instrument" claim is armored against its best objection,
**not** an artifact of the feeder scoring its own training data. (This is the same train-on-eval guard
the spectrogram uses, applied to the one number in the decision path.)

**Operating point (prevalence caveat).** At the shipped thresholds the contraction **moderates ~51%**
of items at **~80% OOF remove-precision / ~95% allow-precision** — but that precision is on the
**balanced** Band-1 set; deployment prevalence differs, which is exactly why removes carry a
probability and escalation remains the safeguard for everything between the thresholds.

theory-radar (your own tool) then gives the interpretable contraction over the 8 validated feeders (`pcN` = PCA
projections of the feeder scores; `pc0` ≈ the dominant general-valence factor):
- **toxicity ≈ `fairness_equity − pc0`** — low fairness relative to general valence.
- obscene ≈ `(pc1 max pc0) + physical_harm`
- insult ≈ `(virtue_care min pc0) + pc1`
`fairness_equity` / `virtue_care` surfacing explicitly matches Band 1's per-feeder signal. This is the
"metric/contraction" learned as one line of math — interpretable, on-brand, and it confirms the
covered categories are recoverable from the existing axes.

## What this means
The prototype is stronger framed not as "a moderator on a fixed 9-axis taxonomy" but as a **Moral
Spectrum Analyzer**: it measures its own coverage, moderates where validated, escalates where not, and
**discovers coverage gaps beyond the nine** — a novel, honest information-integrity instrument.
Sequence:
1. **(done)** confirmed — two gaps clear the floor; `threat` retracted (balanced re-sample).
2. **(done)** built `identity_attack` (civil_comments + Measuring Hate Speech) through the full gate
   → **PASS, AUROC 0.80**, and wired live as the 10th channel (`docs/IDENTITY_ATTACK.md`).
3. **(done)** assessed `sexual_explicit` → **DECLINED as a moral axis; it is a policy-norms signal**
   (`docs/SEXUAL_CONTENT_ADMISSION.md`).
4. **(done)** learned contraction for covered categories → shipped + wired, leakage-controlled
   (Band 1 above). **(mechanism selected; bar MET at scale)** decision-layer invariance → equivalence-class
   averaging: selected at **θ_d 0.42** on the 8 smoke scenarios (leave-scenario-out), then **met at
   scale on 60 held-out items with LLM-generated classes at θ_d 0.219 ≤ 0.5** (raw 0.407 → 0.219).
   Caveats: 24% generator-refusal hole (→ escalate) and natural-not-adversarial paraphrases
   (`docs/INVARIANCE_FINDINGS.md`).
5. the spectrogram — with `threat` shown as *covered* and `identity_attack` as a lit 10th band — is
   the demo centerpiece. **Fine-print discipline (train-on-eval guard):** the Band-3 confirmation
   sample and the `identity_attack` feeder's civil_comments training rows share a corpus; when the
   10-channel spectrum is re-rendered, its `identity_attack` coverage must be computed on **fresh
   civil_comments rows disjoint from the feeder's training set** (or those rows explicitly excluded),
   and the panel must say so — the gate's own held-out is clean, but the demo visual must not leak.
