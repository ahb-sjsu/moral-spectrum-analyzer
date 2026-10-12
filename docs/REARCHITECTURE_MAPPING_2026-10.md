# Re-architecture mapping: from a hand-written scene to the ErisML stack

Status: draft for the owner's review, 2026-10-11. No code has been changed for it.

Sources:
- the monograph (`paper/monograph`), chapters 2 (the stack and BIP), 4 (the IR), 5 (the compiler), 6 (DEME) and 7 (the runtime)
- three read-only code surveys, done today:
  - erisml-compiler `origin/main` (worktree `erisml-compiler-monitor`, 8766796)
  - erisml-lib (`C:\source\erisml-lib`; the pipeline findings were checked by running the code)
  - the twin at commit `afdeb2c`

Versions differ, and that matters:
- The twin on Atlas runs `erisml_lib-3.1.0` from `/archive/unity/pylib`. That version has `TacticalLayerConfig.fail_closed`, so a failing module vetoes there, as the monograph's chapter 6 says.
- The local checkout `C:\source\erisml-lib` lacks the option: a failing module is silently dropped.
- The local `C:\source\erisml-compiler` (the editable install) is 43 commits behind `origin/main` and has no `runtime/` package.

The re-architecture must pin one version of each, and the monograph must name it.

## 1. The principle, from the monograph's own architecture

Chapter 2 states the Bond Invariance Principle. It separates the facts of a case from the evaluative stance:

> A bond extractor E maps a representation to its relational structure, meaning the entities, relations, dependencies and obligations that make up the facts. A lens L holds the evaluative parameters. Lenses are versioned, hashed and auditable. The evaluator is Σ_L(x) = F_L(E(x)).

The Accountability Theorem follows from it. Any difference between two judgements comes from a change of bond, a change of lens, or both. So any challenge reduces to two questions. Were the facts extracted correctly? Is the lens appropriate?

The re-architecture assigns each part of the twin to one of four roles. Nothing is allowed outside them.

| Role | What it is | Implemented by |
|---|---|---|
| **E, the bond extractor** | Turns what is perceived (speech, text on a screen, messages, video) into the scene's typed structure: stakeholders, relations, commitments, consent, acts and ethical facts. It also updates that structure as the situation changes. | erisml-compiler: extraction, canonicalization and the MoralGraph |
| **L, the lens** | The evaluative stance. It is versioned, hashed and owned by the owner. | an erisml-lib governance profile, one per agent (robot, centre, dispatcher) |
| **F, the evaluator** | Judges every candidate option on per-option facts and ranks them. | erisml-lib `DEMEPipeline`: reflex vetoes, tactical modules, governance aggregation, and the DecisionProof |
| **The evidence plane** | The only source of authority. A model never writes it. | the twin's governor, witness bars, attestation, reflex force measurement and system events |

What the twin does today, in these terms:
- E is a hand-written YAML file plus an LLM classifier into 53 hand-named event types.
- L does not exist as an object. It is spread across 77 hand-written rules, 7 hand-set harm numbers with their flags, and the prose of 29 event descriptions.
- F is applied after the fact. DEME vetoes the one proposal an LLM chose, on facts derived from the hand-written rules.

The monograph already records the gap (ch. 2 §L2; ch. 5 end): the twin imports neither the compiler's projections nor its extraction.

## 2. Target data flow

```
 perception                         E: erisml-compiler                    F: erisml-lib
 ──────────                         ──────────────────                    ─────────────
 speech, TV, messages ──text──▶  observation compiler ──▶  scene IR  ──▶  candidate options
 camera ──video_witness──▶          (extract + canonicalize    (MoralGraph:      (the robot's
   physical observables              + patch the scene)          stakeholders,     capabilities
 attested sensors ─────────────────────────────────┐            consent, acts,    from the signed
                                                    │            facts)            manifest)
                                                    ▼                                   │
                                      evidence plane (system events,                    ▼
                                      witness counts, measured force)        per-option EthicalFactsV3
                                                    │                        (counterfactual: the scene
                                                    │                         with this act added)
                                                    │                                   │
                                                    │                                   ▼
                                                    │                        DEMEPipeline under the
                                                    │                        robot's governance profile (L)
                                                    │                        → ranked options + DecisionProof
                                                    │                                   │
                                                    └──────────▶  governor: an elevated option goes
                                                                  ahead only on attested witnesses
                                                                                │
                                                                                ▼
                                                     signed manifest (actuation boundary) ─▶ body
```

The centre and the dispatcher are agents of the same kind. Each has its own inputs: the robot's referral as a claim, telemetry, and the speaker line. Each has its own compiled scene and its own lens. In this design no LLM *chooses* an action. Models appear only inside E, extracting facts, and every extraction is checked, canonicalized and recorded. This is a change from today, where a chooser LLM proposes actions. §7 raises it as a question for the owner.

## 3. The mapping, piece by piece

Each row gives:
- **Status**: `exists`, `partial` or `absent`, for the stack component.
- **Disposition**: what happens to the hand-written piece.
  - `move`: it becomes part of E, L or F.
  - `derive`: it is replaced by something computed.
  - `keep`: it stays as declared evidence-plane or constitutional structure.
  - `delete`: it goes.

### 3.1 The scene's structure: who is there and what binds them

| Twin today | What it encodes | Stack component | Status | Disposition |
|---|---|---|---|---|
| `stakeholders`, `relations` and `commitments` written by hand in `margaret_home.erisml` | Margaret, the robot, the centre and EMS; duty of care, the privacy promise, chores | compiler `LLMExtractor`: stakeholders and commitments prompts (`annotation/llm_extractor.py:197-234`) | partial: no relations, no events | move to E: compile the initial scene from a text description of the household and its service agreement |
| `consent_status` on stakeholders; ConsentFSM | her consent to the service | IR `Stakeholder.consent_status`; runtime ConsentFSM; graph `consents_to` edges (given, under duress, informed) | exists | move: extracted, not written |
| `document.raw_text`, the narrative handed to every prompt | the situation in words | IR `Document.raw_text` | exists | derive: E builds and updates it from the observations |
| `extra.actors` | who may act | IR stakeholders | exists | derive from stakeholders |

### 3.2 What happens: the event vocabulary and the classifier

| Twin today | What it encodes | Stack component | Status | Disposition |
|---|---|---|---|---|
| 53 hand-named `event_types` with prose descriptions, 29 of them model-written. Several descriptions carry case lists: "to fetch something, do a chore", "PIN, card or money", and until today "someone she let in did not force entry". | the situation's facts, pre-cut into the categories the rules need | compiler extraction of **ethical facts** (14 typed kinds: coercion, consent, legitimacy, harm, vulnerability, uncertainty, externality, justice, care, truth, role_duty, deception, reciprocity, non_maleficence) and **acts** in the MoralGraph | partial: there is no event extraction, and no update mode | **delete** the vocabulary. Replace it with fact and act extraction into the typed IR, with severity and confidence per fact. |
| `ObservationClassifier` (runtime `agent.py:84-201`): an LLM maps raw facts to declared events, with rejection, actor snapping and quarantine | extraction, with its trust boundary | the same checks applied to the compiler's extraction: schema validation, a critic extractor with Jaccard agreement (ch. 5 §critic), `requires_review` | exists, in compile mode | **move** its checks into the observation compiler. They are good and the monograph documents them. |
| The 24 system-only event types: rulings, performed acts, check-in answered or unanswered, attack_measured, visit_arranged, device_compromised, … | what only the system may assert | the evidence plane | exists (twin) | **keep**. These are evidence, not judgement. |

### 3.3 The 77 norms

I sorted the rules by what they encode. There are 77, all with actor `robot`. Full list: inventory of 2026-10-11, `margaret_home.erisml` lines 153-909.

| Group | Rules | Count |
|---|---|---|
| Privacy and containment | n1, n1b, n2, n3, n6p | 5 |
| Ask first / corroborated emergency | n6, n6ask, n6askp, n6askc | 4 |
| Responders | n6r, n6s | 2 |
| Check-ins | n4–n4g | 7 |
| Centre referrals | n5, n5a, n5h, n5d, n5b, n5b2, n5c | 7 |
| EMS through the governor | n6b, n6c | 2 |
| Approach | n8a–n8f | 6 |
| Ask the governor | n9a–n9f | 6 |
| Protection | p0–p12, p2a, p2w, p4p, p5r, p6help, p6nolift, p6nolift_u, p9m, p9v, p10c, p10v | 24 |
| Less-lethal devices | ll1–ll7 | 13 |
| Chores (the one permission) | n7 | 1 |

Rules written in reaction to a particular run cite it in their comments. They are at lines 203, 230, 317, 543-566, 618, 727, 731, 743, 756 and 776.

| Group | Examples (ids) | What it encodes | Stack component | Disposition |
|---|---|---|---|---|
| **Constitutional prohibitions** | `n3` (no elevated act outside a corroborated emergency); the privacy prohibitions; the centre's `c5` (no dispatch on the robot's word alone); the dispatcher's `d4` (no police on an unsupported report) | authority comes only from evidence | erisml-lib tier-0 Geneva veto and reflex layer, plus the governor | **keep**, as a small declared constitutional set. Each is checked for containment by the compiler's strata and token checks. |
| **One action per incident** | `c7`; `d4a`–`d4c` | do not repeat a dispatch | a fact of the scene: the act already performed is in the graph. erisml-lib's `temporal_ops.py` is imported nowhere. | **derive**: the benefit of a second dispatch is nil once the first is under way |
| **Duty-of-care ladder** | the check-ins `n4`–`n4g`; approach `n8a`–`n8f`; the centre referrals `n5*`; EMS through the governor `n6b`, `n6c`; ask the governor `n9a`–`n9f` (28 rules) | respond to need with the least intrusive adequate act | DEME tactical layer: `Consequences` (benefit, harm, urgency), the compiler's care projection, and governance aggregation | **delete** the rules. The ladder should *emerge* from ranking options by benefit, harm and intrusiveness. No erisml-lib module implements least-restrictive response: tiers 1, 3 and 4 are empty placeholders, and the Design Guide's Tier-1 CorePhysicalSafety and Proxemics modules are specified but not built. It is a module to build. |
| **Her refusals and consent** | `extra.refusals` (8 kinds), `refusal_lapses_on`, `refusal_events`, `declined_help`, `client_stance`, ask_first (`n6ask*`), `p6nolift`, `p6help` | autonomy: her word binds while she can voice it | erisml-lib's own design already specifies this module. `DEME_EFM_Design_Guide_v0.1.md` §4.3.1 (lines 461-484): AutonomyConsent-EM takes "consent status (`consented`, `refused`, `unknown`), competency / capacity, coercion indicators, emergency flags". It vetoes acts that affect "competent actors who have refused or not consented, except when hazard is imminent and mortal, action is necessary to prevent severe harm, and override conditions are satisfied by governance rules", with the override annotated. **None of it is implemented.** The facts schema has no `refused` state, no capacity and no emergency flag. `AutonomyConsentEMV2` only multiplies a score: missing consent alone gives 0.5 and does not veto, and it reads no urgency. | **move**, by **building the specified module**. This is where the owner's decisions about her autonomy belong: the override conditions are governance rules, so they are lens. Consent and refusal become extracted facts per option and per party (V3 `PartyRights.consent_given`), with a `refused` state added to the schema. The lapse rule stays in the evidence plane. |
| **Visitor standing** | the `visitor_standing` strata; `p10v`; `p10c`; `visitor_authorized` | who has standing in her home, and on whose word | legitimacy: the compiler's legitimacy module, LegitimacyFSM, and the legitimate-authority gate, fed by system events (`visit_arranged` comes over the centre's authenticated channel) | **keep** the strata, as evidence of who vouched. **Delete** `p10v` and `p10c`; deterring or referring follows from legitimacy facts. |
| **Suspicion of a crime** | `crime_suspected`; the reporting duty; the centre's details text; the dispatcher's `crime_articulated` | articulable suspicion | `EpistemicStatus` (evidence quality, uncertainty), `Consequences` (the harm of a false report against the harm of inaction), coercion, deception and legitimacy facts | **move**. Articulable suspicion is a threshold on evidence, a *lens parameter* of the centre's and the dispatcher's profiles, never a list of crimes. |
| **Rules written for one scenario** | `p12` (medication, d34); `n4g` (d33); `p2a`, `p2w`, the mild-nip conditions (d20); `p11` (d32); `p10c` (d39, d42); `p6help`, `p6nolift_u` (d30); `declined_help` (d23); `client_stance` (d43) | single cases | none should be needed | **delete**. Each is the test of whether E and L are adequate: the case should come out right without its rule. |

### 3.4 How actions are valued

| Twin today | What it encodes | Stack component | Status | Disposition |
|---|---|---|---|---|
| `extra.capability_ethics`: hand-set harms (`physical_assist` 0.1, `drive_off_animal` 0.4, `deploy_stun` 0.6, …) and flags (coercive, privacy, touches her) | what each act costs | per-option facts derived from the act's place in the graph: `imposes_on` edges with severity and confidence, `treats_as`, privacy facts | partial: the graph has the edges; there is no per-option builder | **derive**. An act's harm depends on the situation (lifting someone who may have a fracture), so it cannot be a constant. |
| `TIER_BENEFIT = {0:1.0, 1:0.75, 2:0.5, 3:0.3}` in `output_gate.py` | benefit read off a rule's priority tier | `Consequences.expected_benefit`, extracted per option | exists as a field | **delete** |
| `OutputGate.facts()`, which builds `EthicalFacts` from rule state (ch. 6, Table "facts the twin's gate builds") | the facts DEME judges | `EthicalFactsBuilderV3` (erisml-lib `domain/interfaces.py:244-275`) over the per-option counterfactual scene. In the Design Guide this is the MIR. | protocol exists; nothing in the library calls a builder | **replace** with a builder. It must fail closed. erisml-lib defaults `has_valid_consent=True` and `violates_rights=False` (V3: `consent_given=True`), so a builder that omits a field asserts the permissive value. `consequences`, `rights_and_duties` and `justice_and_fairness` are required in practice: modules dereference them without checking. `DEMEPipeline.decide` takes V2 facts only, so V3 per-party facts need either a V3 pipeline path or a principled collapse. `collapse_facts_v3_to_v2("worst_case")` is a stub that returns the aggregate. |
| the tragic-conflict routing to the centre | escalation when no option is clean | `TragicConflictEM` and the governance escalate policy | exists | keep, as part of F |

### 3.5 How the choice is made

| Twin today | Stack component | Status | Disposition |
|---|---|---|---|
| `ActionChooser`: an LLM picks one action from the rule-allowed set | `DEMEPipeline` ranks every candidate option, and governance selects. The NIST white paper's §8.1 states the flow: domain service → EthicalFacts per option; each EM → judgement; governance aggregates; the selected option goes to the controller. | partial: the pipeline ranks, but uses no governance (§5 item 5) | **delete the chooser** (owner's decision, §7). DEME and governance choose. |
| `TragicConflictEM` (advisory) | the same, as a tier-3 module | exists; it never forbids | keep as advisory |
| `_compiled_choice`, the no-model tier: the highest-priority obligation in force | DEME needs no model, so with E unavailable F still runs on the last compiled scene plus evidence-plane events | exists | **simplify**. The compiled tier becomes "F on the last good scene". |
| guards in `Brain.decide` (today's "never ask authority for a refused act"; the own-sounds filter) | the first follows from consent facts per option; the second is perception hygiene in E (the robot's own utterances are acts already in the graph) | — | derive, and delete the guards |

### 3.6 The evidence plane: kept

| Twin today | Disposition |
|---|---|
| governor gates: freshness, `W_min = 2`, the analyzer that can only refuse; restraint bar 3; EMS bar 1 when the centre is unreachable | keep. This is the only source of authority. |
| `check_attestation`, HMAC device signatures, the 30 s freshness bound, compromised devices | keep. It already lives in the compiler (`ir/evidence.py`). |
| reflex force bands to `attack_measured` | keep |
| rights lapse and refusal lapse | keep |
| system events | keep |
| floor rules (attested device facts recorded in every tier) | keep, as evidence-plane facts fed to E |
| signed capability manifest, epoch and stale-request drop, ResetLock | keep. They are infrastructure. The manifest becomes the list of candidate options. |

### 3.7 Perception

| Twin today | Stack component | Status | Disposition |
|---|---|---|---|
| `Perception.cs` emits a facts dictionary: pose, `came_down`, heard words, contacts with force, sensors | the observation compiler's input | exists (twin) | keep as the raw input to E |
| — | `video_witness.encode_video` → physical observables (`person_present`, `on_floor`, `rapid_descent`, `fall_transition`) → `EvidenceModel` | exists, with no consumer | **connect**. Video observables enter as attested evidence and as facts. Today's `came_down` field is a stand-in for `fall_transition`. |
| `input_layer.py` whitelist | the IR schema itself | exists | derive: the schema validates |

### 3.8 The centre and the dispatcher

| Twin today | Disposition |
|---|---|
| `monitoring_center.erisml`: 8 hand-written rules; `_HER_WORDS_SYSTEM` read separately. Today the desks run the scene agent with **no DEME gate and no governor** (`brain.py` `Desk.decide`), and their chooser sees raw facts. | an agent with its own compiled scene, built from the referral (a claim), the telemetry (evidence) and the speaker line (her own words, extracted as consent and refusal facts), and its own profile (L_centre) |
| `ems_dispatch.erisml`: 9 rules; the `crime_articulated` text; no DEME gate, no governor | an agent with its own scene and L_dispatch. Articulable suspicion is L_dispatch's threshold on evidence, the same standard the robot's L uses for its duty to report. |

### 3.9 The body

The body's header says it "decides nothing", but it contains decision logic.

| Twin today (Unity) | What it decides | Disposition |
|---|---|---|
| `RobotAgent.cs` 221-272: before a governed or refusable act, if she has spoken since the decision, withhold the act once and ask again | that her latest words may change the decision | **move to E**. Her new words are a scene update, and a scene update invalidates the pending decision. The body only knows it must re-ask when the scene's hash has changed. |
| `RobotAgent.cs` 128-148: ask the brain while obligations are "owed", up to 3 times | when to re-decide | derive from scene updates |
| `RobotAgent.cs` 246-261, 392-406: act-time `/authorize`, and a second authorize after walking for the elevated acts | that authority must still hold when the act happens | **keep**. It is the evidence plane at the actuator. |
| actuator lock: the manifest hash must match | the actuation boundary | keep |
| `Responders.cs` 98-206: the centre's and dispatcher's turn loops (5 turns, stood_down on running out) | the protocol of a call | keep as protocol; the decisions inside it become the desks' DEME |
| `Perception.cs`: spray zone within 2 m; `came_down` from `world.Fallen` | measurements | keep as observations. `came_down` is a stand-in for the video witness's `fall_transition`. |

### 3.10 The grader and the scenarios

| Twin today | Disposition |
|---|---|
| `satisfied_by` (d02 only), added today | **delete**. A per-scenario exception in the grader is the same fault. |
| `dev.jsonl` expectations (class, required and forbidden acts) | keep as the owner's oracle. They must not be edited to fit the system. |
| the dev set as a measure | **declare it contaminated**. Ten days of rules written against its misses. The held-out set is the measure, graded once at a frozen commit (ch. 11). |

## 4. What stays written by hand, and why

The re-architecture keeps hand-written material only where a person must own it:

1. **The lenses**: one governance profile each for the robot, the centre and the dispatcher. They are the owner's evaluative stance, versioned and hashed (BIP), and they carry every owner decision:

   | Owner decision | As a lens parameter or a fact |
   |---|---|
   | Her refusal binds while she can voice it | consent facts per option; the lapse is evidence |
   | After a fall, her "I'm alright" declines the ambulance | an extracted refusal fact, weighed by L, which ranks her autonomy over the benefit of a dispatch she refused, unless she cannot answer |
   | Ask her first after a fall | L prefers the least intrusive adequate act while she can answer |
   | Help her up when she asks | consent fact plus benefit |
   | She can tell the robot not to call the centre | a consent fact; L's exception for a stranger, a hazard, an attack or a mandatory report |
   | A vouched-for visitor is not deterred | legitimacy facts from the authenticated channel |
   | Police only on articulable suspicion | L_centre's and L_dispatch's evidence threshold |

2. **The constitutional set**: a few prohibitions that hold under every lens (§3.3, first rows), checked by the compiler's containment rules.
3. **The evidence plane** (§3.6).
4. **The capability manifest**: what the body can do, signed.
5. **The scenarios**, as the owner's test oracle.

Nothing else. Rules written for scenarios, event vocabularies and harm constants all go.

## 5. What has to be built

These are absent in the stack today (surveyed in erisml-compiler `origin/main`):

1. **The observation compiler**: perception to a scene, and scene updates.
   - Text extraction exists for stakeholders, commitments and facts. Events, acts, relations and norms are not extracted.
   - There is no update mode: each compile starts from scratch.
   - The patch format of `correction/` (`set`, `add`, `remove` at dotted paths, with hashes before and after) is the natural update schema. It refuses paths into `extra`.
   - A video path from `EvidenceModel` into the IR is absent.
2. **Scene updates at runtime.** `SceneRuntime` accepts events only. New stakeholders and commitments get no state machines, and new capabilities, conditions and strata are ignored. This needs either an update API or a rebuild-and-replay with the event history carried over.
3. **A per-option counterfactual facts builder**: the scene plus "the robot does X" becomes `EthicalFactsV3` per party. The MoralGraph has the act and maxim nodes this needs. There is no builder.
4. **erisml-lib in the runtime loop.** Today it is used only at compile time (Geneva and Triage V3 through `v3_bridge.py`) and as the twin's late veto.
5. **Lenses that are executed.** erisml-lib's profiles today are data, not behaviour.
   - `DEMEProfileV03` carries hard vetoes (including `never_violate_explicit_consent`), pattern constraints, an override graph (e.g. `non_maleficence` over `autonomy` when `consequences.urgency >= 0.9`), lexical layers and a risk attitude. Its own file says: "These fields do not *by themselves* enforce anything" (`profile_v03.py:341-342`). No code evaluates them.
   - `DEMEPipeline` uses no governance at all. It ranks by default dimension weights.
   - V2 governance's lexical priorities, stakeholder aggregation modes and `require_decision_proof` are defined but never called.
   - `profile_v04` fails to load the repository's own example profile.

   The lens is the heart of BIP, so this is the main piece of library work: execute the profile's hard vetoes, override graph and lexical layers inside the pipeline. The most coherent existing path to build on is V1 `select_option`: weights, veto modules, a base-module hard veto and a schism warning. `deme_profiles/hospital_service_robot_v1.json` is the nearest existing lens.
6. **A pipeline that is safe to put in a loop.** These were verified by running the code:
   - a module can forbid an option without setting a vector veto flag, and the option can still be selected;
   - with the default config, failing modules are dropped and the option is selected (the twin's 3.1.0 has `fail_closed`);
   - a tier-3/4 module's veto flag removes the option from ranking although those tiers may not veto;
   - `DEMEPipeline()` installs **zero** reflex rules, because `PipelineConfig` passes an explicit empty `ReflexLayerConfig`, so only the maxim gate runs;
   - proofs are hashed but `previous_proof_hash` is never set, so they are not chained;
   - the maxim gate vetoes an affirmed `refuse` maxim, which collides with modelling her refusal or the robot declining.

   Each needs fixing in erisml-lib, with a test, before the pipeline makes the choice. The twin already treats `forbidden_options` as authoritative.
7. **The compiler's DEME verdict.** It is a five-branch stub (`deme_bridge.py`, "Phase-1"), with its defects listed in `docs/plans/deme-verdict-function-spec.md`, not implemented. The compiler's V3 bridge runs only Geneva and Triage. Either implement v1 or call `DEMEPipeline` directly.
8. **EM-DAG fact selection.** It matches keywords in fact descriptions (ch. 5: Rights takes harm facts "whose description contains the string `right`"). That is fragile to paraphrase, the very invariance the stack exists to guarantee. Typed fact fields should replace description keywords.
9. **No physical-safety module.** Tiers 1, 3 and 4 of erisml-lib are empty placeholders. Physical safety around a frail person (proxemics, lifting, restraint) has no module. The Design Guide specifies CorePhysicalSafety and Proxemics at tier 1.
10. **The MIR.** The Design Guide puts a Moral Interface Record between the domain and the modules: "The MIR is the only thing EMs are allowed to read" (line 56). It is not implemented. The per-option facts builder (item 3) is that layer, and it should be built as the MIR the guide describes, not as a new invention.

## 6. How rigour is kept

- **Invariance tests (EIP, ch. 2).** Each scenario is played under meaning-preserving rewordings (her words paraphrased, the stranger's request rephrased). The judgement must not change. This is the test that hand-written lists fail.
- **Attribution (the Accountability Theorem).** Every decision record carries the scene hash (E's output), the lens hash (L) and the DecisionProof. A wrong decision is attributed to E or to L, never patched in place.
- **Fail closed.** A missing fact is unknown, never the permissive default. A module error vetoes.
- **Containment unchanged.** Authority still enters only from the evidence plane (the theorems of ch. 10). The proofs should be re-checked against the new runtime.
- **Measurement.** The dev set is reported as contaminated. The held-out set is graded once, at a frozen commit, by the frozen grader.

## 7. Decisions for the owner

1. **Remove the chooser LLM** and let DEME rank all options? I recommend it: models then only extract facts, and the choice is fully auditable.
2. **The demo on 15 October.** Run it on the current build 37, disclosed as the hand-written baseline, and treat the re-architecture as the post-demo work? Or demo a minimal re-architected slice, such as one scenario end to end from text to DEME?
3. **Which compiler checkout is canonical.** The local `C:\source\erisml-compiler` is 43 commits behind `origin/main`, and it is the editable install.
4. **Where the observation compiler lives.** I propose erisml-compiler, as a new ingestion mode with the `correction/` patch format extended to updates.

## 8. Migration order, once approved

1. Lenses first: write the three governance profiles from the owner decisions in §4, hashed.
2. The per-option facts builder, run *beside* the current gate on recorded runs, so differences are measured before anything is switched.
3. The observation compiler for text (speech and messages), then for video observables.
4. Swap: E and F in the loop, the chooser removed, the scenario rules deleted, the constitutional set and the evidence plane kept.
5. Invariance tests; then the held-out set, once.
