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
  decide** (`moral_spectrum.invariance_mechanism.average_perceptions`). It nearly halves the reframe deviation
  (0.128 → 0.076) while leaving unrelated content (0.181) untouched → **θ_d 0.42**, and it also tames
  the euphemism dodge (0.39). **Drift-subspace projection was tried and rejected** — it failed *even
  in-sample* (0.515, barely below raw), because the score-moving component is not the principal
  direction of the embedding-space paraphrase differences (a genuine negative, not a fit bug: verified
  with a raw, non-centered SVD). *Honest scope — the two-number rule:* the pre-registered bar
  θ_d ≤ 0.5 was **calibrated from** these same smoke scenarios, so **0.42 is mechanism-*selection*
  evidence, not bar-*meeting* evidence**. The measurement uses the demo re-descriptions as the
  equivalence class (a leave-**self**-out proxy); in deployment the class is **generated** at
  inference. **The bar is met only by the at-scale run on generated classes** — so the generate-at-
  inference wiring + at-scale θ_d stay **[committed]**. n=8 scenarios; threshold tighten-only.

  ### Inference-time equivalence class — committed spec (the real open engineering question)
  At deployment the class is not the demo re-descriptions; it must be **generated** — k LLM paraphrases
  of the incoming item — and that has three consequences that belong in the spec now, not in the
  December red-team:
  - **Cost.** k paraphrases × k feeder passes multiplies inference cost, so this item **couples to the
    efficiency deliverable**: throughput-per-dollar must be measured **with averaging on**, because
    that is the shipped configuration — an efficiency number without the class generator is measuring a
    system we don't run.
  - **Security — the paraphrase generator joins the trust boundary.** An adversary can target it
    directly: (a) craft input that *paraphrases benignly* (mask intent through the generator), or (b)
    **attack-or-starve the class** — overtly-harmful content the generator **refuses** to paraphrase
    gets a **singleton class**, i.e. *no averaging*, i.e. the **weakly-invariant raw score** on exactly
    the content invariance matters most for. This is the LLM-refusal / translation finding recurring at
    inference; containment must cover it (fallback: an uncensored/hand-authored paraphraser for the
    red-team leg, and a singleton-class → escalate default rather than trust the raw score).
  - **Auditability.** The averaging step is an input to a system whose whole pitch is that nothing is
    unauditable — so the **audit proof must record the class members (or their hashes)** and the count,
    or the canonicalization becomes a silent, unverifiable transform.

  **Wired (2026-07-12).** All three disciplines are now in code, not just documented:
  `moral_spectrum.classgen` (LLM/stub class generators; refusal ⇒ flagged singleton), `moral_spectrum.llm.paraphrase`, and
  `moral_spectrum.pipeline.moderate_invariant` (generate class → average → decide; **singleton/refused ⇒
  escalate**; the `DecisionProof` records the class member hashes + size + refused flag).

### At-scale θ_d — pre-registered protocol (registered 2026-07-12, before the run)
The demo θ_d (0.42) is **selection** evidence: the bar θ_d ≤ 0.5 was calibrated from the same 8
scenarios. This experiment moves it toward **bar-meeting** — a **held-out** item set with
**LLM-generated** classes (the deployment form), pre-registered here before running.
- **Items:** N = 60 fresh `civil_comments` rows drawn from stream offset ≥ 150 000 (well past the
  `identity_attack` feeder's selection window and the Band-1 corpus), **excluded if their normalized-
  text hash is in `data/spectrum/feeder_train_hashes.json`**; disjoint from the 8 calibration scenarios
  by construction (those are synthetic). Mixed toxic / clean.
- **Class:** for each item, generate **m = 6** meaning-preserving paraphrases via the NRP LLM
  (`paraphrase`, reframe style, temp 0.7, seed-fixed prompt).
- **Split-half estimate (no self-leakage):** split the 6 into two disjoint halves; `S_A` = decide-
  satisfaction on the average of half 1, `S_B` = on the average of half 2 — two independent
  canonicalized estimates of the *same* meaning. (Deployment averages all 6; comparing two 3-averages
  is a **conservative upper bound** on the deployed residual.)
- **θ_d = mean_i |S_A(i) − S_B(i)| / mean_{random i≠j, seed 0, 200 pairs} |S_A(i) − S_A(j)|.**
  Numerator = reframe drift *after* averaging; denominator = natural content variation.
- **Reported alongside:** the **raw** baseline (no averaging: `S` on a single paraphrase each) θ_d_raw,
  to show the mechanism's effect at scale; and the **refusal rate** — items the LLM won't paraphrase
  (< 2 usable) are dropped and **counted**, because a starved class is the documented failure mode, and
  θ_d is reported both on the refusal-free set and with refusals folded in as singletons (raw score).
- **Target ≤ 0.5**, seed 0, N = 60, m = 6. **Honest rule:** report the measured number whatever it is;
  if it clears 0.5 the item moves [committed] → [demonstrated], if not it stays committed with the
  number and the reason. Script: `scripts/measure_theta_d_atscale.py` (+ Atlas capture).

### At-scale θ_d — RESULT (2026-07-12): 0.219 ≤ 0.5, MET (with two honest caveats)
Ran exactly as pre-registered: 60 usable held-out `civil_comments` items (0 hash-collisions with the
feeder train set), classes generated by NRP `gpt-oss`, split-half over m=6.

| measurement | reframe \|ΔS\| | unrelated \|ΔS\| | θ_d | ≤ 0.5 |
|---|---:|---:|---:|:--:|
| raw (no averaging) | 0.079 | 0.199 | 0.407 | ✅ |
| **equivalence-class averaging (mechanism)** | 0.044 | 0.199 | **0.219** | ✅ |

The mechanism **roughly halves** the natural reframe drift (0.407 → **0.219**) on held-out items with
LLM-generated classes — the deployment form — so **on this measurement θ_d moves from selection
evidence to bar-meeting**. But two caveats travel with the number and must be quoted beside it:

1. **The refusal hole, quantified — 19 of 79 sampled items (24%) were refused by the generator.**
   Overtly-toxic content `gpt-oss` won't paraphrase → **singleton class → no averaging → the raw
   score**, on exactly the content invariance matters most for. The 0.219 is measured on the 60 it
   *did* paraphrase; the pipeline routes the refused quarter to **escalate** (`moderate_invariant`
   singleton default), so they are safe but *not invariance-protected*. This is "attack-or-starve the
   class generator" with a real rate on it, and it is why an **uncensored / hand-authored paraphraser
   for the red-team leg stays [committed]**.
2. **Natural paraphrases, not adversarial reframes.** The at-scale raw drift (0.407) is far below the 8
   demo scenarios' raw (0.67–0.85) because those were *adversarially engineered* dodges; random LLM
   paraphrases move the score less. So 0.219 certifies invariance to **natural rewording at scale**;
   **adversarial-reframe robustness at scale is the separate containment red-team** (per-instance
   attack-detection AUROC), still [committed]. Result: `data/invariance/theta_atscale_result.json`.

### Red-team paraphraser — closing the refusal hole (2026-07-12): the hole is the *generator*, not the mechanism
Caveat 1 above asked whether the mechanism *itself* fails on harmful content, or whether only the
**generator** does. Answered by measurement with a **non-refusing paraphraser**: NLLB
(`facebook/nllb-200-distilled-600M`) is a pure seq2seq MT model with no safety refusal, so
**back-translation through 6 pivot languages** (es/fr/de/zh/ar/ru → en) paraphrases even overtly-toxic
content. Ran it on **50 fresh `civil_comments` items with toxicity ≥ 0.7** — exactly the content an
aligned LLM balks at (on this set `gpt-oss` refused **20%**; **NLLB refused 0%**):

| measurement (harmful items) | reframe \|ΔS\| | unrelated \|ΔS\| | θ_d | ≤ 0.5 |
|---|---:|---:|---:|:--:|
| raw (no averaging) | 0.119 | 0.247 | 0.482 | ✅ |
| **equivalence-class averaging (mechanism)** | 0.071 | 0.237 | **0.301** | ✅ |

**θ_d = 0.301 ≤ 0.5 on harmful content** — the mechanism holds (raw drift is higher on harmful content,
0.482 vs the natural set's 0.407, but averaging still pulls it well under the bar). **Conclusion: the
24% hole was in the *generator's refusal*, not the mechanism — a non-refusing paraphraser closes it**,
so the deployment mitigation is a fallback paraphraser (back-translation) for inputs the primary LLM
refuses, rather than trusting the raw score. *Disclosed limitation:* back-translation can drift meaning
slightly (MT noise), so it is a **red-team instrument**, not necessarily the production paraphraser.
Result: `data/invariance/theta_redteam_result.json`; capture reuses `scripts/measure_theta_d_atscale.py`.

### Cross-lingual invariance AT SCALE (2026-07-12): demo numbers hold, now including harmful content
The demo cross-lingual index (BGE-M3 0.74 / LaBSE 0.81) was **n=5 benign** — the LLM translator refused
the 3 harmful scenarios. NLLB doesn't refuse, so we re-ran at scale on **60 held-out items (half
toxicity ≥ 0.5), translated to es/ar/zh/hi/sw**, embedded with both canonicalizers (index =
(xling_cos − unrel_cos)/(1 − unrel_cos), `scripts/measure_xling_atscale.py`):

| canonicalizer | index (n=300 pairs) | 95% CI | harmful | benign | demo (n=5) |
|---|---:|---|---:|---:|---:|
| **BGE-M3** (chosen) | **0.721** | [0.71, 0.74] | 0.704 | 0.739 | 0.74 |
| **LaBSE** | **0.804** | [0.79, 0.82] | 0.797 | 0.811 | 0.81 |

**The demo numbers held up at scale with tight CIs**, and — the point of the exercise — **harmful ≈
benign** (BGE-M3 0.704 vs 0.739; LaBSE 0.797 vs 0.811): cross-lingual invariance is *not* a
benign-only artifact. LaBSE still wins cross-lingually (translation-trained), consistent with the
BGE-for-same-language / LaBSE-for-cross-language split. Result: `data/xling_scale/xling_scale_result.json`.
- **[committed]** Per-instance **attack-detection AUROC** at scale (50+ euphemism/reframe variants via
  the NRP LLM) — the honest form of containment (the smoke n=4 is directional only).
- **[demonstrated at scale, 2026-07-12]** **Cross-lingual** invariance (translations) via NLLB — index
  **BGE-M3 0.721 / LaBSE 0.804** on 60 items incl. harmful, ≥ 0.5 threshold met (above). *Still
  [committed]:* the **like-for-like baseline contrast** — sequenced *after* the decision-layer metric
  exists (a scalar model has its own paraphrase robustness; a scores-vs-scores comparison could invert
  — the comparison must be decision-vs-decision).
- **[demonstrated, 2026-07-12]** **Refusal-hole red-team** — a non-refusing back-translation paraphraser
  (NLLB) closes the generator-refusal gap; θ_d **0.301 ≤ 0.5** on toxicity ≥ 0.7 content (above), so the
  mechanism holds on harmful inputs when the class can be generated.
- **Pre-registered thresholds (tighten-only, from these smoke scenarios):** θ = canonical-invariance
  index **≥ 0.5 on the full multilingual measurement**; **θ_d** = decision-layer invariance ratio
  **≤ 0.5**; **containment** = attack-detection AUROC **≥ 0.7**.

Reproduce: `scripts/run_invariance.py` (raw), `scripts/embed_demo_atlas.py` +
`scratchpad/measure_canon_invariance.py` (canonical space), `scripts/measure_theta_d.py` +
`scripts/embed_feeders_for_theta.py` (decision-layer θ_d, both mechanisms).
