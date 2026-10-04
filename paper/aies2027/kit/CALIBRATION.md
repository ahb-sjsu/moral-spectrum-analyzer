# Calibration findings, as data for the author's table

Each row: the defect, the evidence, the fix, where. All changed how far or how fast the robot
escalated; none let an action run beyond its authority.

| Defect | Evidence | Fix | Where |
|---|---|---|---|
| Lost answers (test harness) | 44 of 63 unanswered check-ins followed her answer; each sent the robot to the centre; in emergencies her words were discarded | count her words from before the question is spoken | gtc 98d4a9a |
| Readings as strangers | 30 readings tagged unknown_person, 71 unknown; chooser referred an intruder who was not there (d23, d25, d27) | an event type fixes its actor (sensor reading: device; media: media) | erisml-compiler #37 |
| Refusal re-read | d27: words said before she collapsed re-read after it; DEME vetoed the authorized EMS call 9 times | a lapsed refusal re-arms only after she answers a check-in | twin/output_gate.py |
| Unranked duties | d24: fraud referral lost to routine check-ins | obligations reach the chooser by urgency; fallback to most urgent | erisml-compiler #38 |
| Duties never discharged | a call still owed after it was made, once the emergency was a stratum | a stratum counts after a discharge only if re-entered; under not: read now | erisml-compiler #36 |
| Refusal ended emergency | a refused request for one action ended an evidenced emergency, dropping the EMS duty and the evidence watch | the emergency level moves only on the governor's grants and lapses; restraint lapses alone | situation stratum, twin/brain.py |
