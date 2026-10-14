# C11 tamper check on manifest 2dd546c4, 14 October 2026

The terminal half of C11 on the gate brain's manifest, run on the GPU workstation in the gate
brain's own environment (gtc 2835805, erisml-compiler d606f44, erisml-lib 054ed18), since the
manifest records the compiler version it was compiled with.

- The signed manifest `twin/manifest/constitution.manifest.json` verified against
  `twin/stack/constitution.erisml`: 25 actions, sha256 2dd546c4...98fbb, exit 0.
- A copy with one character of its canonical text changed (the first "wait_and_observe" made
  "Wait_and_observe") was refused: "the canonical text does not match its hash", exit 1.
- The commands are those of `docs/DEMO_RUNBOOK.md` (the C11 terminal check). `run.txt` is the
  output, with the repository and temporary paths replaced by `<repo>` and `<tmp>`. The tampered
  copy was deleted after the run.

Not covered here: the live half of C11 on storyboard47 (the body's copy tampered from the controls
view, a proposal refused at the act, the restore). It has not been run on this build.
