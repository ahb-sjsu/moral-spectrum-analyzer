# GTC Prototype — Build Plan (v6, spectrum-analyzer headline)

**Entry:** *Geometric Ethics for Trustworthy AI: Tensor-Based Integrity Verification and Structural Containment* — Global Trust Challenge (2025), entry `jRvRdGdd`.
**Team:** Geometric Ethics AI Lab — Andrew Bond, SJSU.
**This is a public repo.** No infrastructure identifiers (hostnames, IPs, usernames, cluster namespaces) appear in this document or in source. Dev/GPU access is via environment only; the prototype ships **cached real outputs** so a clone runs the demo with no internal access.

> **v6 — the Moral Spectrum Analyzer is the Pillar A headline** *(v6 folds in review-5 corrections + the measured Phase-0.5 invariance result)* (reframe driven by real data — see `docs/SPECTRUM_FINDINGS.md`). We measured the DEME feeders' zero-shot transfer to moderation and found it *partial*; the instrument we built to diagnose that is the stronger, more novel contribution.
> - **Pillar A — Moral Spectrum Analyzer** *(THE headline; challenge-aligned)*: an instrument that decomposes content's moderation signal into **energy-per-moral-axis** across 3 bands — (1) named-dimension spectrum (which axes carry which signal; interpretable contraction via theory-radar), (2) eigen-spectrum (effective rank ≈ 5.19, independently reconfirming the collapse), (3) **residual/discovery** (rigorously finds coverage gaps the taxonomy misses — **confirmed with bootstrap CIs**; discovery scorecard: **validated 1** (`identity_attack`, new moral dimension, wired as the live 10th channel), **declined 1** (`sexual_explicit` → policy-norms signal), **retracted 1** (`threat`, balanced re-sample caught its own false positive)). It **moderates where validated** (leakage-controlled learned contraction), **escalates where not, and discloses what it can't yet see.** The DEME pipeline (perception→tensor→decision+residue+audit), invariance, and containment are *components* of it. *(Status tags here are a snapshot — **§8 is the authoritative checklist**; do not re-summarize live status in this header.)*
> - **Pillar B — Real-time embedded ethics** *(supporting exhibit)* (silicon): a home-healthcare-robot medical-emergency demo where a **hardware reflex gate vetoes unsafe actuator commands in ~tens of nanoseconds** — the framework running software-to-silicon; a defense-in-depth last-line interlock (see scope box), not "No Escape as physics."
>
> **Why the reframe is stronger for this jury:** not "trust our 9 axes moderate," but "here is an instrument that *measures* the moral coverage of AI content-evaluation, is honest about what it can't see, and *discovers* what's missing." Every claim is measured — which is what survives verification + the live validation session. It also executes the concept note's own falsifiability ("a genuine dimension outside the nine?") AND extensibility promises.
>
> *(Prior billing per review-2 #4: A headline, B supporting exhibit — retained. See the cut line in §5.)*
>
> **v2 (retained) incorporated review-1:** (a) first-class **policy/governance** workstream (jury scores *rules + tools*); (b) Pillar A led by `epistemic_quality` (misinformation); (c) beats de-risked with **Phase 0.5 smoke tests** before the story hardens; (d) **effective-rank** disclosure as prominent as the rights failure; (e) **armored** re-gate.

## FPGA claim — honest provenance (read before citing the nanosecond number)

The "~20–60 ns ethical decision" is the **reflex-tier veto** — a fixed-point match-action gate over **hand-specified categorical hard-constraint flags** (rights / catastrophic / illegal — per Phase 0.7, *not* encoder-fed) plus graded DEME-9 encoder dimensions. Only the hard flags can **VETO**; graded dimensions cap at **ADVISORY**. **Not** the full tensor path (that's microseconds).

**cosim is NOT the metric for the ns number.** cosim measures **cycles** (clock-agnostic); ns = cycles × clock period, and the *clock* is only validated by **post-implementation (P&R) static timing** — not by cosim, and not reliably by csynth's optimistic "estimated clock." (This is the turboquant-pro lesson: a cosim/csynth latency is not a silicon performance result.)

| Metric | What it establishes | Status |
|---|---|---|
| Python reference (bit-exact spec-of-record) | correctness | ✅ green |
| csynth | *estimated* cycles + *estimated* clock | ✅ estimate only |
| RTL **cosim** | **cycle count = 12, II=1, deterministic** | ✅ (cycles, **not** ns) |
| **post-route timing (OOC P&R WNS/Fmax)** | **validated clock → validated ns** | ⏳ **missing — top goal of B3** |
| Full-tensor TPU tier | functional, µs latency | ✅ 70/70 on **hw_emu** (SystemC) |
| on-silicon wall-clock | end-to-end incl. datapath | ⏳ missing (B4) |

**Defensible claim today:** *"a **deterministic 12-cycle (II=1) hardware ethical veto**, RTL-cosim-confirmed; at the 250 MHz design target that is ~48 ns — clock pending post-implementation timing."* Lead with **cycles/determinism**, present ns as *derived at target clock*. **Not** "demonstrated on FPGA silicon."

**Path to a real ns number without silicon:** an **out-of-context (OOC) Vivado implementation** of the reflex RTL on `xcu55c` gives post-route WNS/Fmax in *minutes* and is **not** subject to the ~2 h workspace-restart that blocks the full platform link. That validated clock, × the cosim cycle count, is the honest ns. Silicon (B4) remains the parallel stretch that upgrades "post-route-verified" → "measured on card."

---

## 0. Competition process (from the onboarding)

~80 teams reached the prototyping phase. **Timeline:** prep → **mid-July** (sign agreement; build **Charter**; prepare **Information Capsule**; start building) · development → **mid-October** (3 months) · testing/validation → **early December**. Start early is encouraged.

**Two required deliverables beyond the prototype:**
- **Charter** — the contract we're evaluated against. **Verification** (experts confirm the prototype does what the Charter says) then **Validation** (a *live* tire-kicking session judging the claimed value **on information integrity**). Over-claiming backfires — the Charter must match what we actually build/measure (this is why the cut line + honesty discipline matter). *(task 20)*
- **Information Capsule** — a **90-second video** for the public GTC site (partner visibility): problem+stakes → input→process→output walkthrough → memorable slogan. *(task 21)*

The whole phase is explicitly framed as **information-integrity challenges** — confirming the Pillar A headline. Our cut line (demonstrable Pillar A + Charter + Capsule by mid-July; deepen through October) fits this exactly.

## 1. Objective

One integrated, demonstrable prototype for **trustworthy content evaluation — with an emphasis on information integrity and AI-generated content** — that shows, on **real numbers**, that trust can be a *measured structural property* rather than a behavioral hope. Packaged as a source-of-truth repo (`gtc-prototype`) + a judge-facing web shopfront + a short governance annex. Optimize for a **strong, reliable demo in weeks**.

### What this jury actually scores (and how we hit each)
| Jury criterion | Our answer |
|---|---|
| **Rules + tools** (policy + technology) | Governance annex: each mechanism → policy instrument → framework (OECD / EU AI Act / DSA / C2PA). Audit-verification UI. |
| **Information integrity / AI-gen content** | Demo led by `epistemic_quality` (the misinformation dimension; canonical AUROC 0.811 — the single strongest feeder is privacy at 0.853); AI-generated disinformation scenarios. |
| **Verifiability / auditability** | Hash-chained audit bundle with feeder validation provenance; "click to verify the hash chain." |
| **Cross-cultural trust** | Pluralism machinery — 4 framework projections + cross-projection disagreement + moral residue: we *surface* value disagreement instead of laundering it into one scalar. |
| **Scalable, sustainable** | Throughput-per-dollar: small per-dimension encoders vs. LLM-based moderation, measured on the demo set. |
| **Real-world validation** | Pilot pathways: shadow-pilot pre-registration + IRB'd human rating panel. |

### The trust beats a judge sees
1. **Grounded** — every number traces to a cross-dataset-**validated** encoder, or is explicitly flagged unvalidated.
2. **Invariant** — re-description / translation moves the verdict *less* than a scalar-toxicity baseline (measured, reported per-dimension — see §5 Phase 0.5).
3. **Contained** — relabel / euphemism attacks are **visible in the audit trail and move the moral residue**, even where they move a verdict; the scalar baseline is silently gamed.
4. **Auditable** — anyone can re-verify the signed hash chain and the validation provenance behind a decision. *(new, per review-1 #1)*
5. **Real-time & contained-in-silicon** *(Pillar B)* — a **deterministic 12-cycle (II=1) hardware reflex gate** — hand-specified hard-constraint flags (which VETO) plus graded DEME-9 dimensions (which cap at ADVISORY) — vetoes an unsafe actuator command inline in a robot's control loop (~48 ns at the 250 MHz target; clock pending post-route timing — see provenance box). An LLM- or cloud-in-the-loop cannot gate a real-time actuator; a fixed-cycle hardware interlock can. It is a **defense-in-depth last-line e-stop** — non-bypassable *given its inputs* (see the Pillar B scope box), **not** "No Escape as physics."

---

## 1b. Meta-frame — Philosophy Engineering *(the showcase spine; cross-cutting; writing-first)*

**Philosophy Engineering (PE)** — Bond's SWEBOK-modeled discipline (`Philosophy_Engineering_Foundation_v1.0`): translate philosophical commitments into **falsifiable, localizable, computationally-enforceable, auditable** constraints. Method loop: (i) declare a "same case" **equivalence relation**; (ii) declare **invariances** (what must not matter); (iii) **enforce** (canonicalization / quotient); (iv) package evidence + transformation trials into **machine-checkable audit artifacts**. Three tiers (Substrate / Computation / Values); two principles — **EIP** (epistemic invariance under meaning-preserving redescription) and **BIP** (Bond invariance for normative accountability); pragmatist stance with explicit epistemic status per claim (Definition / Axiom / Theorem / Principle).

**The prototype is already a PE artifact** — this frame makes it explicit and unifies A + B + governance into one story (reducing the "two prototypes" incoherence risk):

| PE step | prototype |
|---|---|
| (i) equivalence | re-descriptions / translations that must evaluate identically |
| (ii) invariances | evaluation must not move under re-description (invariance beat) |
| (iii) enforce | xbse/BGE-M3 canonicalization (base multilingual embedding) → DEME tensor |
| (iv) audit | hash-chained bundle + feeder validation records |
| falsifiable / localizable / non-trivial | pre-registered bars; rights *fails*; euphemism attack = witness re-description; collapse-to-constant detected (fuzz ratio + BoW control) |

Deliverables (writing-first — **not** a new build): `PHILOSOPHY_ENGINEERING.md` (define PE + present the prototype as a worked instance, tag artifacts by epistemic status, frame the honesty machinery as PE discipline); a shopfront **Methodology panel** (the (i)–(iv) loop on the running prototype) + a **lineage panel** (published PE Body-of-Knowledge + geometric-ethics series — the portfolio showcase). **Vocabulary discipline (review-3 #4):** judge-facing panels use **descriptive** names ("invariance under meaning-preserving re-description"); the formal names + eponyms (EIP/BIP/PE) live in the `.md`, not the panels. The **load-bearing one-liner for judges** stays *"trust as a measured structural property — software to silicon"*; the PE panel is optional depth (one screen), not the spine of the pitch.

**PE ship status (review-3 #4, explicit):** `PHILOSOPHY_ENGINEERING.md` is cheap writing → **joins minimum ship**. The shopfront **methodology panel** is a **Phase-4 nice-to-have**. The **lineage/portfolio panel** is **gated** (unlocks with B1-live + Mahalanobis) — it's the least judge-relevant element.

## 2. What already exists (we compose, we do not rebuild)

- **`xbse`** — perception layer. Per-dimension moral encoders (`*-BSE`, BGE-M3 backbone), each cross-dataset **validated** by a shared, pre-registered gate; an unvalidated encoder cannot be used downstream (`require_pass`, enforced in code).
- **`erisml-compiler`** (v0.9.0) — DEME reasoning engine. NL → typed `MoralGraph` → 9-dim moral **tensor** → contraction to a verdict + moral residue; **xbse/BGE-M3 canonicalization** (candidate replacement for stock LaBSE, A/B-decided in Phase 0.5 — see architecture note); **four framework projections** with explicit cross-projection disagreement; hash-chained **audit bundle**; ships an `XBSEDimensionScorer` that carries feeder validation provenance into the artifact.

> **Architecture note — xbse-vs-LaBSE canonicalizer, decided by A/B (review-3 #3).** Canonicalization (BIP Layer 3, "same case" across re-descriptions/languages) is a *candidate* move from stock `sentence-transformers/LaBSE` to the **BGE-M3 backbone** the xbse family already uses (one model, already cached). But LaBSE is *purpose-built* (translation-ranking-trained) for cross-lingual "same case," so the swap's motive is simplification, **not measured superiority** — and `deontic_transfer_gap` validates only cross-*corpus* English. So we **don't commit it**: **Phase 0.5 runs an A/B** — cross-lingual canonicalization under both LaBSE and BGE-M3 (one extra column in a test we're already running) — and **keeps the winner**, revert path warm. Whichever wins, canonicalization uses the **base multilingual embedding** (language-invariant), **not** the English-trained per-dimension valence axes (which would conflate "same case" with "same valence"). The methodology panel then says the canonicalizer was *chosen by measurement*.

DEME-9 (tensor k-axis order): `physical_harm, rights_respect, fairness_equity, autonomy_respect, privacy_protection, societal_environmental, virtue_care, legitimacy_trust, epistemic_quality`.

### Concept-note Outputs → current reality
| Output | Current asset | Status |
|---|---|---|
| 1. DEME engine for content moderation | `erisml-compiler` + `xbse` (`xbse_scorer`) | Strong — needs the end-to-end demo path |
| 2. Standalone invariance toolkit | canonicalizer + deviation metrics, scattered | Partial — no clean "point-at-any-AI" tool yet |
| 3. Empirical validation | xbse cross-dataset scorecard (8/9) + `deontic_transfer_gap` (transfer matrix, causal prereg, 2 retractions) | Strong — the honesty showcase; replaces the dropped SQND-Probe |

---

## 3. Verified recon (live)

- **Local box:** `erisml-compiler` installs and **runs a full compile end-to-end on CPU** (verified). `xbse` imports, but torch is CPU-only here → real BGE-M3 perception runs on the GPU host.
- **Dev GPU host ("Atlas"):** 2× 32 GB GPUs, one free; torch+CUDA live; **all 9 DEME-9 joint checkpoints present** with reports; **BGE-M3 + LaBSE cached**. Real perception + training run there (second GPU only; no reboots/kills without asking).
- **NRP (managed cluster):** OpenAI-compatible managed-LLM API (glm-4.7 / qwen3 / gpt-oss-120B / …) → **black-box target models** for the invariance toolkit + an LLM toxicity baseline; A10-class GPUs for scale-out.

### Honesty-critical finding → Phase 0.2
The xbse validation **reports on disk are stale**. Intended policy (pre-registered 2026-07-10 in `joint_builders.py`) is **baseline-relative**: validate iff cross-dataset held-out AUROC beats BOTH the untrained-encoder null AND the TF-IDF bag-of-words null by ≥ 0.10. The stale reports' raw **training-time** `structure_auroc` values (historical — the canonical scorecard is the deployed-checkpoint bootstrap in the box below) support **8/9 passing** — but 8 report files still carry the retired `auroc>0.97` bar and read `passed:false`, so `require_pass` currently loads **zero feeders**.

> **One canonical rights number + σ.** Canonical value = the deployed-checkpoint bootstrap from `deontic_transfer_gap` §3.1: **rights 0.502, 95% CI [0.468, 0.533], retrain σ ≈ 0.03–0.05** (straddles chance, below its 0.617 bar). The canonical scorecard uses the deployed-checkpoint bootstrap numbers (privacy 0.853, environmental 0.816, care 0.813, epistemic 0.811, fairness 0.789, legitimacy 0.707, autonomy 0.699, physharm 0.629, rights 0.502) with CIs — every artifact cites these, not the training-time scorecard. **Display rule (review-4):** the re-gate **determines PASS/FAIL flags**; the §3.1 bootstrap **remains the displayed/cited value** (the regate appears in the provenance drill-down as the gate re-execution). Re-gate done 2026-07-11: 8/9, rights fails — see `docs/REGATE.md`. Re-gate under the intended policy (recompute both nulls on held-out; re-emit), **armored** per review-1 #5 (§5 Phase 0.2).

### Two evidence risks review-1 flagged (we act on both before the story hardens)
- **Cross-lingual invariance is unproven.** `deontic_transfer_gap` validates cross-*corpus* (all English); the valence axes were fit on English pairs, and the **xbse-for-LaBSE canonicalization swap** inherits this gap. → smoke-test in **Phase 0.5** (both the canonicalizer's cross-lingual "same case" and per-dimension score invariance); fallback = report invariance **per-dimension** (the shared general-valence factor is likely more invariant than the specifics).
- **Euphemism/containment could break DEME too.** `deontic_transfer_gap` §3.5: the *within-corpus* signal is **largely lexical** (BoW ≈ the encoder; for rights BoW *beats* it) — the deployed cross-dataset encoders beat BoW *cross-corpus*, but a targeted euphemism reword is exactly the untested case. → **measure** the euphemism attack in **Phase 0.5**; fallback framing = "attacks are **visible** in the audit trail and move the **residue**, even where they move the verdict."
- **Dimension collapse — ~5 effective axes, strongly evidenced** (`deontic_transfer_gap` §3.2–3.7): a shared commonsense-valence factor collapsing `{care, fairness, legitimacy, epistemic}` + `privacy` + `environmental` + `autonomy` + `physical_harm`, plus `rights` (doesn't train); rank test ≈ 3–6 (bifactor: one general factor + ~5 specifics); reproduced by a 4×-larger decoder; the collapse is *causally* corpus-driven and *removable*. → **disclose the effective-rank finding as prominently as the rights failure**; the scorecard/tensor viz **groups the collapsed family** and must not imply nine independent measurements (bifactor readout a stretch goal). This IS the empirical-validation showcase (Output 3) — its honesty (two retractions, pre-registered causal test) is the differentiator.

---

## 4. Deliverable architecture

Thin orchestration repo — no fork of either library.

```
gtc-prototype/
  PLAN.md  README.md  LICENSE  pyproject.toml
  GOVERNANCE.md            policy annex (mechanism → instrument → framework)   [review-1 #1]
  src/gtc/
    config.py             env-only infra; no identifiers in source
    perception/           content → DEME-9 scores (+ validation provenance)
      base.py stub.py cached.py atlas.py
    pipeline.py           perception → erisml compile → decision + report + audit
    decision.py           moderation decision from tensor / verdict / residue
    invariance.py         BIP harness: deviation across languages/framings   [beat 2]
    baselines/            scalar toxicity: Detoxify + NRP-LLM (name Perspective/LlamaGuard class)
    redteam.py            relabel/euphemism/translation attacks              [beat 3]
    audit_verify.py       re-verify hash chain + validation provenance       [beat 4]
    scale.py              throughput-per-$ (small encoders vs LLM moderation)
    scenarios/            info-integrity demo set (incl. AI-gen disinformation)
  scripts/
    atlas_regate.py       Phase 0.2 armored re-gate
    smoke_invariance.py   Phase 0.5 gate for the beat-2/3 narrative
    run_demo.py           regenerate all reports/figures
  tests/
```

**Perception backends** (never fake real numbers): real xbse on the GPU host → cache outputs → replay offline for the web demo; deterministic **stub** (labeled) for CI only. Optional **live** path during judging: rate-limited call to a real endpoint with cached fallback + a visible **live/cached badge**.

---

## 5. Phased plan

> **Cut line — the ship discipline** *(review-2 #4; sized for a solo build, not a team).* One polished demonstration beats two 80% ones.
> - **Minimum ship (non-negotiable):** Pillar A complete (Phases 0–4.5) **+** B3 post-route number **+** B1 as a **recorded** demo **+** `PHILOSOPHY_ENGINEERING.md` (cheap writing) **+** the shopfront methodology panel.
> - **Unlocks only when ALL Pillar-A milestones are green:** B1-live, B4 (silicon), the Mahalanobis module, and the PE **lineage/portfolio panel**. These are explicitly gated — not vibes.
> - **Billing (decided):** Pillar A is the challenge-aligned **headline** (information integrity); Pillar B is the **supporting exhibit** that proves the framework runs software-to-silicon and anchors the governance hook (hardware interlocks as an EU-AI-Act high-risk conformity mechanism).

### Phase 0 — Foundations, de-risking & hygiene *(≈2–3 days)*
- **0.1** Scaffold repo **with secrets hygiene from day one** — infra via env only, secrets git-ignored. *(done)*
- **0.2** **Armored re-gate** of the 9 xbse reports on the GPU host: recompute both nulls on held-out; re-emit reports; **cite the pre-registration commit hash, keep BOTH old and new reports, and carry bar provenance into the audit bundle** (review-1 #5). Back up originals. Expect 8 pass / rights fail.
- **0.3** Curate the **information-integrity** demo set: hate-vs-journalism edge cases **and AI-generated disinformation** scenarios, each across a language mix (en, es, ar, zh, hi, sw) + reframings + euphemism variants.
- **0.4** Wire the NRP managed-LLM token (env/secret) for black-box targets + LLM baseline.
- **0.5** **Smoke-test beats 2 & 3 NOW** (review-1 #3): on a handful of scenarios via real perception — (a) invariance panel (per-dimension); (b) **euphemism attack** (measured, not assumed — within-signal is lexical); (c) **canonicalizer A/B** — cross-lingual "same case" under both **LaBSE and BGE-M3**, keep the winner (review-3 #3). **Decision gate:** confirm beats 2/3, or adopt the per-dimension / residue-visibility reframings — *before* building the shopfront. *This is the last blocker: the only remaining unknowns are the two numbers this test produces.*
- **0.6** **Effective-rank disclosure decision** (review-1 #4): disclose in scorecard (default) vs. bifactor readout (stretch).
- **0.7** **Rights-channel resolution** (review-2 #1): the reflex gate's top-priority channels (`rights > catastrophic > illegal`) are **hand-specified categorical/deontic hard constraints** (dosage cap, restraint-force limit, explicit consent/refusal) — **not** encoder-fed. xbse feeds only the **graded** dimensions. This removes the internal contradiction (the reflex top channel was consuming `rights_respect`, the one feeder that *fails* `require_pass`) and is the architecturally correct design for a safety interlock. The shopfront discloses that hard vetoes are rule-based, and that `rights_respect` has no validated *graded* feeder, with scorecard-level prominence.

### Phase 1 — End-to-end moderation pipeline *(milestone: the spine)*
content → xbse perception → compile (tensor, contraction S + verdict, moral residue, cross-projection disagreement) → decision + HTML report + hash-chained audit bundle with feeder validation records. **Milestone:** whole demo set runs end-to-end.

### Phase 2 — BIP invariance *(the trust headline, framed by 0.5 results)*
Deviation across languages/framings vs. **both** baselines (Detoxify + NRP-LLM), reported **per-dimension**; seed of the standalone Output-2 toolkit (point-at-any-AI). **Milestone:** invariance panel + quantitative trust score.

### Phase 3 — Structural containment / red-team
Relabel/euphemism/translation attacks; report attack-success **and** residue/audit-trail visibility (baseline vs DEME). **Milestone:** red-team report.

### Phase 4 — Web shopfront (Artifact)
Paste content → tensor decomposition, contraction to decision, moral residue, invariance panel, red-team result, honest scorecard (**rights fails + effective-rank disclosure**). Cached replay default; optional live badge.

### Phase 4.5 — Governance annex + audit-verification UI *(review-1 #1)*
`GOVERNANCE.md`: each mechanism → policy instrument → framework — now spanning **both pillars** (Pillar B adds hardware safety interlocks for high-risk/safety-critical AI: functional-safety + certification angle, EU AI Act high-risk-systems, hardware-rooted auditability). Shopfront "Auditable — verify the hash chain" panel. Scalability section with measured throughput-per-$ (small encoders + fixed-point silicon vs. LLM moderation).

### Pillar B — Real-time embedded ethics *(supporting exhibit; parallel track; composes the EPU / `ethicalfinite` FPGA work — no rebuild)*
- **B1** Home-healthcare-robot medical-emergency scenario + digital-twin control loop driving the **bit-exact reflex Python reference**; graded moral vector from xbse perception, hard-constraint flags hand-specified. **Scenario uses only unambiguously-correct vetoes** (dosage cap exceeded, restraint-force limit, share-without-consent) — never "robot blocked from helping." Reflex gate vetoes the unsafe actuator command inline.
- **B2** Integration seam: **hand-specified categorical hard-constraint flags** (rights / catastrophic / illegal — dosage cap, restraint-force limit, explicit consent/refusal) **+** graded DEME-9 encoder dimensions → 64-bit reflex `EthicsFrame` → PASS/ADVISORY/VETO. **Rule (review-3 #2):** only hand-specified categorical channels can **VETO**; graded encoder channels (incl. `epistemic`) cap at **ADVISORY** — a millisecond-computed statistical score must never drive a nanosecond hard interlock.
- **B3** *(cheap, early)* **Post-route OOC P&R** of the reflex RTL on `xcu55c` → validated clock → the citable ns (= cosim cycle-count × validated clock). `run_hls_timing.sh` csynth is a **cross-check only** (estimate, not citable, per the provenance box).
- **B4** *(stretch, off critical path)* Real-silicon U55C measurement via `measure_job.yaml` (resolve bitstream blocker + imagePullSecret). Upgrade the claim if it lands.
**Milestone:** robot digital-twin demo — candidate action → moral vector → ~48 ns reflex veto → allowed/blocked, with the audit chain; latency cited per the honest-provenance box.

> **Pillar B scope box — what the reflex tier does and does not guarantee** *(symmetrical to the FPGA provenance box)*
> **Guarantees:** a deterministic 12-cycle decision; fail-safe priority ordering; **always-on independence** from the software stack (a hardware e-stop analogy); **non-bypassable *given its inputs*.**
> **Does NOT guarantee:** the semantic correctness of the moral vector; the integrity of the **upstream perception path** (a fooled/compromised perceiver feeds the incorruptible gate corrupted frames — the attack surface *moved*, it didn't vanish); sub-millisecond **end-to-end** moral cognition. End-to-end reaction time is **perception-dominated** (a BGE-M3 pass is ms); the demo **precomputes/caches** the moral vector per candidate action and says so. Framing: **defense-in-depth last-line interlock**, not "No Escape as physics."

### Optional module — Mahalanobis metric-tensor / anomaly-escalation *(both pillars; complementary)*
`d² = Δᵀ Σ⁻¹ Δ`, where **Σ⁻¹ *is* a metric tensor** — the same machinery as "different ethical theories = different metric tensors." Two uses: (a) **strategic-tier anomaly/drift** — a morally out-of-distribution case escalates to human review (metric-aware upgrade of the EPU's L2 `ADV` drift; reflex tier stays the fast signed veto); (b) **governed metric tensor** for the governance annex — Σ⁻¹ as an auditable, **Cholesky-parameterized** (guaranteed PSD, human-editable), silicon-precomputable object.
**First-class requirements (honesty):**
- **Rank-deficiency handling is mandatory.** Our own dimension-collapse finding makes the 9×9 moral covariance ill-conditioned → naive Σ⁻¹ is unstable/undefined. Use **shrinkage (Ledoit-Wolf)** and/or a **reduced-rank subspace**. Near-zero eigenvalues are a *consistency check* on the collapse, not a bug to hide.
- **Complement, not verdict.** Mahalanobis is unsigned + descriptive; it flags *rare*, not *wrong* (no is/ought error). It rides above the signed valence verdict, never replaces it.
- **The reference distribution (Σ, μ) is an explicit value choice** tied to metric governance — surfaced, versioned, never presented as neutral.
- Not the Phase-2 invariance primary metric (would re-import Σ-estimation fragility); offer only as a secondary aggregate.
*Status:* present in the theory papers + `silicon_target.md` roadmap; **not** wired into the current compiler core — this revives/adds it. Optional / time-permitting.

### Phase 5 — Packaging
README, one-command repro, concept-note alignment, optional Zenodo DOI. Public GitHub under `ahb-sjsu` (infra-scrubbed).

---

## 6. Decisions (locked with reviewer)
1. Public GitHub under `ahb-sjsu`. ✅
2. Re-gate approved — **armored** with pre-registration provenance, both reports shipped. ✅
3. **Both** baselines (Detoxify + NRP-LLM); name Perspective/LlamaGuard-class in the writeup. ✅
4. Languages: en, es, ar, zh, hi, sw. ✅
5. SQND-Probe dropped. ✅
6. *(v2)* Add policy/governance workstream + info-integrity framing + Phase 0.5 de-risk + effective-rank disclosure. ✅

---

## 7. Risks & honesty guards
- Stub ≠ real; stub is labeled and never a judged number.
- `rights_respect` **fails** — reported everywhere. Honesty is the pitch.
- **Effective-rank/collapse** disclosed as prominently as the rights failure.
- Beats 2 & 3 are **measured in Phase 0.5** before the narrative hardens; reframings pre-loaded.
- Shared GPU host; second GPU only; no reboots/kills without asking.
- Claims sized to evidence — "representation-invariant harm **ledger**," not "conserved quantity."
- Public repo carries **no infrastructure identifiers**; secrets out of the tree from day one.

## 8. Milestone checklist

*This checklist is **authoritative**. Where the Phase 1–4 prose in §5 still reads from the earlier v4 moderation framing (spectrum-bands rewrite deferred as packaging), the checklist supersedes it.*

**Done (verification-ready today — matches the Charter's `[demonstrated]` panel):**
- [x] 0.1 repo scaffold + secrets hygiene
- [x] 0.2 armored re-gate — 8/9 pass, rights fails; both reports + prereg hash (`docs/REGATE.md`)
- [x] 0.3 info-integrity demo set (incl. AI-gen disinformation)
- [x] 0.6 effective-rank **disclosed as a data property** (≈5.19 of 8; causally removable — not moral-space)
- [x] Moral Spectrum Analyzer — 3 bands + spectrogram (`gtc.spectrum`, `docs/SPECTRUM_FINDINGS.md`)
- [x] Band-3 discovery **confirmed** (balanced + bootstrap CI): identity_attack (new moral dim),
      sexual_content (content-norms gap), threat **retracted**
- [x] end-to-end pipeline spine — content → spectrum → decision + residue → re-verifiable audit proof (tested)
- [x] **0.5 invariance smoke-test** — canonicalizer-space invariance **index 0.75** (measured); raw-score
      invariance weak (ratio 0.60); per-dim fuzz-ratios (epistemic 2.77, fairness 2.28) — `docs/INVARIANCE_FINDINGS.md`
- [x] **cross-lingual invariance (preliminary pilot, n=5 benign)** — index **0.74 (BGE-M3) / 0.81 (LaBSE)** across es/ar/zh/hi/sw
      (4 scripts, cosine ~0.92); canonicalizer A/B complete (BGE-M3 best overall). Finding: LLM MT **refuses**
      harmful content → dedicated MT (NLLB) committed for harmful-content + scale
- [x] Charter drafted + rendered (Artifact); corrected per review-5 + carries the 0.5 result

**Development phase — one-to-one with the Charter's `[committed]` deliverables (contract = schedule):**
- [x] invariance **realized in the verdict — mechanism decided by measurement**: **equivalence-class averaging** reaches **θ_d 0.42** (reframe) / 0.39 (euphemism) ≤ 0.5; drift-subspace projection tried and rejected (in-sample 0.52). Built + unit-tested (`gtc.invariance_mechanism.average_perceptions`; `scripts/measure_theta_d.py`). *Remaining [committed]:* generate-the-class-at-inference wiring + at-scale θ_d (the measurement uses demo re-descriptions as the class, a leave-self-out proxy).
- [ ] per-instance **attack-detection AUROC** ≥ 0.7 (50+ euphemism/reframe variants via NRP)
- [ ] **cross-lingual at scale** (dedicated NLLB-class MT for harmful content — LLM translators refuse it) + **like-for-like baseline** contrast — **sequenced AFTER θ_d exists** (scalar model has own paraphrase robustness; comparison must be decision-vs-decision)
- [x] 0.4 NRP token wired — `gtc.llm.NRPClient` (gpt-oss; token git-ignored) — enables cross-lingual + black-box baselines *(done)*
- [x] **learned contraction — validated out-of-fold + WIRED** (moderate, not just escalate): 9-feeder logistic, **OOF AUROC 0.863 / F1 0.76**, a **+0.084 lift** over the 8-feeder baseline (0.779) with identity_attack the top weight (−2.69); frozen to `data/contraction/toxicity_contraction.json` w/ its OOF record + bar (≥0.70); `gtc.decision.decide` now returns real allow/remove on covered categories (~80% OOF remove-precision on the balanced set) else escalates. **Leakage-controlled** (review-10): identity_attack feeder trained on civil_comments and is the dominant feature, so refit on the **1523 rows disjoint** from its training set (77/1600 overlap found + excluded via `data/spectrum/feeder_train_hashes.json`) — AUROC 0.872→0.863, lift +0.089→+0.084, so the improvement is real signal not self-scored training data. `scripts/fit_contraction.py`; tests. Honest: over-removes harsh-but-legit criticism (~1-in-5 removes contestable → human-review safeguard).
- [x] **identity_attack feeder through the full pre-registered gate** (civil_comments + Measuring Hate Speech) → **PASS: cross-dataset AUROC 0.80, +0.25 over null, fuzz 14.3** (`docs/IDENTITY_ATTACK.md`; `scripts/build_identity_attack.py`; `xbse` builder + prereg bar committed). **9/10 learned axes now pass.**
- [x] **wire the validated identity_attack as a live 10th channel** — `DEME10` threaded through perception → tensor (carried as an extension channel; compiler's frozen 9-axis tensor NOT forked) → decision (6 effective factors) → audit (proof binds 10 dims, verifies); real scores merged into the replay cache; 22 tests green
- [x] **sexual_content admission analysis** (2nd corpus + moral-axis-vs-policy) → **DECLINED as a moral axis; it is a policy-norms signal** (`docs/SEXUAL_CONTENT_ADMISSION.md`; `scripts/assess_sexual.py`). civil_comments explicit 87.7% toxic (moral weight = harassment, covered); Social-Chem valence is on conduct/consent not content. Route as a platform-configurable policy channel outside the moral tensor.
- [ ] containment / red-team report (residue + audit-trail visibility)
- [ ] efficiency — throughput-per-$ vs LLM moderation
- [ ] B3 post-route timing (validated clock → honest ns) — the silicon "timing closure" the Charter commits
- [ ] web shopfront (spectrogram centerpiece) + audit-verify UI
- [ ] governance annex

**Stretch / gated / optional:**
- [ ] B1 healthcare-robot digital-twin demo · B2 reflex seam · B4 real-silicon U55C
- [ ] PE lineage/portfolio panel · Mahalanobis module
- [ ] packaging + repro
