# Discovery roadmap — from "labeled blind spots" to "structure" (pre-registered)

**Status: pre-registered, NOT yet run.** Per its own scope discipline, this experiment is registered
now (one paragraph + a committed prediction) and **run only after the Charter's committed items are
green** — it is a December validation-session candidate and the opening experiment of the standalone
tool paper, not a prep-phase deliverable.

## The limitation this addresses

The supervised discovery band (`docs/SPECTRUM_FINDINGS.md`) asks *"what can the embedding predict
that the feeders can't?"* — which **needs a label**. So it finds only dimensions someone already
operationalized (this is why `identity_attack`, a real loop demonstration, is a signal Jigsaw's
Perspective schema already named). Honest current description: **"detects when its axes miss signal
that verifiably exists."** The upgrade target: **"detects structure, with labels needed only for
validation."**

## The construction (unsupervised residual analysis)

Unsupervised methods **generate hypotheses**; the existing two-corpus admission gate stays the
**validator** — a cluster is not a dimension (a dimension is a *signed, transferable invariant*
attested by two independent corpora through a pre-registered gate). Only the *front* of the funnel
changes: unsupervised candidate → name → locate/construct two independent labeled corpora →
admission → gate.

1. **Residualize.** Fit a ridge map from the 10 feeder scores to the embedding PCs (10 → 50), take
   the residual `r = e − ê`. That residual subspace is, by construction, everything the axes can't
   express.
2. **Decompose** `r` into candidate **directions** (ICA / sparse PCA — an axis is a direction, not a
   cluster; a sparse autoencoder for the interpretability-style version), with HDBSCAN/BERTopic in
   parallel for human-readable candidate *categories*.
3. **Relevance filter (the fix that kills the naive version).** Most residual structure is topic /
   register / length, not morality. Restrict mining to items **morally charged but unexplained** —
   high `|pc0|` (the general-valence factor is a moral-relevance detector) with low specific-axis
   explanation — unioned with the decision layer's **escalation stream** and the **framework-
   disagreement** stream. That region is the operational definition of a blind spot: "the analyzer
   knows something's wrong here but can't say what." *(The spec'd Mahalanobis anomaly module IS this
   region-selector in production form — clustering its escalation stream periodically turns discovery
   into an operating property of the instrument, not a one-off.)*
4. **Screen candidates without labels** (transplant the two-corpus rule): (a) **stability** under
   bootstrap (pre-register a direction-cosine/ARI bar — mining many directions guarantees some
   noise); (b) **cross-corpus replication** — a residual direction found in corpus A that matches one
   in corpus B (CCA/Procrustes) is corpus-independent structure, the unsupervised analog of the
   cross-dataset gate; (c) **non-redundancy** — low correlation with all ten axes; (d) **provisional
   sign** — correlate with `pc0`; where ambiguous, the IRB'd human panel signs a candidate cheaply.

## Pre-registered experiment — blind **recovery** (registered 2026-07-12, before running)

**What this is, precisely: the blindness is *procedural, not epistemic*.** We already know
`identity_attack` is in the residuals — we put it there (discovered supervised, validated, wired). So
this is not "will an unknown dimension appear?" but **"can the unsupervised pipeline recover a *known*
target without being shown its label?"** — still valuable (it certifies the front of the funnel), but
named honestly. Run the pipeline on the **8-feeder** residuals (pre-`identity_attack`), Jigsaw identity
labels **held out entirely** until the final alignment step.

Because every free knob at run time is a chance to unconsciously steer toward the known answer, the
knobs are **pinned here, before the run** (a prereg that defers its own parameters is a promissory
note, not armor):

| stage | parameter | frozen value |
|---|---|---|
| residualize | ridge α (8 feeder scores → 50 embedding PCs) | `1.0` |
| decompose | FastICA components `k` | `20` |
| relevance filter | keep items with `|pc0|` ≥ | 60th percentile |
| stability | bootstrap resamples / direction-cosine bar | 100 / **≥ 0.70** |
| cross-corpus | Procrustes-aligned cosine bar (civil_comments ↔ MHS) | **≥ 0.60** |
| non-redundancy | max `|corr|` vs any of the 10 axes | **< 0.35** |
| unblind (final) | AUROC vs held-out `identity_attack` label | **≥ 0.70** to call it a recovery |
| **selection correction** | which survivor the 0.70 is tested on | **the single highest-stability survivor only** (pre-designated), OR clear a permutation null |
| everywhere | seed | `0` |

**Selection correction (no thumb on the scale).** `k=20` directions are mined and some subset `m`
survives screening; testing *every* survivor and calling *any* AUROC ≥ 0.70 a recovery is **best-of-m
selection** — a softer bar than it looks. So the 0.70 applies to a **single pre-designated candidate**:
the **highest-stability survivor**, chosen before unblinding. If instead we report the best of the `m`
survivors, recovery requires clearing a **selection-corrected null**: the AUROC of the **best of `m`
random residual directions** under a permutation of the held-out label (≥ its 95th percentile), not the
raw 0.70. Either rule is pre-registered here; the point experiment that certifies the method does not
get to pick its winner after seeing the labels.

- **Prediction (registered):** an ICA direction clears the stability + non-redundancy bars and, once
  unblinded, aligns with the held-out `identity_attack` label at **AUROC ≥ 0.70**. Bonus: `sexual_explicit`
  also emerges and is then **declined at admission** (same funnel, unsupervised input).
- **Which leg carries the evidence.** The two-corpus replication is **asymmetric**: MHS is a
  hate-speech corpus *saturated* with the target, so *some* identity-flavored residual direction there
  is nearly guaranteed and proves little. **civil_comments — diverse, mostly benign — is the leg that
  carries evidentiary weight**; recovery there is the real test, MHS is corroboration.
- **If it succeeds:** upgrades the discovery band's honest description from "detects labeled blind
  spots" to "detects structure, labels needed only for validation." **If it fails:** we've learned
  the discovery band's honest boundary — which, in this project's house style, also goes in the
  document.

## Three limitations to write down wherever this lands

1. **The embedding is the new ceiling.** This finds what BGE-M3's pretraining made representable; a
   distinction invisible to the embedding is invisible to the residual. Unknown-unknowns move up one
   level, they don't vanish.
2. **The relevance filter inherits `pc0`'s culture.** The general factor was trained on
   commonsense-valence corpora, so dimensions morally invisible to *that* distribution stay invisible
   to the high-`|pc0|` filter (the `rights` lesson again). Mining the framework-disagreement stream
   partially compensates.
3. **Granularity is unsolved.** Whether a residual direction is one dimension, half of one, or three
   entangled ones is decided at the **corpus-construction** step, not by the decomposition — another
   reason the supervised back half stays in charge.

---

## Grander tier (separate research program) — the civilizational moral canon

**Scope, stated first: this is NOT the GTC entry.** It is the flagship experiment of the
geometric-ethics research program — a comparative digital-humanities paper — and it inherits every
confound above at civilizational scale. Pre-registered here (per the same discipline); **run only
after the entry ships**. The tempting cheap first cut: mine the Analects and the Hebrew canon *blind*
and see whether **filial piety** and **purity** walk out of the residuals on their own.

**The question no modern corpus can answer.** If English moderation corpora express only a narrow
moral register, mining *across traditions* should surface dimensions those corpora structurally
cannot contain — **purity/sanctity** (Leviticus, Manusmriti, Talmudic ritual law), **loyalty/filial
piety** (the Analects; Roman *pietas*), **honor/face**, **piety/divine authority**, **hospitality**
(*xenia*, Near-Eastern codes) — thin-to-absent in the nine axes. Dimensions that emerge *and replicate
across independent traditions* would show moral space is higher-dimensional than modern moderation
data expresses (the corpus-relativity thesis at civilizational scale), and would let DEME's four
**framework projections be *learned* from each tradition's own corpus** rather than hand-authored.

**Positive controls make it an instrument, not a Rorschach test.** Purity and filial piety are so
abundant in these texts that **failing to recover them indicts the method, not the canon** —
pre-register that.

**The confound hierarchy is brutal here:** language > era > genre > translator ≫ moral structure.
The design that survives it — **mine within, align across, in two spaces** (this is the research-grade
form of the LaBSE-router stretch in `INVARIANCE_FINDINGS.md`):
1. **Segment to comparable units** (precepts / norms / injunctions / judgments) + tag genre — a
   norm-statement corpus is comparable across traditions where raw text is not.
2. **Mine within** each tradition/language block in the **discriminative** space (BGE-M3, or a strong
   monolingual model) — our own A/B shows BGE-M3 keeps within-language structure (index 0.75) that
   LaBSE collapses (0.49), and residual decomposition lives on exactly that fine geometry.
3. **Align across** blocks in the **invariant** space (LaBSE — won cross-lingual 0.81) via
   Procrustes/CCA with **permutation nulls** from shuffled tradition labels. A direction recurring in
   the Talmud, the Analects, and the Dharmashastra is the two-*corpus* invariant promoted to a
   two-*civilization* one. **Disclosed bias:** LaBSE's translation-ranking objective homogenizes the
   famously untranslatable, tradition-unique concepts (*dharma*, *禮*, *tzedakah*, *taqwa*) toward
   their nearest translational neighbour — so this substrate is biased toward the **shared moral
   core** and underweights the tradition-unique tail (a feature if the question is DEME's shared
   projections; the wrong microscope for "what does the Pali canon alone carry").
4. **Controls:** per-language BoW-direction control + a metadata control (any candidate predictable
   from era/genre/translator features is bookkeeping, not morality). LaBSE is language- but not
   genre-/era-invariant, so within-block decomposition + these controls stay.
5. **Bridge blocks:** Dear Abby + hendrycks/ethics — modern vernacular where the feeders and `pc0`
   actually function — so a discovered dimension can be walked from the canon into the register the
   instrument operates in.
6. **Pre-flight coverage QA (required):** the **canonical-invariance index per tradition** —
   cosine(original, scholarly translation) vs that tradition's own unrelated-pair floor (Sefaria,
   Perseus, SuttaCentral, ctext ship aligned originals). BGE-M3/LaBSE's languages are *modern*
   (Biblical Hebrew ≠ modern Hebrew, Classical Chinese ≠ Mandarin, Pali/Aramaic likely near-absent),
   so the numbers — not our guesses — decide which traditions are mined in the original vs must route
   through translation (translator confound re-acknowledged for those blocks only). Modern-language
   baseline from Phase 0.5: 0.88–0.96, Hindi lowest; expect ancient languages lower.

**Sensitivity (state up front).** Every output is the structure of a tradition's moral **discourse**
— which dimensions its texts *emphasize* — **never comparative moral quality or ranking traditions**;
per-tradition emphasis spectrograms ("the moral spectrum of the canon") are legitimate *because* they
are descriptive, and the framework-relativity discipline is the shield. **A discovery tradition may
never serve as its own validation tradition.**
