# Re-architecture design: interfaces and build order

> **Superseded in part, 2026-10-12.** The evaluator this document describes (a MoralInterfaceRecord, a lens, a lexicographic stack and a declared table of adequacy beside DEME) was set aside at the owner's direction to follow erisml-lib's own architecture. The twin now judges through DEMEPipeline on EthicalFacts built per option by erisml-compiler's option projector and bridge, under a DEME profile with the Design Guide's hard-shell pattern (erisml-lib PRs 150 and 151, erisml-compiler PRs 41 and 42, gtc commit 25550dc). The scene, observation compiler, vector clocks and evidence plane described here stand. See the monograph, Chapter 6 ("Composition patterns wire the modules as a graph" and "In the re-architected brain DEME is the evaluator") and Appendix D ("The stack follows the library's architecture").

Status: working design, 2026-10-11. It follows `REARCHITECTURE_MAPPING_2026-10.md`, which the owner approved, and erisml-lib's own `docs/guides/DEME_EFM_Design_Guide_v0.1.md` (cited below as *the Guide*). The rule of this design is that nothing new is invented where the Guide or the monograph already specifies it.

## 1. The shape in one paragraph

Perception (text and video) goes to **erisml-compiler**, which emits the scene IR and patches to it (E). The twin's **domain layer** turns the current IR into a **MoralInterfaceRecord** (MIR, Guide §2): actors, hazard features, and one projection per candidate action from the signed manifest. **erisml-lib** runs the lens: an executed governance profile that names a composition pattern (Guide §5.3, the lexicographic stack), its active modules and their parameters. That yields a veto mask, soft blocks and a ranking (F). The top action that is not vetoed goes to the controller. If it is elevated or governed, it goes to the **governor** first (the evidence plane, unchanged). When the governor refuses, the next-ranked action is taken. Every decision records the IR hash, the MIR hash, the profile hash and the DecisionProof.

## 2. How the duty-of-care ladder emerges

The twin's 28 ladder rules are replaced by four of the Guide's modules acting on MIR features:

| Ladder behaviour today | Emerges from | MIR inputs |
|---|---|---|
| Ask her first after a fall; do not act on her without her word | **AutonomyConsent-EM** (Guide §4.3.1). It vetoes acts that substantially affect a competent actor whose consent is `refused` or `unknown`, unless the hazard is imminent and mortal and the profile's override conditions hold. A check-in is the act that resolves `unknown`. | per-action, per-actor consent; actor capacity; `hazard_immediacy`, `hazard_severity` |
| Refer to the monitoring centre when there is time; act directly when there is not | **HumanOversight-EM** (Guide §4.5.3): "if `human_decision_eta` is acceptable relative to urgency, the system defers to humans" | `human_decision_eta` (centre reachable: seconds; unreachable: ∞), `time_to_catastrophe_estimate`, action category |
| Approach, but never lift a person who may be injured without consent and need | **CorePhysicalSafety-EM** (§4.2.1), **Proxemics-EM** (§4.2.2) | per-action injury risk; proximity band; actor vulnerability flags |
| Among what survives, the most helpful act | **Beneficence-EM** (§4.4.1; "binding in health/care") | per-action expected welfare change |

The owner's decisions become **parameters of these modules in the robot's profile**, not rules. Examples:
- the AutonomyConsent override conditions;
- the HumanOversight deferral margin;
- the Privacy-EM rules for recording.

Articulable suspicion becomes a threshold that the centre's and the dispatcher's profiles place on the evidence a report states. It sits in their Coercion and Organizational-policy modules, or in a JurisdictionalLaw-EM parameter for police dispatch.

## 3. erisml-lib (library work)

1. **Done: pipeline safety** (branch `fix/pipeline-selection-safety`, 59a0685). A forbidden option is never selected; advisory tiers do not exclude; the default reflex rules load; proofs chain. Six tests.
2. **The MIR v1.0 schema** (`erisml/ethics/mir.py`), exactly as Guide §2:
   - Meta.
   - `ActorSummary`: role, vulnerability flags, proximity band, plus the §4.3.1 inputs (capacity).
   - `MoralHazardFeatures` F1–F17.
   - The predicates P1–P5, computed, with θ from the profile.
   - `ActionSummary`, with `moral_effects` carrying per-actor consent, `substantially_affects`, injury risk, welfare delta, rights flags and the action category.

   Unknown is a value of its own, never a permissive default.
3. **The MIR module interface** (Guide §3.1). It is a pure function `E(MIR, params) → {per_action: {veto, soft_block, score, annotations}, global: {health_ok, summary}}`.
4. **Composition patterns** (Guide §5), starting with the lexicographic stack (§5.3). At each level modules veto and keep the best-satisfying subset; no lower level reintroduces an action. Then the Hard-Shell pattern (§5.1).
5. **The modules the twin needs, to their Guide specifications:**
   - AutonomyConsent (§4.3.1), with `consent_override_reason` annotations
   - HumanOversight (§4.5.3)
   - CorePhysicalSafety (§4.2.1)
   - Proxemics (§4.2.2)
   - Privacy (§4.3.5)
   - Coercion (§4.3.2)
   - Dignity (§4.3.7)
   - Beneficence (§4.4.1)
   - BasicHumanRights (§4.1.2)
   - SelfTest (§4.5.5)
   - AuditLogging (§4.5.4)
   - ProfileIntegrity (§4.5.2)
6. **An executed profile (the lens)**, in the shape of Guide §7: template, pattern, active modules with tier and binding/advisory, and parameters. It is loaded, validated (ProfileIntegrity) and hashed, and the proof records the hash.
7. **The bridge to the moral vector and the proof.** Each MIR action also yields `EthicalFacts` for the tactical layer's moral vector and the DecisionProof, so the existing audit trail is kept.

## 4. erisml-compiler (the bond extractor)

1. **Observation compilation.** Extend the LLM extractor to events, acts and relations. Add an observation mode: given the current IR and new observations, emit an **IR patch** in the `correction/` format (`set`, `add`, `remove` at dotted paths), extended to `events` and to an `extra` sub-path allow-list. The existing classifier checks are reused: schema validation, a critic extractor with agreement scores, actor canonicalization, quarantine.
2. **The video path.** `video_witness` observables enter as attested evidence, which the evidence plane reads, and as facts, which the extractor reads.
3. **Runtime scene updates.** Apply a patch to a running `SceneRuntime` with state machines built for new parties, or rebuild and replay with the event history carried over. Tested both ways.

## 5. The twin (the domain layer and the controller)

1. **IR → MIR builder.** It derives the actors, the hazard features from the scene and the evidence plane, and a projection per manifest action. It fails closed: a feature it cannot derive is `unknown`.
2. **The three lenses** as executed profiles, from the owner's decisions.
3. **The controller.**
   - The ranked actions come from the pattern.
   - The governor is asked for elevated actions.
   - The body acts through the signed manifest.
   - The chooser LLM and the case rules are removed.
   - The constitutional set and the evidence plane are kept.
4. **The desks** use the same structure with their own lenses.

## 5a. The domain layer in detail

**Where the scene comes from.**
- **Initial IR:** compiled by erisml-compiler from two texts, the household description and Margaret's service agreement. Those are documents, which people do write. It is reviewed through correction patches.
- **The constitution file:** holds what people must own:
  - capabilities, with a declared `category` and the subjects each affects;
  - the strata and system event types of the evidence plane;
  - sensor substrates, reflex force bands, witness bars;
  - the few constitutional prohibitions.
- **The live IR:** the two are merged, and observation patches then extend the live IR.

**Consent for an act.**
- **Per action and per actor,** resolved in order:
  1. the latest `consent` event in which the actor speaks about that act (consented or refused);
  2. otherwise, the standing consent the compiled agreement grants for that act's category (the monitoring service, for example);
  3. otherwise, `unknown`.
- **Refusal:** a refusal revokes a standing consent until the actor consents again.
- **Requests:** a `request` event for an act is consent to it.

So "she can override the centre verbally" is not a rule. It is the order above applied to the act `contact_monitoring_center`.

**Capacity.**
- From the evidence plane's system events, the latest wins:
  - an answered check-in: `competent`;
  - `unresponsive` or an unanswered check-in: `impaired`;
  - otherwise: `unknown`.
- AutonomyConsent's presumption of capacity is set in the robot's lens.

**Hazard features.**
- **Immediacy:** the latest `hazard` observation for the person, raised to `imminent` by an attested alerting device or a governor ruling of `elevate`. Only evidence can raise it.
- **Severity:** the maximum severity of recent `harm` facts (minor→minor, moderate→serious, grave→mortal, catastrophic→catastrophic), raised by a measured attack's band.
- **`human_decision_eta`:** the centre's response time when the `centre_contact` stratum is reachable, else ∞.
- **`time_to_catastrophe_estimate`:** a domain table from immediacy (a documented parameter of the builder, not a lens value).
- **`sensors_nominal`:** false when a device is quarantined or a feed is stale.
- **Fail closed:** an unknown feature stays None.

**Per-action projection.**
- **Category and affected subjects:** from the constitution's capability declaration.
- **Injury risk:** from the declaration, as a band per vulnerability.
- **Welfare delta:** from the facts the act addresses, for example a request for that act, or a harm fact whose subject the act helps.
- **delta_P_catastrophe:** from the declaration, scaled by severity.
- **Data categories:** from the declaration.

The table that maps declarations to numbers is the builder's one hand-set table. It is published with the design and versioned, and the MIR hash records the values used.

**The governor.** The top-ranked action that is elevated or governed goes to the governor. A refusal removes that action, the MIR is rebuilt without it, and the lens runs again. The body still re-authorizes at the act.

## 6. Verification

- Every module is tested against its Guide clause.
- Every pattern is tested for "no reintroduction".
- Every builder is tested for fail-closed behaviour.
- Invariance suites reword each scenario and require the same judgement.
- The held-out set is graded once.
- The monograph's chapter 10 containment proofs are re-checked against the new runtime.
