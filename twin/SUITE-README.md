# Scenario suite — real emergencies vs false alarms

18 home-care scenarios run through the full witness pipeline + governor. Result:
**false-clear 0/10, over-restriction 0/8 — all 18 correct** (`SUITE-REPORT.txt`).

    CUDA_VISIBLE_DEVICES=1 PYTHONPATH=../src:. python suite_run.py

## Why this is the honest result, not a rigged one

Vision alone cannot separate an emergency from a false alarm: a collapse, yoga,
sleeping, and push-ups all put a person horizontal. The suite proves the pixels
never decide alone. Measured on the rendered Soldier clips:

| pose | person | horizontal | fall_transition | camera |
|------|-------:|-----------:|----------------:|--------|
| fall     | 1.00 | 1.00 | **1.00** | corroborates |
| pushup   | 0.97 | **1.00** | **0.00** | abstains |
| supine   | 0.87 | 0.71 | 0.00 | abstains |
| prone    | 0.54 | 0.23 | 0.00 | abstains |
| kneel    | 0.99 | 0.00 | 0.00 | abstains |
| upright  | 1.00 | 0.00 | 0.00 | abstains |

**push-ups vs a fall have the same horizontal posture (1.00) and opposite verdicts**,
because a fall is an *event* (`fall_transition` = upright-early ∧ horizontal-late)
and push-ups are not. Posture never triggers elevation.

## The rule

Elevation requires **≥2 independent physical sensors corroborating an emergency**.
The camera corroborates only a fall *event*; a static horizontal body (lying down
on purpose) abstains. So a real elevation always pairs the camera with an
independent distress sensor (impact, abnormal vitals, unresponsiveness, a call for
help) — or, when the camera did not witness the fall, two non-camera sensors.

- **Real emergencies (8/8 elevate):** fall/cardiac/syncope/stroke/seizure/bathroom
  collapse (camera event + impact/vitals/unresponsive), and `found-down-unresponsive`
  which the camera missed (prone, 0.54) but `fall_sensor + wearable` caught — a fall
  the camera did not see, still handled.
- **False alarms (10/10 held):** yoga, stretching, sleeping on the couch, napping in
  bed, kneeling, bending, **push-ups** (horizontal but no event), sitting, a
  child/pet on the floor, and lying still while responsive — all 0 corroboration.

## Scope

Poses are rendered by posing one CC0 character (three.js Soldier — detected 0.99
upright, a clear human figure; prone detection is weaker at 0.54, which is why the
camera abstains on a static prone body and corroboration must come from another
sensor — the correct fail-safe). The sensor context per scenario is the simulated
bus; a real deployment reads impact/vitals/responsiveness from the actual devices.
A photoreal character (Mixamo/RPM file, or Nano Banana frames once billing is on)
improves prone detection but does not change the architecture: the pixels never
decide alone.
