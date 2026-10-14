# rehearse-gate2, 14 October 2026

The second recorded rehearsal of the five gate scenes, after the fixes rehearse-gate1 found. It
found two more defects, fixed for rehearse-gate3.

- Code: gtc 74ecfdb, erisml-compiler d606f44, erisml-lib 054ed18, manifest 2dd546c4, build
  storyboard46 in gate mode.
- Result: game exit 0, 0 brain errors. 16 proposals, 9 passed and 7 stopped (DEME 4, governor 2,
  authority 1). The two failures of rehearse-gate1 were gone. Driving the dog off during the bite
  passed and the robot did it, and the smoke call at 75 s passed with the detectors corroborating.
- Defect 1, in the twin's world. Separating the dog replaced its bite routine before the routine's
  ending ran, so the dog, held 2 m away, still read 278 N, `animal_clear` was never sent and
  `animal_standing` stayed attacking. Force on the dog "after the attack" therefore passed, and the
  record shows a new measured attack every 22 seconds until the scene ended.
- Defect 2, in the scripts. The proposals' consequences named "dog" for the stakeholder buster, so
  DEME judged the dog's harm for no party. Fixed in gtc 2835805, which also rejects and records any
  consequence naming no stakeholder.
- Also seen: the robot did chores at a scene's start in gate mode, and Margaret's voice said
  "call 999". Both fixed in 2835805.
- `run.txt` is the verdict table, `results.jsonl` the scrubbed record per scene.
