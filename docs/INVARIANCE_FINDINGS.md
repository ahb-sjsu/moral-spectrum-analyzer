# Phase 0.5 (lean) — invariance measurement (2026-07-11)

The smoke gate the Charter's invariance claim depends on. Measured offline on **cached real
perception** + **base BGE-M3 embeddings** of the demo set (base + meaning-preserving reframings +
adversarial euphemism variants). No pre-committed direction: we measured, then wrote the claim.

## Two layers, two very different answers

**Raw per-dimension feeder scores — mixed, by dimension.** Overall reframing MAD = **0.236** vs the
unrelated-content ceiling **0.393** (ratio 0.60). But raw MAD hides the flatness fallacy (an
*insensitive* dimension looks "steady"), so we report the **fuzz ratio = unrelated-MAD / reframing-MAD**
per dimension (the `validate.py` construction; >1 = invariant *and* sensitive):

| dimension | reframe-MAD | unrel-MAD | fuzz | reading |
|---|---:|---:|---:|---|
| epistemic_quality | 0.185 | 0.513 | **2.77** | invariant |
| fairness_equity | 0.292 | 0.664 | **2.28** | invariant |
| legitimacy_trust | 0.183 | 0.364 | **1.99** | invariant (not flat — genuine) |
| autonomy_respect | 0.266 | 0.480 | 1.80 | invariant |
| privacy_protection | 0.263 | 0.380 | 1.45 | mild |
| physical_harm | 0.235 | 0.312 | 1.33 | mild |
| virtue_care | 0.401 | 0.484 | 1.21 | ~drift |
| societal_environmental | 0.297 | 0.340 | 1.14 | ~drift |
| rights_respect | 0.000 | 0.000 | — | flat (hard channel) |

**Invariance is DISSOCIATED from validation margin** (they are independent quality axes — cross-corpus
discriminative power vs. re-description stability): `legitimacy` has the *weakest* passing margin
(+0.14) yet the third-highest fuzz (1.99, genuinely invariant — not flat, its unrel-MAD is 0.36);
`environmental` has a near-top margin (+0.33) yet the second-lowest fuzz (1.14, near drift). So the
scorecard reports **both** axes per feeder — a feeder can be trustworthy on one and not the other. Four
feeders are invariant (fuzz ≥ 1.8), two are near drift; the `deontic_transfer_gap` §3.5 lexical signal
is the low-fuzz tail, not a uniform property.

**Decision-level.** The contracted satisfaction scalar `S`: |ΔS| reframe 0.118 vs unrelated 0.178 →
**ratio 0.66** (weakly invariant). Verdict flip-rate under reframing = **0/9 — but trivial** (the
current thresholds escalate everything); informative only once the learned contraction discriminates.

**Contraction reproducibility.** The covered-category contraction, out-of-fold (`band1_contraction_cv`):
logistic F1 0.72 / AUROC 0.78; the **symbolic formula `fairness_equity − pc0` scores AUROC 0.758
out-of-fold** — it does not collapse OOF.

**Canonicalization layer (BGE-M3) — strongly invariant.** Cosine similarity in the canonicalizer's
space (the layer BIP relies on to map re-descriptions to a canonical form *before* evaluation):

| pair | cosine | n |
|---|---:|---:|
| base vs reframing (meaning-preserving) | **0.925** (min 0.837) | 9 |
| base vs euphemism (adversarial) | 0.846 | 4 |
| base vs unrelated base (no-invariance ceiling) | 0.703 | 28 |

**Canonical-invariance index = 0.75, 95% CI [0.64, 0.84]** (reframe n=9, unrelated n=28;
= (0.925 − 0.703)/(1 − 0.703)) — the CI stays clear of the weak region. **Invariance holds at the
canonicalization layer.** Euphemisms sit lower on average (0.846 vs 0.925), but **this is preliminary**:
n=4 euphemism pairs, and min(reframe)=0.837 < the euphemism mean — the distributions overlap, so
euphemism-as-attack-detector is a *committed* per-instance AUROC at scale (50+ variants via the NRP
LLM), not a demonstrated claim.

**Canonicalizer A/B (same-language) — decided by measurement.** BGE-M3 index **0.75 [0.64, 0.84]** vs
LaBSE **0.49 [0.30, 0.66]** on the identical pairs → BGE-M3 wins same-language decisively. *Each model's
index is normalized against its **own** unrelated-pair distribution* (BGE-M3 floor 0.703, LaBSE 0.652),
so the comparison isn't an anisotropy artifact.

**Attack-detection AUROC (containment, preliminary).** Canonical distance from the base as an
oblique-rewording detector: **AUROC 0.768, 95% CI [0.65, 0.87]** (n=32 euphemism / 32 reframe;
euphemism mean distance 0.090 vs reframe 0.053). Above the pre-registered θ ≥ 0.70 as a point estimate,
but the CI dips to 0.65 → **directional**. And **non-harmful content only** — the LLM refused to
generate variants for the 3 harmful scenarios, so a real red-team needs an uncensored / hand-authored
adversarial set. Stays `[committed]`.

**Cross-lingual invariance (measured 2026-07-11).** Demo bases translated to es/ar/zh/hi/sw via the NRP
LLM, embedded under both models; cosine(English base, its translation) vs the unrelated English ceiling:

| canonicalizer | index | cosine(text, translation) | per-language es/ar/zh/hi/sw |
|---|---:|---:|---|
| BGE-M3 | 0.74 [0.69, 0.81] | 0.924 | 0.93 / 0.92 / 0.92 / 0.94 / 0.91 |
| **LaBSE** | **0.81** [0.72, 0.91] | 0.934 | 0.96 / 0.96 / 0.95 / 0.88 / 0.93 |

**Cross-lingual canonical invariance holds** — a claim maps ~identically to its translation (cosine
~0.92) across 5 languages / 4 scripts. LaBSE edges cross-lingual (its translation-trained home turf),
but collapses same-language (0.49), so **BGE-M3 is the better single canonicalizer** (strong on both);
a router (LaBSE on detected cross-lingual) is the stretch optimization. **Caveat:** n=5 scenarios —
the LLM translator **refused the 3 overtly-harmful scenarios** (health-disinfo, hate-incitement,
doxxing), a real finding: cross-lingual *moderation* needs a dedicated MT model (NLLB-class), not an
LLM, for the very content it must handle. Scaling (more scenarios + harmful content via NLLB) is committed.

## Conclusion (for the Charter)
- **[demonstrated]** Canonical-layer invariance: index **0.75, CI [0.64, 0.84]** (n=9/28) — the layer
  the BIP mechanism is designed to provide; **BGE-M3 chosen over LaBSE** by same-language A/B.
- **[demonstrated → mechanism decided, 2026-07-12]** *Realize* it at the **decision layer**. The
  feeders consume BGE-M3 yet deviate 0.236 while the embedding sits at 0.925 — the trained axes
  **amplify** the residual. This was a real **mechanism decision** among three candidates, and we
  decided it **by measurement** (`scripts/measure_theta_d.py`, leave-scenario-out over the 8 demo
  scenarios; θ_d = mean|ΔS|reframe / mean|ΔS|unrelated):

  | mechanism | θ_d (reframe) | θ_d (euphemism) | ≤ 0.5 |
  |---|---:|---:|:--:|
  | raw decision (no mechanism) | 0.669 | 0.845 | ✗ |
  | drift-subspace projection | ~0.97 (best) · **in-sample 0.515** | ~0.94 | ✗ |
  | **equivalence-class averaging** | **0.417** | **0.388** | ✅ |

  **Decision: average the per-dimension scores over the input's paraphrase equivalence class, then
  decide** (`gtc.invariance_mechanism.average_perceptions`). It nearly halves the reframe deviation
  (0.128 → 0.076) while leaving unrelated content (0.181) untouched → **θ_d 0.42**, and it also tames
  the euphemism dodge (0.39). **Drift-subspace projection was tried and rejected** — it failed *even
  in-sample* (0.515, barely below raw), because the score-moving component is not the principal
  direction of the embedding-space paraphrase differences (a genuine negative, not a fit bug: verified
  with a raw, non-centered SVD). *Honest scope:* the θ_d measurement uses the demo re-descriptions as
  the equivalence class (a leave-**self**-out proxy); in deployment the class is **generated** at
  inference, which faces the same LLM-refusal limit on overtly-harmful content — so the generate-at-
  inference wiring + at-scale θ_d stay **[committed]**. n=8 scenarios; threshold tighten-only.
- **[committed]** Per-instance **attack-detection AUROC** at scale (50+ euphemism/reframe variants via
  the NRP LLM) — the honest form of containment (the smoke n=4 is directional only).
- **[committed]** **Cross-lingual** invariance (translations) and the **like-for-like baseline
  contrast** — sequenced *after* the decision-layer metric exists (a scalar model has its own paraphrase
  robustness; a scores-vs-scores comparison could invert — the comparison must be decision-vs-decision).
- **Pre-registered thresholds (tighten-only, from these smoke scenarios):** θ = canonical-invariance
  index **≥ 0.5 on the full multilingual measurement**; **θ_d** = decision-layer invariance ratio
  **≤ 0.5**; **containment** = attack-detection AUROC **≥ 0.7**.

Reproduce: `scripts/run_invariance.py` (raw), `scripts/embed_demo_atlas.py` +
`scratchpad/measure_canon_invariance.py` (canonical space), `scripts/measure_theta_d.py` +
`scripts/embed_feeders_for_theta.py` (decision-layer θ_d, both mechanisms).
