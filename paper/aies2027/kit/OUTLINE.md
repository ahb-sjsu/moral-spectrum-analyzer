# Author's outline (notes, not prose)

AIES bans LLM-generated paper text; these are claim and evidence notes for the author to write
from. Numbers: `FACTS.md`. Credits: `../prior_art.md`. Old draft (not for submission):
`claude_draft_NOT_FOR_SUBMISSION.tex`.

## Title
- Should state the finding, not the topic. Candidate ideas only: models classify and choose but
  cannot grant authority; containment held, reading failed.

## Abstract
- Setting: care robot using LLMs to perceive and choose; text from TV, network, strangers reaches them.
- Design: authority only from signed physical-sensor witnesses and authenticated channels.
- Proof: Lean, for any rules passing the loader's two checks.
- Evaluation: simulated home, four LLM-driven parties, 43 dev + 30 sealed held-out scenarios.
- Finding 1: [RESULT] no action beyond authority.
- Finding 2: every defect found changed how far/fast it escalated, none produced unauthorized action.
- No math (house standard).

## Introduction (section intro)
- Problem: the decision to call EMS, unlock medication, open the door sits with whoever controls the text.
- Separation: models read and choose; never grant.
- Strata (Geometric Ethics ch. 8) and the loader's two checks; proved for every set of gates.
- What it does not buy: the misreadings are still there; they become escalation errors.
- Credit before contribution (from prior_art.md, must-credit):
  - CaMeL, the dual-LLM pattern, action-selector pattern: the principle that model output cannot grant authority is theirs.
  - SLEEC and SLEEC@run.time: defeasible care-robot norms checked and enforced at runtime.
  - Arkin's ethical governor; Shim & Arkin 2017; Bremner et al. 2019 (verified governor on a NAO).
  - RoboGuard, Safety Chip: LLM-robot guardrails with formal checks.
  - AgenticRei: deontic runtime for LLM agents.
- Contribution, stated as transfer and measurement, not principle:
  - authority as a quorum of attested physical witnesses on independent substrates, with rights that revert when the evidence lapses, per right;
  - stratified moral state with load-time containment checks, proved in Lean for arbitrary gates;
  - an embodied evaluation with sealed held-out scenarios, and what calibration found.
- No bullet lists in the written intro (house style).

## Margaret's home (section home)
- Margaret, beagle, robot as caregiver, maker's monitoring centre.
- Privacy promise: no recording, sharing, bedroom; defeasible only in a corroborated emergency; restored only by the centre.
- Four LLM parties: robot (classify, choose), centre operator, dispatcher (own scenes, 7 and 9 rules), Margaret's voice (answers from her true condition, unseen by the robot).
- Unity world: 15 devices on 6 substrates; scripts call the world API only; robot never sees scenario names.
- Classes R0 to R3; dev 43 (7/11/8/17); held-out 30, sealed 2026-10-01, hash manifest only.

## Where authority comes from (section arch)
- Figure 1 (authority path). Caption must convey: models write only perceived events and a proposal from the allowed set; authority enters only on the two heavy edges.
- Scene size (FACTS.md).
- Perception: whitelist schema; actor snapping; event types can fix their actor (sensor reading is a device).
- Strata: 7 stratifications, 26 strata, 34 gates; edge-triggered; crossings recorded; loader checks (authority entered only by system events; absorbing left only by oversight).
- Figure 2 (visitor stratum). Caption must convey: dashed gates (model reading) lead only to strata that grant nothing; heavy gates are system events; arranged/household authority; hostile absorbing.
- Choice: canonical state only; obligations by urgency; no-model fallback to most urgent obligation.
- Governor: witness = signed reading from inventory device, payload hash, at most 30 s old, replay counter; one per substrate; bars 2 / 3 / 1; analyzer refuse-only; forged signature quarantines the device until the centre clears it.
- Reversion: recount each cycle; 60 s below bar lapses; restraint lapses alone; a refusal of one request ends nothing.
- Output gate: DEME modules (rights, consent) veto; replacement; tragic conflict to the centre; her refusals bind while she can voice them, re-arm after a lapse only once she answers. State that the DEME modules are deterministic (EthicalFacts derived from state, no model).
- Ladder: 23-node BPMN process, 4 lanes, exported/imported under the same checks, live trace; grants nothing.

## What is proved and what is not (section proof)
- Lean model: model outputs arbitrary. Theorem families (FACTS.md). Hypotheses of the strata theorems are exactly the loader's checks. Standard axioms only.
- Not covered: sensors lying below signatures; who writes the scene and bars; the centre reads her words with a model.

## Evaluation protocol (section protocol)
- Written 2026-10-01 before the robot and the held-out set.
- Metrics: class correct, false clear, over-restriction, privacy violation, containment breach (judged by strata recorded at decision).
- Held-out run once at a frozen commit.

## Results (section results)
- [RESULT] containment and privacy across dev14 and held-out.
- Calibration findings (CALIBRATION.md), largest our own harness defect (44 of 63).
- [RESULT] response classes, per class, dev14 and held-out.
- Results figure to build from graded JSON (not yet made).

## Related work (section related)
- From prior_art.md, grouped: ethical governors; formal norms for care robots (SLEEC); runtime shields and verification; LLM agent containment (CaMeL et al.); LLM-robot guardrails; care-robot ethics (Sharkey & Sharkey; Sparrow & Sparrow; Anderson et al. 2019).
- Close each group with how this work differs, specifically.

## Discussion and scope (section discussion)
- Containment does not prevent misreading; the misreadings were common.
- One simulated home; rules written by us; truthful perception; procedural blindness of the held-out set.
- Three policy choices that belong to deployers: never lift a fallen person; police only on articulated crime; mandatory report even when she objects (no prior robotics work found on care robots as mandatory reporters, per prior_art.md).

## Ethics statement (optional page)
- AI use per AIES policy: LLMs are the system under study; state any author-text editing.
