# check49, 17 October 2026

The check of the fix for the reset race that check48 found (owner, 16 October: "fix the reset race
in the robot code", then "yes, build and check it, then commit"). Not part of the registered dev set.

**The fix** (gtc 70dd556, `World.cs` and `RobotAgent.cs` only). `World.Start` resets the world, and
the robot passes a reset on to the brain from a handler it subscribes in its own `Start`. When the
world's `Start` ran first, the robot missed that reset and the brain kept what the last run left in
it. World now counts its resets. Once subscribed, the robot runs the handler itself if a reset has
already happened. Either start order now gives one reset at start.

Unity build storyboard49 = storyboard48 plus the fix. The script checked every other runtime file
in the Unity project against gtc HEAD before building (line endings ignored). Build exit 0, 0
compile errors. Gate brain as before (gtc 2835805 Python, erisml-compiler d606f44, manifest
2dd546c4), not restarted.

- **A. Free mode, three starts** (under xvfb, 45 s each). Each logged exactly one `BRAIN_RESET`,
  epoch 1, with 0 brain errors and the manifest verified. storyboard48 in the same mode logged none
  (check48).
- **B. Probe p02g** (one scene). Two resets, epoch 1 at start and epoch 2 for the scene. Before the
  fix, rehearsals logged either 5 or 6 resets for 5 scenes from run to run, depending on which
  `Start` ran first, so a run now logs one more reset than it has scenes. The lock, the refusal of
  `approach` at the act, the manifest verified again and `approach` performed, the same lines as
  c11probe-gate and check48. Game exit 0, 0 brain errors.
- **C. The live launcher.** `demo_live_gate.sh` now uses storyboard49 (the previous version is kept
  as `demo_live_gate.sh.storyboard48.bak`). Started in free mode on the VNC display :21, it logged
  `BRAIN_RESET epoch 1` and the manifest verified, and `demo_live_gate.sh stop` closed it.

The probe's video is 33 s, shorter than the run (the two proposals are 41 s apart). The recorder
caught only part of the run. The log and the records cover all of it. The video (sha256
a917a849…183a) is not committed.

`run.txt` is the check script's output with the launcher check appended (Unity's memory
configuration lines dropped, Atlas paths replaced by `<unity>/`). `results.jsonl` is the probe's
record.
