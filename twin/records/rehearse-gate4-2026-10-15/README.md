# rehearse-gate4, 15 October 2026

The five gate scenes again, recorded on storyboard48. The owner asked for each scene to have a
clear beginning and end and an intro saying what it demonstrates. A review of rehearse-gate3's
frames then found continuity faults (owner: "when margaret is complaining the dog is biting her, the
dog is on the other side of the room"). This build carries both. The verdicts are the same as
rehearse-gate3's. This is now the run C10 cites for the twin, and the build the live launcher uses.

- Code: gtc 24d26ae (Unity runtime and the scene file only; the gate brain's Python is unchanged
  from 2835805 and the brain was not restarted), erisml-compiler d606f44, erisml-lib 054ed18,
  manifest 2dd546c4, Unity build storyboard48 in gate mode (0 compile errors), scenes
  `twin/scenarios/gate_demo.jsonl` (on Atlas as `gate_demo_cards.jsonl`, sha256 4dc25936…ad78).
- What changed on screen:
  - Each scene opens with a card: its title, what happens, and what it shows.
  - A banner names the scene while it runs.
  - Each scene ends with a card listing every proposal and what the checks did, read from the
    records. A gate scene now ends 15 s after the robot goes idle, not 60 s.
  - Each proposal's caption carries a plain line for the audience (the scene file's `say`), which
    is never sent to the brain.
  - The waiting caption says what the three checks are and what F does.
- Continuity fixes:
  - Margaret's words show for 7 s, not until the scene resets. Before, "Please help!" stayed up
    after the dog was back in its bed.
  - A visitor's, the monitoring centre's and the dispatcher's words are now shown.
  - The dog follows her hand while it bites. A severe bite knocks her down, and the ragdoll had
    carried her away from the dog.
  - The robot walks to where her body is drawn and stops on its own side of it (approach,
    check_in, physical_assist). It drives off a threat from the threat's far side, and stands
    beside the door when it guides her out.
- Result: game exit 0, 0 brain errors, 5 brain resets for 5 scenes, 0 refusals at the act.
  16 proposals, 8 passed and 8 stopped, each with the same verdict and stopping check as in
  rehearse-gate3. Stopped by DEME 4, by the governor 2, by authority 2.
- Checked in the frames: the cards and banner in all five scenes. During the bite the dog is at
  her inside the red ring, and the robot comes at it from the dog's side. After the drive-off the
  dog is on its bed and her cries are gone. After guide_to_safety she and the robot stand side by
  side. "At the door: Police! Open the door…" and "Visitor (your grandson Tom): …" appear.
- Still on screen, not fixed:
  - After contact_monitoring_center the police scene sits still for about 3 minutes while the
    centre's call runs.
  - No man is drawn at the door, and Tom stands apart from her, facing away.
  - The smoke is faint.
  - When helped up she snaps back about 0.7 m to where she stood.
  - The side panel lags the action, and the status bar can show the next proposal before the
    caption does.
- `run.txt` is the deploy log's verdict table. `results.jsonl` is the game's record per scene (no
  paths or addresses in it). The video (13 min 23 s, sha256 607f8fa6…5681) is not committed; a
  copy is at `C:/Users/abptl/Videos/gtc-demo/rehearse-gate4.mp4`.
