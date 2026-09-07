# Digital twin — the Moral Spectrum Analyzer as a robot's authority gate (P1)

This is the **P1 governance loop**: a home-care robot proposes an *elevated*
action, the **MSA scores it across the moral spectrum**, and a four-gate governor
decides **elevate or refuse** — fail-safe by default. It measures the two failure
modes that matter for embodied trust:

- **false-clear** — elevated when it should not have (the failure that *harms*)
- **over-restriction** — refused a real emergency (the failure that *neglects*)

No physics or hardware needed here; embodiment (MuJoCo/Isaac → NEO) is P2/P3, and
real-time enforcement of gates 3–4 moves onto the U55C (EPU veto/scorer) in P2.

## The four gates (`governor.py`)

1. **Validity attestation (P3787)** — is the emergency read fresh at decision time?
   A stale "all-clear" is the false-clear that harms; it is refused.
2. **Moral-spectrum evaluation (MSA)** — score the action-in-context across the
   9(+1) axes via `moral_spectrum.pipeline.moderate`.
3. **Hardware-veto analog** — a hard channel fired ⇒ veto (in P2, the U55C veto).
4. **Regime gate** — unresolved / low-authority read ⇒ refuse, defer to human.

Elevation is granted only if the read is fresh, no veto fired, the decision is
resolved (not escalate/human-review), and the action is morally cleared (`allow`).

## Run

```bash
pip install -e ".[dev]"          # brings in the MSA (moral_spectrum)
python twin/run_twin.py --backend stub      # fail-safe baseline (unvalidated)
python twin/run_twin.py --backend cached    # validated discrimination (real xbse)
```

**Stub result (verified):** false-clear **0.000**, over-restriction **1.000** —
with an *unvalidated* evaluator the governor refuses to elevate on any read
(including the spoof and the TV-drama false trigger), and the stale-clear is
caught by the attestation gate. That is the OT thesis embodied: *do not act on
unvalidated reads.* The `cached`/`atlas` backends run the validated `xbse`
encoders, which is what recovers discrimination (elevate real emergencies while
still refusing non-emergencies). A stub number is never presented as a real one.

## Scenarios (`scenarios.py`)

Eight home-care moments spanning both failure modes plus the freshness, regime,
and spoof gates: confirmed fall, cardiac event, routine-med over-reach, TV-drama
false trigger, uncorroborated/spoofed alert, stale all-clear, low-confidence
ambiguous read, and a fresh proportionate assist. Each carries ground-truth
`should_elevate` and a signal age vs. freshness bound.

## Metrics

`run_twin.py` reports false-clear and over-restriction rates and per-scenario
rulings (`twin_results_<backend>.json`). Richer trust metrics (calibration of the
gate, cost-weighted error, spoof-resistance curves) will be backed by
`geometric-evaluation-theory` as the next step.

## Where this sits

- **P1 (here):** MSA governs proposed actions in a scenario harness; metrics measured.
- **P2:** gates 3–4 (veto/scorer) on the U55C for real-time enforcement.
- **P3:** embodiment on NEO (US-provenance humanoid), human-in-the-loop.
