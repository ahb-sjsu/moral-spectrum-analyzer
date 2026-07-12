# GTC Prototype Charter

**Entry:** *Geometric Ethics for Trustworthy AI* (`jRvRdGdd`) — refined for the prototyping phase as
**the Moral Spectrum Analyzer.**
**Team:** Geometric Ethics AI Lab — Andrew Bond, San José State University.
**Domain:** Information integrity — trustworthy AI content-evaluation and moderation.

> This Charter is the contract we are evaluated against (verification: *does the prototype do what
> the Charter says?*; validation: *does it deliver the claimed value on information integrity?*).
> Every claim below is marked **[demonstrated]** (already measured, verification-ready) or
> **[committed]** (a development-phase deliverable with a defined success metric). We state claims at
> the strength the evidence carries — nothing more.

---

## 1. The problem (information integrity)

AI systems that moderate or evaluate content collapse a multi-dimensional moral judgment into a
single score. Three failures follow, all corrosive to information integrity:

1. **Opacity** — a scalar "toxicity" score cannot say *which* values drove a decision (was this
   removed for harm? unfairness? privacy? a targeted attack?), so it cannot be audited or contested.
2. **Instability** — the same content re-described, translated, or euphemised can score differently,
   which disinformation exploits.
3. **Unknown blind spots** — worst of all, a scalar system **cannot tell you what it cannot see.** A
   fixed moral taxonomy is *imposed*, never *tested* against reality, so the categories it misses are
   invisible — and moderation silently fails on them.

## 2. What we build

**The Moral Spectrum Analyzer** — an instrument that decomposes a piece of content's moderation
signal into **energy per moral axis** (by analogy), measures which axes actually carry which signal, moderates
where it is validated, **escalates and discloses where it is not**, and **discovers the moral
dimensions a taxonomy is missing** — with a verifiable audit trail behind every decision.

Its components (each an existing asset, composed — not rebuilt):
- **Grounded perception** — small per-dimension encoders, each independently *validated* on held-out
  cross-dataset data; an unvalidated encoder cannot be used, and every score carries its validation
  provenance.
- **Structured evaluation** — content → a moral **tensor** (nine axes) → an auditable contraction to
  a decision, logging the *moral residue* (values considered but not acted on).
- **Verifiable audit** — every decision emits a hash-chained proof binding it to the exact inputs and
  the validation record of each encoder that produced it.
- **Supporting exhibit — real-time embedded ethics** — the same evaluation cast as a hardware reflex
  gate (a nanosecond safety interlock for physical agents), showing the framework runs software to
  silicon.

Disciplinary frame: **Philosophy Engineering** — the discipline (defined in its Foundation document,
modeled on the software-engineering body of knowledge) of translating philosophical commitments into
*falsifiable, auditable, computationally-enforceable* constraints. **This prototype is a worked
instance of that discipline:** discovering a missing dimension is not a failure — it is the
falsifiability working, exactly as designed.

## 3. What the prototype does — three bands

1. **Coverage spectrum** — for a labeled content stream, measure each moral axis's signal against
   each moderation category, and derive the interpretable contraction that reconstructs a category
   from the axes. Shows what the system can and cannot read.
2. **Structure spectrum** — the eigen-spectrum of the moral representation → its *effective rank*:
   how many independent axes the *deployed representation* actually uses (a property of the data and
   encoders, shown causally removable — not a claim about moral reality).
3. **Discovery spectrum** — the moderation signal present in content but **not captured by the named
   axes** → candidate missing dimensions, each anchored to an independent label so it can be
   *validated* and added.

Around these: it **moderates** where an axis is validated and confident, **escalates to human review**
where signal is weak or off-distribution (rather than confidently mis-moderating), and **discloses**
its own coverage limits in every report.

## 4. Demonstration plan

- **Verification demo (short):** paste a piece of content → see its moral spectrum (which axes fire,
  with validation badges), the decision + moral residue, and a one-click re-verify of the audit
  proof. Plus the spectrogram over a labeled corpus.
- **Validation (live session):** experts "kick the tires" — try their own content and re-descriptions,
  inspect why a decision was made, watch the analyzer *escalate* on content it can't read, and see the
  discovery band surface a dimension the nine axes miss.

> **Conservative-by-default (state this up front).** The decision layer ships *conservative*: it
> **escalates** any input the learned contraction cannot confidently score. The contraction now
> moderates the **covered** categories (toxicity family) — returning real **allow / remove** where
> confident (OOF AUROC **0.863**, leakage-controlled) and escalating the rest (~49% of the balanced
> fit corpus; *more* on the deliberately-hard adversarial demo set, which is mostly edge cases). So a
> paste-content demo returns a **mix** of allow / remove / escalate, with every *remove* carrying its
> violation-probability and the contraction's out-of-fold validation in the audit proof — and every
> *escalate* honestly saying "not confident, route to a human." The remaining discrimination
> (beyond the covered categories, and the decision-layer invariance that makes it robust to rewording)
> is committed work, but confident allow/remove on covered categories is now a **current** capability.

## 5. Value & impact metrics

**[demonstrated] (measured, verification-ready):**
- **Grounding** — 8 of 9 moral encoders pass a pre-registered, armored cross-dataset validation gate;
  the 9th (`rights`) *fails and is reported as failed* and handled as a hand-specified rule, not a
  learned score (`docs/REGATE.md`). The analyzer then **discovered and validated a 10th** axis
  (`identity_attack`, AUROC 0.80) absent from the taxonomy → **9 of 10 learned axes now pass.**
- **Structure** — the *deployed representation* is lower-rank than its named axes: effective rank ≈
  **5.19 of 8** (a data property, shown *causally removable* in our own pre-registered experiment —
  **not** a claim about moral reality; low rank comes from the training corpora, and independent
  corpora decouple the collapsed axes). Adding the validated `identity_attack` as a 9th feeder raises
  it to **5.68 of 9** — a **pre-registered prediction** (6.08 orthogonal bound) that landed in the
  "partially independent" band: it contributes ≈½ an effective dimension of new signal (max corr 0.34
  to any existing axis), consistent with an identity attack partly overlapping unfairness/cruelty.
- **Coverage + learned contraction (now wired — the pipeline *moderates*)** — a learned contraction
  over the validated feeders scores toxicity at **out-of-fold AUROC 0.863 / F1 0.76** (5-fold), and is
  **shipped as a frozen, OOF-validated artifact the decision layer consumes**: it now returns real
  **allow / remove** on covered categories where confident (e.g. `hate_incitement → remove`, p 0.75),
  and escalates the ~49% it isn't confident about. The discovered `identity_attack` feeder carries the
  **largest weight** (−2.69) and lifts the contraction **+0.084** (0.779 → 0.863 AUROC, **both
  measured on the identical 1523-row disjoint sample**) — the new axis measurably improves moderation. **Leakage-controlled (this is the axis's own strongest objection,
  and it survives):** because the `identity_attack` feeder trained on civil_comments rows and is the
  contraction's dominant feature, we found the overlap with the fit corpus (77 of 1600 rows, 4.8%) and
  **refit on the 1523 disjoint rows** — AUROC moved only 0.872 → 0.863 and the lift only +0.089 →
  +0.084, so the improvement is real signal, not the feeder scoring its own training data
  (`data/spectrum/feeder_train_hashes.json` freezes the exclusion). Honest operating point: at the
  shipped thresholds the *remove* decision is **80% precise** out-of-fold (so ~1 in 5 removes is
  contestable → the audit trail + human-review escalation are the safeguard, not decoration; the demo's
  `harsh_but_factual_criticism → remove` is exactly such a case, shown, not hidden). Validation corpus
  is balanced (base-rate 0.5), so AUROC — not raw precision — is the transferable number.
- **Discovery — and closed the loop.** The analyzer flagged **two coverage gaps beyond the noise
  floor, confirmed with bootstrap CIs** (2–3× the covered-category baseline). The first,
  *identity-attack* (+0.24 [0.20, 0.28]), was **built into a real encoder and passed the exact
  pre-registered gate the other feeders faced**: cross-dataset held-out **AUROC 0.80, 95% CI
  [0.78, 0.83]** (anchor-level bootstrap), **+0.25 over its pre-registered null** (both nulls beaten),
  on two independent corpora (Jigsaw civil_comments +
  Berkeley Measuring-Hate-Speech) — **and is now wired live as the pipeline's 10th channel** (the
  moral vector and every audit proof span 10 axes; the compiler's frozen 9-axis tensor type was *not*
  forked). **The nine-axis taxonomy was genuinely missing a dimension, and the pipeline discovered,
  validated, *and wired in* the fix** (`docs/IDENTITY_ATTACK.md`). The second,
  *sexual-content* (+0.20 [0.17, 0.25]), was **assessed and DECLINED as a moral axis** — it is a
  **policy-norms / appropriateness signal**, not a moral valence (`docs/SEXUAL_CONTENT_ADMISSION.md`):
  consensual explicitness isn't a moral violation, and where a labeled corpus exists the moral weight
  is *harassment* (already-covered axes, 87.7% of explicit civil-comments are toxic), while the only
  moral-valence corpus scores sexual *conduct/consent*, not content. An initial third candidate
  (*threat*) was **retracted** after balanced re-sampling showed the existing axes cover it (0.88).
  So the discovery pipeline flagged three candidates and **validated one, retracted one, and declined
  one on principle** — an admission criterion that can say *no* is what separates a moral instrument
  from a taxonomy that calls everything a platform dislikes "unethical."
- **Invariance (canonicalization layer)** — meaning-preserving re-descriptions map close in the
  BGE-M3 canonical space → **canonical-invariance index 0.75, 95% CI [0.64, 0.84]** (n=9/28; cosine
  0.925 vs 0.703 unrelated; *each model's index normalized against its own unrelated-pair floor*),
  measured 2026-07-11; **BGE-M3 chosen over LaBSE by a same-language A/B** (0.75 vs 0.49). Per-dimension
  fuzz-ratios (**1.1–2.8; four feeders ≥ 1.8, two near drift**) show invariance is **dissociated from
  validation margin** — legitimacy has the *weakest* margin yet high fuzz (1.99), environmental the
  reverse — so the scorecard reports both axes per feeder. *Cross-lingual (preliminary pilot):* a claim
  maps ~identically to its translation across es/ar/zh/hi/sw (index 0.74/0.81), **n=5 benign scenarios
  — the 3 overtly-harmful ones were refused by the LLM translator; harmful + at-scale is committed.**
  *(Euphemism-as-attack-detector is committed — below.)*
- **Auditability** — every decision emits a re-verifiable hash-chained proof carrying each encoder's
  validation record.

**[committed] (development phase, with success metrics):**
- **Invariance realized in the verdict — mechanism *selected* (θ_d 0.42, leave-scenario-out proxy; at-scale committed).**
  The feeders consume BGE-M3 yet their scores deviate 0.24 while the embedding sits at 0.925: the
  trained axes *amplify* the residual drift. This was a **mechanism decision** among three candidates,
  resolved **by measurement** (`scripts/measure_theta_d.py`, leave-scenario-out): **equivalence-class
  averaging** — average per-dimension scores over the input's paraphrase class, then decide — reaches
  **θ_d = 0.42** (reframe) / 0.39 (euphemism); **drift-subspace projection was tried and rejected**
  (failed even in-sample, 0.52). **Two-number honesty:** the pre-registered bar θ_d ≤ 0.5 was
  *calibrated from* these smoke scenarios, so 0.42 measured on the same scenarios' re-descriptions
  (even leave-scenario-out) is **mechanism-selection evidence, not bar-meeting evidence** — the bar is
  met only by the **at-scale run on generated classes**, which is why this item stays [committed]. The
  mechanism is built and unit-tested (`gtc.invariance_mechanism.average_perceptions`). *Remaining
  [committed]:* the **generate-the-class-at-inference** wiring and **at-scale θ_d** — and that
  generator is itself a new trust-boundary + cost surface (spec'd in `docs/INVARIANCE_FINDINGS.md`:
  attack-or-starve the class generator → singleton class → raw score; k× inference cost measured
  *with* averaging on; audit proof records the class). Then **cross-lingual at scale** (dedicated MT — LLM translators *refuse* harmful
  content) and the **like-for-like baseline contrast**, sequenced *after* θ_d (decision-vs-decision,
  not scores-vs-scores). θ: canonical index ≥ 0.5 on the full multilingual measurement, tighten-only.
- **Containment** — per-instance **attack-detection AUROC** (canonical distance as a detector):
  **0.768 [0.65, 0.87]** on 64 generated variants (euphemism mean distance 0.090 vs reframe 0.053) —
  above the pre-registered θ ≥ 0.70 as a point estimate, but the CI dips to 0.65 (**directional**), and
  **non-harmful content only** (the LLM *refused* harmful-scenario variants → a red-team needs an
  uncensored / hand-authored set). Adversarial re-descriptions also move the logged residue, visible in
  the audit trail. Full red-team report in December.
- **Efficiency** — throughput-per-dollar of small encoders vs. LLM-based moderation.
- **Real-time interlock (supporting exhibit)** — the hardware reflex gate's latency confirmed by
  post-implementation timing (a deterministic 12-cycle decision; on-silicon measurement as a stretch).

## 6. Scope & honest limits

- **Not a drop-in universal moderator.** The validated encoders transfer *partially* to social-media
  moderation; the prototype's value is measuring *where* they do, moderating there, and escalating
  elsewhere — not claiming blanket coverage.
- **`rights` does not transfer** (framework-relative) and is handled as a hand-specified rule, not a
  learned score.
- **Cross-lingual — split.** Canonical-layer cross-lingual invariance is *measured* (index 0.74–0.81,
  n=5 benign scenarios; scaling + harmful content via dedicated MT committed). The **feeders' own
  cross-lingual *scoring* is not yet validated** — the valence axes were fit on English pairs; whether
  a Spanish threat *scores* like its English original is untested.
- **The silicon interlock is cycle-simulated** (deterministic 12 cycles, II=1); **post-route timing
  closure and on-card measurement are committed deliverables**, not current claims.
- **The multi-attribute *labels* are not the novelty — the instrument is.** Multi-attribute moderation
  exists (Jigsaw's Perspective API ships `identity_attack`, `sexual_explicit`, `threat`, `insult` — the
  very labels our discovery band used; per-dimension moral scoring exists too: Moral-Foundations
  classifiers, Delphi, ETHICS, LlamaGuard). We do **not** claim to have invented multi-dimensional
  moral scoring or "discovered that identity attacks matter." What is novel is the **composition**:
  validation-gated perception whose provenance travels into a verifiable audit proof (regulation-as-
  code), self-coverage measurement as a first-class output, an **enforceable moral-axis / policy-norm
  admission boundary** (identity_attack admitted, sexual_content declined, threat retracted), and a
  **closed discovery→gate→wire loop**. Position: an **auditable measurement instrument with receipts**,
  not an oracle and not "a new moderator."
- **The discovery band finds *labeled* blind spots, not unknown-unknowns (yet).** The AUROC-gap method
  needs an independent label to compute against, so it detects *when the axes miss signal that
  verifiably exists* — it cannot yet surface a dimension nobody has operationalized. (This is why
  `identity_attack`, a real demonstration of the loop, is a signal Jigsaw's schema already named.)
  The path from "finds labeled gaps" to "finds structure" is **unsupervised residual analysis**
  (clustering the embedding signal the axes *and* the labels both miss) — committed as future work,
  and the single most interesting research direction the prototype points at.
- **The instrument is only as good as its sensors.** The axes read **0.62–0.85**; "measures its own
  coverage" must never become a fig leaf where disclosing weakness substitutes for reducing it. The
  standing rebuttal — and the template — is that the instrument's response to a measured gap was to
  **close it through the gate** (`identity_attack`), not merely to annotate it.

## 7. Milestones

- **Prep (→ mid-July):** this Charter; the 90-second information capsule; the analyzer + spectrogram
  demonstrable end-to-end. *(Done: analyzer, re-gate, discovery, audit; both discovery follow-ons
  closed — `identity_attack` validated at 0.80 and wired live as the 10th channel, `sexual_content`
  assessed and declined as a moral axis.)*
- **Development (→ mid-October):** the decision-layer invariance mechanism (θ_d ≤ 0.5); learned
  contraction so the pipeline moderates (not just escalates) on covered categories; the policy-norms
  channel for the declined `sexual_content` signal; efficiency numbers; the live web demo; the
  governance annex.
- **Testing & validation (→ early December):** verification + the live validation session.

## 8. Already demonstrable today (verification-ready)

A tested end-to-end pipeline (content → moral spectrum → decision + residue → re-verifiable audit
proof), the armored 8/9 validation scorecard, the effective-rank result, the confirmed discovery of
two missing dimensions with confidence intervals — **and one of them, `identity_attack`, already
built and passed through the full pre-registered gate (AUROC 0.80, 9/10 axes now validated)** — all
reproducible from committed code.
