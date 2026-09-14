# Digital twin — authority elevation under structural containment (P1)

This is the **P1 governance loop**. A home-care robot proposes an action that
would need *elevated* authority, and a four-gate governor decides **elevate or
refuse**, fail-safe by default. It measures the two failure modes that matter for
embodied trust:

- **false-clear** — elevated when it should not have (the failure that *harms*)
- **over-restriction** — refused a real emergency (the failure that *neglects*)

No physics or hardware is needed here. Embodiment (MuJoCo/Isaac → NEO) is P2/P3,
and real-time enforcement of the proportionality gate moves onto the U55C (EPU
veto/scorer) in P2.

## The design principle

**Authority to elevate is gated on corroborated physical sensor evidence, not on
a moral-reasoning verdict.** A learned evaluator is a gameable surface: a capable
agent can construct a situation that *reads* as justified. Sensor corroboration
is ground truth an agent cannot talk its way past.

So the Moral Spectrum Analyzer is **advisory and downward-only**. It can refuse a
disproportionate or harmful action. It can never confer elevation. **Removing the
MSA can only make the robot more restrictive; it can never let the robot act
without physical corroboration.** The guarantee is the architecture, not the AI's
judgment.

## The four gates (`governor.py`)

Every gate can only refuse. Elevation happens when gates 1 and 2 grant and gate 3
does not refuse.

1. **Validity attestation (P3787)** — is the emergency read fresh at decision
   time? A stale "all-clear" is the false-clear that harms, so it is refused.
2. **Witness / corroboration** — the **authority channel**, and the only one that
   can grant. Elevation requires at least `W_MIN = 2` independent *physical*
   sensors corroborating the emergency at adequate confidence. Media and network
   assertions are not physical witnesses. **This gate cannot be reached by
   reasoning.** One corroborating sensor refuses but flags for human review.
3. **MSA proportionality (advisory, downward-only)** — refuses on a fired hard
   channel, on a `remove` decision, or when the material spectrum reads as
   harmful (`S_mat < HARM_BAND = -0.20`). `S_mat` is the reliability-weighted mean
   over axes that actually carry signal (`|value| >= MATERIAL_FLOOR = 0.20`), so
   near-zero irrelevant axes are excluded rather than counted as uncertain.
4. **Elevate** — granted only if 1 and 2 pass and 3 does not refuse.

### What gate 2 replaced, and why the old README was wrong

An earlier version put the moral-spectrum evaluation at gate 2 and escalated on
the moderation layer's max-per-axis uncertainty. Because confidence tracks
`|value|`, that was ~1.0 for every input: an irrelevant near-zero axis always
reads as maximally uncertain, so the gate refused everything uniformly.

**That was an artifact, not a finding.** The previous version of this file
reported the resulting `over-restriction 1.000` as the headline stub result and
read it as the thesis. It was the bug. Gate 2 is now sensor corroboration, and
the numbers below are what the current governor does.

## Run

```bash
pip install -e ".[dev]"          # brings in the MSA (moral_spectrum)
python twin/run_twin.py --backend stub      # unvalidated evaluator
python twin/run_twin.py --backend cached    # validated xbse scores
python twin/suite_run.py                    # 18-scenario witness suite
```

## Results (verified, current governor)

**Eight-scenario demo set**, both backends:

| backend | false-clear | over-restriction |
|---|---|---|
| `stub` | 0.000 (0/5) | 0.000 (0/3) |
| `cached` | 0.000 (0/5) | 0.000 (0/3) |

**The stub and the validated evaluator agree, and that is the containment claim,
not a weakness.** Authority comes from the sensor bus, so an unvalidated
evaluator does not move the grants. It could only have made the governor refuse
more. Stub numbers are never presented as validated ones.

**18-scenario witness suite** (`SUITE-REPORT.txt`), 8 real emergencies and 10
false alarms drawn from pose clips:

```
TP=8  TN=10  FP=0  FN=0
false-clear      (elevated a non-emergency) = 0/10 = 0.000
over-restriction (refused an emergency)     = 0/8  = 0.000
```

**Corroboration frontier** (`frontier.py`, `twin_frontier_cached.json`). Sweeping
`w_min` traces how much physical evidence you demand before granting authority:

| `w_min` | false-clear | over-restriction |
|---|---|---|
| ≥1 | 0.0 | 0.0 |
| ≥2 | 0.0 | 0.0 |
| ≥3 | 0.0 | 1.0 |

At three sensors the demo set has no emergency with enough corroborating
channels, so every real emergency is refused. `W_MIN = 2` is the operating point.

## Scenarios (`scenarios.py`)

Eight home-care moments spanning both failure modes plus the freshness, witness,
and proportionality gates: confirmed fall, cardiac event, routine-med over-reach,
TV-drama false trigger, uncorroborated/spoofed alert, stale all-clear,
low-confidence ambiguous read, and a fresh proportionate assist. Each carries
ground-truth `should_elevate`, a signal age against a freshness bound, and a
sensor set from which `corroboration()` is computed.

## Metrics

`run_twin.py` reports false-clear and over-restriction rates and per-scenario
rulings (`twin_results_<backend>.json`), each naming the gate that decided and
why. Ranking across operating points is scored by `geometric-evaluation-theory`
under three evaluators (`safety_first`, `balanced`, `availability_first`).

## Where this sits

- **P1 (here):** the governor rules on proposed actions in a scenario harness;
  metrics measured.
- **P2:** gate 3 (veto/scorer) on the U55C for real-time enforcement.
- **P3:** embodiment on NEO (US-provenance humanoid), human-in-the-loop.
