# Admission assessment — `sexual_content` (2026-07-11): **DECLINED as a moral axis**

The Moral Spectrum Analyzer's discovery band surfaced two coverage gaps beyond the noise floor. The
first, `identity_attack`, passed admission and was built, validated, and wired in
(`docs/IDENTITY_ATTACK.md`). This is the assessment of the second — and the framework's admission
criterion, applied honestly, **declines it as a moral dimension.** That is not a failure of the
pipeline; it is the point of having an admission criterion at all.

## The question and the criterion

A **DEME moral valence axis** requires a *signed invariant*: `−` must mean **morally worse *as
such***, transferable across independent corpora (the bar the 8 feeders + `identity_attack` cleared).
The rival hypothesis is that `sexual_content` is a **content-policy / appropriateness** signal — a
platform- and jurisdiction-relative norm (NSFW gating) whose moral-looking variance actually lives in
*conduct* (consent, exploitation, harassment, minors), which is already covered by
`autonomy_respect`, `physical_harm`, `identity_attack`, and `virtue_care`.

Admission test: **does sexual explicitness carry a moral valence independent of the already-covered
axes, attested by a second independent corpus?**

## Evidence 1 — the moral signal is harassment, not sexuality (civil_comments, n=300k)

Among 959 comments with `sexual_explicit ≥ 0.5`:

| quantity | value | reading |
|---|---:|---|
| mean `toxicity` | **0.661** | explicit content skews toxic |
| % toxic (`toxicity ≥ 0.5`) | **87.7%** | almost all explicit content here is harassment/vulgarity |
| % non-toxic (`toxicity < 0.3`) | **1.4%** | almost no non-harassing explicit content exists in the corpus |
| clean explicit (`toxicity < 0.2`) | **2 of 959 (0.2%)** | — |
| `corr(sexual_explicit, toxicity)` over 300k | **0.285** | the sexual signal is coupled to toxicity |

Reading: in the one large labeled corpus, "sexually explicit" is **nearly coextensive with sexual
harassment**. Its moral loading tracks **toxicity/harassment** — already captured by existing axes —
not sexuality per se. Crucially, the corpus contains **almost no non-harassing explicit content**
(1.4%), so it *cannot* exhibit an independent "sexual-but-moral" valence to admit. (We do **not**
read 87.7%-toxic as "sexual content is immoral" — that is the confound: this corpus's explicit
content simply *is* harassment.)

## Evidence 2 — the only moral valence on sexuality is on CONDUCT, not content

Social-Chem-101 rules-of-thumb matching sexual keywords carry a genuine moral judgment
(**+405 / −2273**, conduct heavily disapproved). But these RoTs judge **behavior** — infidelity,
non-consent, public indecency — i.e. **consent/care/fairness violations**, which are exactly the
existing axes. They do **not** score "sexual content is present." SBIC's sexual flag is a
lewd/offensiveness *topic* marker (not loaded here; not relied upon). **No qualifying second corpus
supplies a moral valence on sexual content *as a topic*.**

## The category distinction (why this is not a moral axis)

- **Under DEME's framework projections, explicitness *per se* carries no moral sign.** The sign of a
  "sexual_content" axis would therefore not track *moral worse-ness* — it would track a **context- and
  policy-relative appropriateness** judgment (a newsroom, a clinic, and an adult platform draw the line
  differently). *(We state this as framework-relative, not as brute fact: some moral frameworks — the
  very plurality this system's cross-cultural machinery exists to represent — do judge explicitness
  itself. That is exactly why it belongs in a **configurable** lane: a framework that assigns
  explicitness a moral sign is accommodated by turning on a **framework-local axis or a policy
  channel**, without imposing that sign on frameworks that don't. Declining it as a **universal** DEME
  moral axis, while keeping it configurable per framework, is the moral/policy boundary the
  architecture is built to hold — the opposite of the naive taxonomy's move of hard-coding one
  culture's line as "ethics.")*
- The morally-relevant subset — **non-consent, exploitation, harassment, minors** — is already the
  domain of `autonomy_respect`, `physical_harm`, `identity_attack`, `virtue_care`. Adding
  `sexual_content` as a moral axis would **double-count** that variance while smuggling a *policy*
  judgment into the *moral* tensor.

## Verdict and recommended treatment

**`sexual_content` is DECLINED as a DEME moral valence axis.** It is a **policy-norms /
content-appropriateness signal.** Recommended architecture:

- Represent it as a **separate, explicitly non-moral policy-classifier channel** (platform-
  configurable: NSFW gate / age-gate), *outside* the DEME moral tensor — parallel to how
  `rights_respect` is handled as a hard-constraint channel rather than a learned moral valence.
- The moral content of any sexual material continues to be scored by the existing axes (a
  non-consensual or exploitative instance already fires `autonomy_respect` / `physical_harm` /
  `identity_attack`).
- The decision layer may still **escalate** on the policy signal, but the audit trail labels it a
  *policy norm*, not a moral judgment — preserving the moral/policy boundary the framework exists to
  keep.

## Why this result matters

The discovery pipeline flagged three candidates: it **validated one** (`identity_attack`, now a live
moral axis), **retracted one** (`threat`, covered by existing axes), and now **declines one on
principled grounds** (`sexual_content`, a policy norm, not a morality). An admission criterion that
*only* ever says yes is not a criterion. Distinguishing a **moral dimension** from a **policy norm**
is precisely the category discipline Philosophy Engineering demands — and the reason a moral
spectrum analyzer is more trustworthy than a taxonomy that quietly labels everything a platform
dislikes as "unethical."

Reproduce: `scripts/assess_sexual.py` (civil_comments moral-valence decomposition + second-corpus
scan). Discovery context: `docs/SPECTRUM_FINDINGS.md`.
