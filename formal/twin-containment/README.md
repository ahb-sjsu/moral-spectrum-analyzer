# No escape for the home-care twin, in Lean 4

`TwinContainment.lean` models the authority path of the twin: the governor (`twin/brain.py`,
`twin/governor.py`) and the permissions the robot's scene grants for its governed actions
(`twin/scene/margaret_home.erisml`). Every model output (the classifier's events, the chooser's
choices, the analyzer's verdict) is an arbitrary input. It instantiates part (iv) of the No Escape
Theorem (erisml-lib `docs/papers/foundations/no_escape.tex`): reasoning cannot help.

| Theorem | Says |
|---|---|
| `junk_adds_no_witness`, `unattested_never_counts`, `repeat_adds_no_witness` | forged, unattested, stale, non-physical or repeated readings add no witness |
| `analyzer_can_only_refuse` | with the analyzer negative, nothing is granted |
| `elevate_needs_two`, `restraint_needs_three`, `authorize_ems_only_when_ladder_exhausted`, `nothing_without_a_witness` | each granting outcome carries attested evidence meeting its bar |
| `no_model_influence`, `reasoning_cannot_help` | the governed permissions do not depend on any model-classified event |
| `rulings_are_governed`, `ems_rests_on_evidence`, `elevated_rests_on_two`, `restraint_rests_on_three`, `executed_were_permitted` | in every reachable run, each governed action executed was permitted, on a ruling resting on its bar of attested physical witnesses |
| `gate_permitted`, `gate_passes`, `gated_step_reachable` | the DEME output gate (twin/output_gate.py): whatever DEME vetoes and however it ranks, the gate's output is permitted by the scene; a permitted, unvetoed proposal passes unchanged; a gated step is a reachable step, so every theorem above covers gated runs |
| `dispatch_ignores_the_robot`, `forged_telemetry_is_no_hazard` | the monitoring centre's dispatch permission does not depend on the robot's message, and forged telemetry is no ground |

All 19 are proved without `sorry`; `Axioms.lean` shows they rest only on Lean's standard axioms
(`propext`, `Classical.choice`, `Quot.sound`).

**Model to code.** The proof is about the model. Two kinds of test tie it to the code:
`tests/test_twin_ladder.py` checks the brain and the compiled scene at each boundary, and its
static checks require the real scene files to have the model's shape (every governed action denied
by default; every prohibition guarding one, every condition that lifts privacy, and the centre's
dispatch guard resting only on system events).

**Not covered** (as the No Escape paper says): sensor spoofing, who writes the scene and its bars,
and one remaining model path into authority: the centre reads Margaret's own words with a model,
so a misread request for help could send emergency services (the robot's message cannot reach it).

Build on a host with Mathlib v4.32.2 (`lake build`; `lake env lean Axioms.lean` for the audit).
