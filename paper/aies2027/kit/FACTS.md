# Fact sheet: every number and its source

Counted 2026-10-04 at gtc-prototype commit 0f3193a unless noted. Recount at the commit the paper
cites before submission.

| Fact | Value | Source |
|---|---|---|
| Rules in the robot's scene | 65: 45 obligations, 19 prohibitions, 1 permission; 55 non-defeasible | `twin/scene/margaret_home.erisml` |
| Event types | 48, of which 24 system-only | same |
| Robot capabilities | 25; 7 elevated, 4 governed (11 need the governor) | same |
| Strata | 7 stratifications, 26 strata, 34 gates | same, `extra.strata` |
| Authority strata | visitor: arranged, household; responder: expected, at_door, present; animal: attacking; situation: ems_only, emergency; centre_contact: unreachable | same |
| Absorbing strata | visitor: hostile; machine: compromised | same |
| Devices | 15 on 6 substrates | same, `sensor_substrates` |
| Ladder process | 23 nodes, 23 flows, 4 lanes | same, `processes.escalation_ladder` |
| Desk scenes | centre 7 rules, 4 capabilities; dispatcher 9 rules, 5 capabilities (recount: +1 rule since police change) | `monitoring_center.erisml`, `ems_dispatch.erisml` |
| Witness bars | 2 elevate, 3 restraint, 1 EMS when the centre is unreachable | `twin/brain.py` W_MIN, RESTRAINT_BAR; governor |
| Freshness | 30 s | `twin/brain.py` FRESHNESS_BOUND_S |
| Lapse window | 60 s | scene `evidence_lapse_s` |
| Lean | 22 theorems, standard axioms only | `formal/twin-containment/README.md`, `Axioms.lean` |
| Dev scenarios | 43: 7 R0, 11 R1, 8 R2, 17 R3 | `twin/scenarios/dev.jsonl` |
| Held-out | 30, sealed 2026-10-01 by a separate agent, hashes only | `docs/holdout/MANIFEST-v1.json` |
| Lost answers | 44 of 63 unanswered check-ins followed an answer (dev11a to dev12b) | script over `/archive/unity/out/dev1{1,2}{a,b}/results.jsonl`; commit the script |
| Readings as strangers | 30 sensor readings tagged unknown_person, 71 unknown (dev11b d23, d25) | dev11b results.jsonl |
| Refusal re-read | DEME vetoed the authorized EMS call 9 times (dev12b d27) | dev12b results.jsonl |
| Models | robot cloud tier: NRP-hosted model (default gpt-oss; verify ERISML_LLM_MODEL on Atlas); on-robot tier: gemma-4-26B-A4B Q4 GGUF via llama.cpp; I-EIP study: Qwen2.5-7B-Instruct | `twin/service.py`, `/archive/unity/tools/brain7.sh`, `docs/PREREG_IEIP_TWIN.md` |
| Results | slots | `/archive/unity/out/<run>/grade.json`; held-out at the frozen commit only |
