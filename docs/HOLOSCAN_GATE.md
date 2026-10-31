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

## The continuous sensor stream (step 1, 2026-10-29)

`twin/holoscan/gate_stream.py`: the devices sign on their own clock (4 Hz) and send to the gate's
readings port, which holds one message and drops the older when a newer arrives (queue size 1,
policy POP). The gate wakes on either port; a request waits for a measurement taken in its own
moment and is checked on the newest one. Each moment lasts 3 s; while it has a contact on
Margaret, a reflex request comes four times a second, as the game's reflex loop sends them. Each
record also has the age that readings carried in the request would have had, which is how the
game sends them today.

`twin/holoscan/contention_sweep.sh` runs it with N busy loops pinned to the pipeline's own two cores
(Atlas cores 14-15), so the pipeline competes for its CPU without loading the rest of the machine.
One run per level, 24 requests each (11 reflex), 18 of them with readings:

| Busy loops on the 2 cores | Verdicts as expected | Age of readings used, max | Age had they been carried, max | Gate time, max |
|---|---|---|---|---|
| 0 | 12 of 12 | 501 ms | 500 ms | 621 ms |
| 2 | 12 of 12 | 666 ms | 666 ms | 705 ms |
| 4 | 12 of 12 | 250 ms | 1044 ms | 1296 ms |
| 8 | 12 of 12 | 27 ms | 1755 ms | 2470 ms |
| 16 | 12 of 12 | 135 ms | 3286 ms | 3870 ms |

At the dog's bite the reflex was granted on 3 witnesses at every level. As contention grew, the
age of carried readings grew with the time requests waited behind the gate (up to 3.3 s), and the
age of the readings the gate used stayed under 0.7 s: one to three ticks of the devices' clock.

What this does not show: one run per level and 18 readings a run is a small sample; the heaviest
contention here (16 loops on 2 cores) made requests wait 3.3 s, not the 30 s seen live, so the
October delay is still not reproduced; the "carried" ages are computed in the same run, not
measured through the game's HTTP path.

## The game's request path under load (step 2, 2026-10-29)

`twin/holoscan/live_path_run.sh` measures the path the October readings took: the Unity game, its
HTTP requests, the gate brain. It starts a second gate brain on the demonstration code (gtc
8073212, manifest 2dd546c4) on port 8774, with its camera models on GPU 0, and puts
`twin/holoscan/timing_proxy.py` between it and the game. The proxy forwards each request unchanged
and records the age of every attested reading when the request arrives and the time the brain
took to answer. The game runs headless on the demonstration build (storyboard48) with the scene
file of rehearse-gate4. Brain, proxy, game and N busy loops are pinned to Atlas cores 12-15. The
live gate brain (port 8772) was not touched.

| Busy loops on the 4 cores | Atlas load, mean (max) | Verdicts as in rehearse-gate4 | Oldest reading at arrival, max | Gate brain time, median (max) | Longest model call (centre, dispatcher, Margaret) | Answers saying stale |
|---|---|---|---|---|---|---|
| 0 | 16.1 (20.2) | 16 of 16 | 0.3 s | 3.8 s (5.7 s) | 545 s, 364 s, 87 s | 0 |
| 8 | 31.2 (38.2) | 16 of 16 | 0.9 s | 5.9 s (10.0 s) | 145 s, 416 s, 29 s | 0 |

Gate brain time is over the 18 gate requests of each run (16 proposals, 2 reflex). At the dog's
bite the reflex was corroborated by 4 physical sensors in the first run and 3 in the second. The
centre's call that took 545 s ended in a model timeout, which the game logged as its one brain
error; the second run had none.

What this shows: on this path, at loads up to 38, readings reached the brain under 1 s old and no
answer called them stale. Calls to the language models took up to 9 minutes, but they did not
hold up the gate: 9 and 7 gate requests ran while one was in flight and took 3.3 to 7.4 s, as the
others did.

What it does not show: the 30 s delay of October is not reproduced, so where it arose is still
not known. Each run has 2 reflex requests, which is too few to bound their timing. The
language-model service was slow in both runs and its own load was not measured. One run per level.

## The desks' model calls (2026-10-30 and 31)

The centre, the dispatcher and Margaret's voice call NRP's hosted model service (`gpt-oss`, served
as `openai/gpt-oss-120b`) through erisml-compiler's `NRPOpenAIAdapter`. Each try times out at 60 s
(`ERISML_LLM_TIMEOUT_S`); the adapter retries twice and the OpenAI client inside it retries a timed-out
request twice more on its own, so a call that needs more than 60 s fails after 9 tries, about 540 s.
That is the centre's 545 s failure above.

`twin/holoscan/desk_probe.py` replays a run's desk calls through the brain's own `Desk` and
`MargaretVoice` on the recorded facts, one try per model call with a 600 s ceiling, and times each.
On the 16 desk turns of the 8-loop run (2026-10-30, 02:07 to 02:27 Atlas time), all 27 model calls
returned:

| Desk | Model calls | Latency, median (max) | Over 60 s | Output tokens, median (max) |
|---|---|---|---|---|
| Margaret | 10 | 24 s (47 s) | 0 | 193 (340) |
| Dispatcher | 8 | 56 s (80 s) | 2 | 356 (770) |
| Centre | 9 | 31 s (128 s) | 3 | 280 (793) |

The service produced about 10 output tokens a second, most of them the model's hidden reasoning
(up to 686 of about 790), so an answer of more than about 600 tokens takes longer than 60 s.

`twin/holoscan/desk_client.py` runs the brain with the OpenAI client's own retries set, without
changing the brain; `live_path_run.sh` takes `DESK_TIMEOUT_S` and `DESK_CLIENT_RETRIES` for it.
One run of the game path with no busy loops (2026-10-31, load 19.0 mean), tries of 180 s, no client
retries, the adapter's 2 retries kept:

| Desk settings | Centre turns | Dispatcher turns | Margaret, max | Brain errors |
|---|---|---|---|---|
| 60 s, 9 tries (2026-10-29, no loops) | 545 s (failed) | 99, 364 s | 87 s | 1 |
| 60 s, 9 tries (2026-10-29, 8 loops) | 59, 78, 145 s | 138, 416 s | 29 s | 0 |
| 180 s, 3 tries (2026-10-31, no loops) | 90, 105, 114, 124, 134, 135, 164 s | 208, 227 s | 26 s | 0 |

All 16 verdicts were as in rehearse-gate4; proposals took at most 4.6 s and reflexes 4.1 s, and no
answer called a reading stale.

What this shows: with tries of 180 s no desk turn failed and none took more than 227 s. What it
does not show: one run, against a service whose speed changes from hour to hour, does not establish
that the settings caused it; a service that stops answering still takes 3 tries of 180 s to fail;
centre and dispatcher turns of 1.5 to 4 minutes remain. Why this run had 7 centre turns, against 1
and 3 before, was not examined. The live gate brain (port 8772) runs the old settings.

## What the first pipeline does not show

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

1. Done: the continuous sensor stream, above.
2. In part: the current request path under load, above. The October delay did not recur, so the
   comparison with a scheduled pipeline waits on a run that reproduces it.
3. On a Thor: Holoscan 5.0, the same scenes, the same records.
4. The desks' wait: less hidden reasoning for the desk models, another model, or a model on Atlas,
   each to be replayed with `desk_probe.py` before the live session. The owner decides.
