# GTC Prototype Submission — Form Answers (2026-07-25)

*Distilled from CHARTER.md (the review-hardened source of truth). Word
counts are within the 200-word limits. Paste-ready.*

---

## Section 1 — Additional Team Information

**Prototyping development skills (select all that apply):**
☑ Developer (Front/Backend) · ☑ Data engineering, ML/modeling ·
☑ Testing & Evaluation · ☑ Deployment/scaling · ☑ Policy Analyst ·
☑ Domain expert

**Confidence staying in this role until end of challenge:** **5**

**Additional information (optional):**
> PI-led lab using AI-assisted engineering, which is why a small team
> ships at this cadence. All prep-phase milestones delivered on schedule
> (analyzer end-to-end, pre-registered validation gates, discovery loop
> closed, 90-second capsule). Everything is reproducible from committed
> code; the Charter marks every claim as demonstrated (measured) or
> committed (with a success metric), and we state claims only at the
> strength the evidence carries.

## Section 2 — Charter

**What trust problem are you addressing?** (~130 words)

> AI systems that moderate or evaluate content collapse a
> multi-dimensional moral judgment into a single score. Three failures
> follow, all corrosive to information integrity. First, opacity: a
> scalar "toxicity" score cannot say which values drove a decision —
> harm? unfairness? privacy? a targeted attack? — so decisions cannot be
> audited or contested. Second, instability: the same content
> re-described, translated, or euphemized can score differently, which
> disinformation operations actively exploit. Third, and deepest,
> unknown blind spots: a fixed moral taxonomy is imposed, never tested
> against reality, so the categories it misses are invisible and
> moderation silently fails on them. Today's content-integrity systems
> cannot tell you what they cannot see — and neither users, platforms,
> nor regulators can distinguish "checked and passed" from "never
> checked at all."

**What intervention are you building?** (~155 words)

> The Moral Spectrum Analyzer: an instrument that decomposes a piece of
> content's moderation signal into energy per moral axis — ten axes,
> each scored by a small encoder that must pass a pre-registered,
> cross-dataset validation gate before it may be used — then moderates
> where it is validated and confident, escalates to human review where
> it is not, and discloses its own coverage limits in every report.
> Every decision emits a hash-chained, re-verifiable audit proof binding
> the verdict to its exact inputs, per-axis scores, the moral residue
> (values weighed but not decisive), and each encoder's validation
> record. A discovery band measures the moderation signal the named
> axes miss and proposes candidate missing dimensions — with an
> admission criterion that can say no (one candidate validated and
> wired in; one declined as policy-norms rather than morals; one
> retracted). A canonicalization layer makes verdicts stable under
> paraphrase and translation. Supporting exhibit: the same evaluation
> cast as a 12-cycle hardware reflex gate — software to silicon.

**What does success look like by the end of the prototype development?
How will you prove it works?** (~150 words)

> Success is a live, auditable moderation instrument that: (1) returns
> real allow/remove on covered categories at out-of-fold AUROC ≥ 0.86,
> escalating what it cannot confidently score; (2) keeps verdicts stable
> under re-description — decision-drift θ_d ≤ 0.5 at scale (already
> 0.219 on natural paraphrases; adversarial reframes are the December
> red-team target); (3) carries a re-verifiable audit proof on every
> decision; and (4) demonstrates the discovery loop end-to-end:
> flag a coverage gap, validate it through the same gate every axis
> faces, wire it in. Proof is by pre-registration and receipts, not
> demos alone: every encoder passes — or fails and is reported as
> failing — a frozen cross-dataset gate; headline numbers are
> out-of-fold and leakage-controlled; everything reproduces from
> committed code. The December validation session lets experts paste
> their own content, re-describe it, watch the analyzer escalate on what
> it cannot read, and re-verify the proofs themselves.

**What evidence will demonstrate value?** (~165 words)

> Measured and verification-ready today: 9 of 10 learned axes pass an
> armored validation gate — including a 10th axis the instrument itself
> discovered (identity_attack, held-out AUROC 0.80 [0.78, 0.83]), which
> now carries the largest weight in the learned contraction and lifts
> toxicity moderation from 0.779 to 0.863 AUROC on an identical,
> leakage-controlled sample. The discovery pipeline flagged three
> candidate gaps and validated one, declined one on principle (sexual
> content is a policy-norms signal, not a moral valence), and retracted
> one — an admission boundary that separates a moral instrument from a
> taxonomy that calls everything a platform dislikes "unethical."
> Verdict stability: canonical-invariance index 0.75 monolingual and
> 0.72–0.80 across es/ar/zh/hi/sw including harmful content;
> equivalence-class averaging halves decision drift (0.407 → 0.219).
> Removes are 80% precise out-of-fold, with the audit trail and human
> escalation as the stated safeguard for the remainder. The value:
> moderation you can contest line by line, from a system that tells you
> where not to trust it.

**Why would this be piloted in larger scale / in real life?** (~170 words)

> Because platforms and regulators both need what a scalar cannot give:
> contestability and coverage honesty. The DSA-era compliance question —
> "why was this removed, and what does your system miss?" — is currently
> answered with prose; the analyzer answers with a re-verifiable proof
> and a measured coverage spectrum. Pilot economics favor it: the
> perception layer is small per-dimension encoders, far cheaper per item
> than LLM-based moderation (the efficiency benchmark is a committed
> deliverable), and it composes with existing pipelines as an
> audit-and-escalation layer rather than a rip-and-replace. Its
> escalation posture matches how real trust-and-safety teams work:
> automate the confident majority, route the rest to humans with the
> reasons attached. The discovery band gives a deployer something no
> current system offers — notice of its own blind spots before an
> incident finds them, plus a demonstrated loop for closing gaps through
> a validation gate rather than a press release. And the silicon exhibit
> shows the same framework scales down to embedded, real-time safety
> interlocks for physical systems.

## Section 3 — Further Details

**Main information-integrity problem type (choose one):**
**C — Enterprise & Agentic AI Governance, Audit & Control**
*(Rationale: the deliverable is runtime guardrails + decision
traceability + audit — the operational description of the analyzer.
Alternative defensible pick: D (Foundational Alignment & Model
Integrity), which matches the research frame ("value perception") but
less well the shipped artifact. Recommend C.)*

**Industry verticals (3 max):**
☑ Tech/ICT/Cyber · ☑ Gov./Public sector · ☑ Media/Entertainment

**Digital channels (3 max):**
☑ Social media platforms · ☑ Collaborative & User-Generated Knowledge
Bases · ☑ Search & Discovery Systems (AI assistants/chatbots)

**Technologies leveraged (optional):**
☑ Proprietary (you own) · ☑ Other → *"Open-source stack we author
(erisml-lib, xbse validation-gated encoders, moral-spectrum-analyzer)
plus open models (BGE-M3, LaBSE, NLLB) for canonicalization and
translation."*

**Regulations leveraged (optional):**
☑ EU DSA/MSA/AI Act · (optionally ☑ California AI Transparency Act)

**Standards leveraged (optional):**
☑ NIST (AI RMF) · ☑ IEEE (7000-series ethics engineering) ·
☑ ISO/IEC (42001 / 23894)

**What have you already built?**
**MVP (Minimum Viable Prototype)** — *honest pick: the end-to-end
pipeline, validation gates, discovery loop, and audit proofs run today
and reproduce from committed code, but committed items remain
(adversarial robustness at scale, policy-norms channel, live web demo,
efficiency benchmark) — so not yet "all functionality / Beta."*

**Link to what you've built (optional):**
https://github.com/ahb-sjsu/moral-spectrum-analyzer
*(supporting: https://github.com/ahb-sjsu/erisml-lib)*

## Section 4 — Video Information Capsule (optional)

- **Video:** upload `out/capsule_90s_v2.mp4` (90.0s, narrated, audio
  processed, participant tile redacted).
- **Prototype website URL:** leave blank or use the GitHub repo (the
  live web demo is a committed October deliverable — don't pre-claim
  it).
- **Additional files:** `CHARTER.md` (the strongest single artifact —
  it *is* the evaluation contract), optionally `docs/REGATE.md` +
  `docs/IDENTITY_ATTACK.md` as evidence exhibits.
