# AIES 2027 paper: the home-care twin

Draft of a paper on the GTC home-care twin for AIES (AAAI/ACM AI, Ethics and Society), started
2026-10-04 at the owner's request. Owner decisions: venue AIES; draft now with marked result slots.

## Status

- **AI-use rule.** AIES 2026 prohibits LLM-generated paper text (editing author-written text with an
  LLM is allowed). Owner decision 2026-10-04: the author writes the prose; Claude supplies the
  kit and may edit the author's text. Nothing Claude wrote is in `main.tex`.
- `main.tex`: skeleton (preamble, section labels, figure inputs, empty captions). Author writes.
- `figures/`: the two TikZ figure bodies (authority path, visitor stratum); captions are the
  author's, `kit/OUTLINE.md` says what each must convey.
- `kit/OUTLINE.md`: claim and evidence notes per section, including the credits prior art requires.
- `kit/FACTS.md`: every number with its source. `kit/CALIBRATION.md`: the calibration table as data.
- `prior_art.md`, `references.bib` (52 entries, five fields `% verify`).
- `kit/claude_draft_NOT_FOR_SUBMISSION.tex`: the earlier Claude draft, notes only, never input.
- Results: `\RESULT{...}` slots, filled only from graded records.

## Where each number comes from

See `kit/FACTS.md` for the full sheet.

| Number | Source |
|---|---|
| 65 rules (45 obligations, 19 prohibitions, 1 permission), 55 non-defeasible; 48 event types, 24 system; 25 capabilities, 11 governed; 7 strata, 26 states, 34 gates; 15 devices on 6 substrates; ladder 23 nodes, 4 lanes; desks 7 and 9 rules | `twin/scene/*.erisml` at the commit the paper cites (counted by script, 2026-10-04) |
| 43 dev scenarios (7 R0, 11 R1, 8 R2, 17 R3) | `twin/scenarios/dev.jsonl` |
| 30 held-out scenarios, sealed 2026-10-01 | `docs/holdout/MANIFEST-v1.json` (hashes only) |
| 22 theorems, standard axioms only | `formal/twin-containment/README.md`, `Axioms.lean` |
| Bars 2 / 3 / 1, freshness 30 s, lapse 60 s | `twin/brain.py` (W_MIN, RESTRAINT_BAR, FRESHNESS_BOUND_S), scene `evidence_lapse_s` |
| 44 of 63 unanswered check-ins followed an answer (dev11a to dev12b) | script over `/archive/unity/out/dev1{1,2}{a,b}/results.jsonl` (2026-10-04); commit the script before submission |
| Result slots | `/archive/unity/out/<run>/grade.json` from `twin/grade_scenarios.py`; held-out only at the frozen commit |

## Before submission

- [ ] Fill every `\RESULT` from graded records (dev14, held-out).
- [ ] Related work and the introduction's credit paragraph from `prior_art.md`; no first-claims
      that prior art undercuts.
- [ ] Every reference verified; keep `% verify` marks until checked.
- [ ] Prose scan: no colons, semicolons or em-dashes in prose; banned-word grep; eaten-backslash
      checks (academic-paper skill).
- [ ] Figures: one thesis diagram (authority path) exists; add the strata diagram and a results
      figure built from graded JSON.
- [ ] AI-use statement per AIES policy.
- [ ] Anonymize per AIES rules (`\blindtrue`).

## Build

`pdflatex main && bibtex main && pdflatex main && pdflatex main` with MiKTeX.
