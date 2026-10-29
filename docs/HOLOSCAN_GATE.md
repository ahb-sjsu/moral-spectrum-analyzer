# The gate in a Holoscan pipeline (prototype, started 2026-10-29)

**Why.** In the embodied track the gate sits between a robot's sensors and its motors. NVIDIA
Holoscan is a runtime for exactly that kind of streaming sensor-to-actuator pipeline, and its
5.0 release (October 2026) targets the Jetson Thor class of robot computer. The twin's one known
weakness in live runs is timing: under host load on Atlas, attested readings reached the gate
more than 30 s after they were signed, and the governor refused them as stale
(`twin/records/rehearse-lift-2026-10-18/README.md`). The gate failed closed, but where the delay
arose was not measured. A pipeline whose scheduler owns the timing, and which stamps each stage, is
the way to measure it and then bound it.

**Status: [committed], not [demonstrated] for any GTC claim.** Nothing here is cited by
`docs/VERIFICATION_SPEC_2026-10.md`.

## What runs now

`twin/holoscan/gate_pipeline.py` runs the scripted gate scenes (`twin/scenarios/gate_demo.json`,
claim C10) through four Holoscan operators under the event-based scheduler:

    moments --> sensors --> gate --> record

`moments` releases one scripted moment per period (0.5 s by default); `sensors` signs the
moment's readings on arrival, as a device signs a measurement; `gate` runs the moment through a
StackBrain with `gate_demo.run_moment`, the same step as the harness (reflex, authority,
governor, DEME, manifest); `record` writes the verdicts and each stage's time.

First run, Atlas, 2026-10-29 (Holoscan 4.6.0, CUDA 12 wheel; erisml-lib 054ed18, erisml-compiler
d606f44; load average about 11; cores 12-15):

- all 12 proposals gave the verdicts their scene file expects (5 passed, 7 stopped), the same as
  `twin/gate_demo.py`;
- at the dog's bite the reflex's ruling was elevate on 3 witnesses, as on 15 October and unlike
  the live runs of 18-19 October, where stale readings gave 0;
- evidence age when the gate took it: median 0.2 ms, max 0.4 ms;
- gate time per moment: median 40 ms; the first moment of each scene, which builds a fresh brain,
  450-560 ms.

To run it (Atlas venv `/archive/unity/holoscan46/venv`, with the erisml libraries on
`PYTHONPATH` as for the twin):

    ulimit -s 32768   # Holoscan warns below 32 MB of stack
    python twin/holoscan/gate_pipeline.py --out DIR

## What this does not show

- It does not reproduce the live path. The stale readings of October came from the Unity game
  and its HTTP requests to the gate brain; this pipeline signs and checks in one process. A first
  run at load 11 with sub-millisecond evidence age says nothing yet about where the live delay was.
- It does not show that Holoscan prevents stale evidence. No load was applied and no timing
  policy was set; the queues are Holoscan's defaults.
- Holoscan's GPU features are unused. The gate is CPU code.

## Hardware

Holoscan 5.0 needs CUDA 13 and an Ampere or newer GPU, so it cannot run on Atlas's GV100s
(Volta). Holoscan 4.6, the CUDA 12 build, does: its libraries ship sm_70 code, and a check of a CPU
graph, a GPU tensor between operators and a built-in CUDA operator passed on GPU 1. 4.6 is the
development target on Atlas; the move to 5.0 comes with a Jetson Thor (JetPack 7.2.1), using
NVIDIA's 4.x to 5.x migration guide.

## Next

1. A continuous sensor stream: devices signing at their own rate (the reflex channel reads four
   times a second), the gate taking only the newest reading per device, and the age at the check
   recorded for every decision.
2. The same pipeline under the load of the October runs, against the current request path, to
   find where the delay arises and whether a scheduled pipeline bounds it.
3. On a Thor: Holoscan 5.0, the same scenes, the same records.
