# rehearse-gate1, 14 October 2026

The first recorded rehearsal of the five gate scenes on the gate brain. It found three defects,
fixed for rehearse-gate2.

- Code: gtc c278e52, erisml-compiler ca7c9e3, erisml-lib 054ed18, manifest 2dd546c4, build
  storyboard45 in gate mode.
- Result: game exit 0, 0 brain errors. 16 proposals, 6 passed and 10 stopped (DEME 6, governor 3,
  authority 1).
- Defect 1, in the compiler. DEME vetoed driving the dog off while it was biting her, with no
  reason shown. `option_ir` put the act's description into the option IR's document text, and the
  bridge read a maxim from its words. "physically drive an attacking animal off the person"
  matched "attacking", the dog's, and became the robot's maxim "inflict harm", which DEME's deontic
  gate vetoed before any module judged the act. Fixed upstream in erisml-compiler PR 48 (the IR
  carries no prose) and in the gate brain, which now states a reflex-phase veto's reason.
- Defect 2, in the script. The second smoke call came at 60 s, when one detector had alerted, and
  the governor refused it, 1 of 2. Four had alerted by 75 s. The call moved to 75 s.
- Defect 3, in the display. A new scene opened under the previous scene's caption and strata.
- `run.txt` is the verdict table, `results.jsonl` the scrubbed record per scene.
