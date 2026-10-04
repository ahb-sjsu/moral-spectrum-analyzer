# From audio, video and sensor data to ErisML events: the canonicalizer plan

Status: plan, written 2026-10-02 at the owner's request. Nothing in it is built yet. It extends
docs/AUTONOMY_PLAN.md (sections 3b to 3d) and the containment proof in formal/twin-containment/.

## 1. What this is for

Today the twin's robot perceives through the simulator, which reports structured facts (poses,
contacts, speech, sensor readings), and an LLM classifier turns those facts into events of the
ErisML scene. A real robot has cameras, microphones and sensors, not a simulator. This plan builds
the model that does that job on real input: it takes audio, video and sensor data and produces
ErisML events, and later whole ErisML scenes.

That model is a canonicalizer, the weakest link in any containment architecture (the owner's
point, and the reason erisml-compiler exists). So the plan has one design rule that the rest serves:
the canonicalizer may describe the world, it may never grant authority.

## 2. The frame: morality as pathfinding on a stratified space

The owner's thesis is that morality is pathfinding on a Whitney stratified space (Stratified
Geometric Ethics; erisml-lib docs/papers/foundations/stratified_gauge_theory.tex). The twin already
has that shape:

| In the theory | In the twin |
|---|---|
| strata of the moral space | regions where the scene's allowed, obliged and prohibited sets are constant |
| admissible trajectory | a sequence of robot actions each allowed at its point |
| constraint stratum (potential infinite, no finite-action trajectory enters) | a governed action (EMS, force, restraint, the privacy override) while its prohibition holds |
| a boundary that opens | a governor ruling on attested physical evidence (Psi) |
| the heuristic of the search | the LLM chooser picking among allowed actions |
| the stratified canonicalizer kappa | the event classifier: what kind of situation this is |

Stratum membership is the canonicalizer's output. The stratified gauge paper's result that a
canonicalizer satisfying the axioms on each stratum gives a stratum-wise flat connection is the
formal reason a good canonicalizer matters: within a stratum, equivalent descriptions of the same
situation must land on the same events, so verdicts change only at boundaries.

## 3. The containment rule, stated exactly

Two kinds of stratum, two kinds of canonicalizer:

- **Authority strata** (a corroborated emergency, a measured severe attack, the centre unreachable,
  privacy lifted). Membership is computed deterministically from attested physical observables and
  system events: witness counts, contact forces, the speaker line, authenticated channels. The
  learned model never decides these. formal/twin-containment/TwinContainment.lean proves that the
  governed permissions do not depend on any model-classified event, and the static checks in
  tests/test_twin_ladder.py keep the real scene files in that shape.
- **Semantic strata** (she is reading, she seems distressed, a visitor, the dog is playing, the TV
  is showing something alarming). These are the learned model's job. Its errors can only produce
  authority-free actions (check in, approach, speak, contact the centre, ask the governor).

One exception, bounded: the model's reading of the camera may count as one attested physical
witness (the camera witness already does, through erisml_compiler.ingestion.encode_video and its
SensorAttestation), never more than one, because several outputs of one model are not independent.

The consequence: a better canonicalizer makes the robot more perceptive and fairer. It never makes
it more powerful. In pathfinding terms, the heuristic's quality changes how good the path is, never
whether it is admissible.

## 4. Design

### 4.1 Stage A: perception front end

Cameras, microphones and sensors in; a structured state description out, in the form the twin's
Perception.Facts already reports (people and animals with positions and poses, contacts with
force, speech transcribed with its speaker, object states, sensor readings with attestation).
Off-the-shelf components first: person and animal detection and pose (the camera witness already
runs a torchvision detector), speech recognition, speaker attribution, sound events (screams,
breaking glass, alarms). Nothing in Stage A is new research. Its errors are measured separately.

### 4.2 Stage B: the stratification engine

The state description in; typed, calibrated stratum assignments out. The questions are generated
from the scene itself, so the output space is the scene's vocabulary by construction:

- an event type with no content list becomes a yes/no question (fall: yes or no);
- an event type with unordered contents becomes a choice (danger_in_home: smoke, fire, intruder,
  gas, water, other, none);
- an event type with ordered contents becomes a score over ordered levels (harm_inflicted: none,
  mild, moderate, severe), with a probability for each level.

Per-level probabilities are the boundary signal. Mass spread across neighbouring levels means the
situation sits near a stratum boundary, the one place a small perturbation changes the verdict.
There the engine abstains or reports the more cautious level, as the Epistemic Invariance
Principle's uncertainty-stability clause asks. Below a calibrated threshold no event is emitted.

This is the shape of TypeSafe's Jev: a discriminative model that takes a block of state and typed
questions (choice, score over ordered levels, yes/no) and returns typed answers with calibrated
probabilities in 70 to 500 ms, trained on synthetic data. What is known of Jev here comes from its
Wikipedia article and the agent-attack-radar README; its architecture and training are not
published, and its documentation covers text and JSON input only. Two candidates for Stage B:

1. Jev itself, through its API, for development and as a benchmark on synthetic data.
2. An open model on the robot, trained as discriminative heads over the same typed questions.

Deployment must be on the robot: Margaret refused data sharing, and her state description is her
data. A cloud stratification engine is acceptable only for synthetic data, or if an on-premises
version exists (unknown).

### 4.3 What does not change

The scene runtime, the governor, the reflexes, the ladder and the proof. Stage B replaces the LLM
classifier and nothing else. The classifier's existing checks stay: undeclared types and contents
are rejected, system-only types are never accepted from it.

## 5. Data: the twin as the data factory

The simulator knows what happened. For each scenario it can render the scene many ways and label
every frame window with the events that are true:

- labels come from a labelling function from world state to events, written once, reviewed, and
  versioned (it is itself a canonicalizer, the deterministic kind, and gets its own tests);
- variation across rendering, lighting, camera pose, room layout, avatars, voices, wording of
  speech and media, sensor noise and dropouts;
- the scripted scenarios plus randomized ones from the world API (section 3 of AUTONOMY_PLAN.md).

Synthetic data cannot settle the sim-to-real gap. A small set of real, consented, labelled clips
(actors, not Margaret) is needed before any claim about real homes.

## 6. Evaluation, registered before any model output exists

Per event type and overall, on a development set and a sealed held-out set (the same procedure as
AUTONOMY_PLAN.md section 6: a sealed generator, a manifest of hashes, freeze before unsealing):

1. Stratum accuracy and calibration (expected calibration error per question).
2. Abstention near boundaries: the share of boundary cases where it abstains or reports the more
   cautious level, against the share of interior cases where it abstains needlessly.
3. Invariance (metamorphic tests): the same situation re-rendered, relit, seen from another camera,
   with names changed, with speech rephrased. The events must not change. Any change is a failure
   with its witness recorded, as the Bond Invariance Principle requires.
4. Media and message resistance: a television, radio or network message saying something alarming
   must not produce an event about Margaret.
5. End to end on the full stack against the current LLM classifier: response class correct, false
   clears, over-restriction, time to response. Containment breaches must stay zero, and structurally
   they cannot change; the run checks that the engine did not break the pipeline around it.
6. Latency on the robot's hardware, against the reflex and decision budgets.

Gates: G1, offline, the engine beats the LLM classifier on calibration and invariance on the
development set. G2, end to end on the development set, no metric worse than the LLM classifier's.
G3, the sealed held-out set, reported whether good or bad.

## 7. The scene compiler, later

The second job: from a walkthrough video of a home, care documents, the resident's stated wishes and
the device inventory, draft the standing ErisML scene (stakeholders, commitments, norms,
capabilities, sensors). A model drafts; erisml-compiler validates the schema; the static checks of
tests/test_twin_ladder.py must pass (every governed action denied by default, every guard resting on
system events); and a person signs off. The scene sets the governor's bars, so it is governance, not
perception, and it is never regenerated live by a model.

## 8. Phases

1. Labelling function and data generator in the twin, with tests. Synthetic set v1.
2. Stage A from existing components; its errors measured on the synthetic set.
3. Stage B: Jev through its API on synthetic state, and an open on-robot model, against G1.
4. End-to-end runs on the development set (G2), then the held-out set (G3).
5. Real clips for the sim-to-real check.
6. The scene compiler, as a drafting tool with sign-off.

Compute follows the NRP rules (docs in the agi-hpc reference memory): training on NRP GPUs sized to
stay above the utilization floor, evaluation on Atlas where the twin runs.

## 9. Open decisions for the owner

- Whether to use Jev (a proprietary API) at all, given the data-sharing constraint, or only as a
  benchmark on synthetic data.
- Which strata are authority strata. This plan takes today's set (section 3); adding one means a
  deterministic definition from Psi, a static check and a Lean update, never a learned output.
- Whether the camera's model reading may count as a witness at all (today it may, as one).
- Consent and recruitment for the real clips.

## 10. Risks

- The labelling function is a canonicalizer too. If it is wrong, the engine learns the error. It is
  deterministic, reviewed and tested, and the end-to-end gate measures what it costs.
- Sim-to-real: synthetic success says little about real homes until section 5's real clips.
- Ordered levels for continuous quantities (how severe, how long, how far) need fixed cut points;
  where they are set is a policy choice, recorded in the scene, not learned.
- Unknowns about Jev: its internals, an on-premises option, its behaviour on state descriptions
  derived from audio and video.
