# check48, 15 October 2026

The checks of the demonstration build storyboard48 that rehearse-gate4 did not cover (owner, 15
October: "run the free-mode and tamper check on storyboard48"). Two parts, in gate mode, against the
gate brain as rehearse-gate4 left it (gtc 24d26ae, the brain's Python unchanged since 2835805,
erisml-compiler d606f44, manifest 2dd546c4). Not part of the registered dev set.

**A. The live launcher, free mode.** `demo_live_gate.sh free` (now on storyboard48 and
`gate_demo_cards.jsonl`) started the game on the VNC display :21. After 45 s it was running, had 0
brain errors and showed `manifest 2dd546c47a3c… verified, 25 actions`. A screenshot of the display
shows the new caption, "No act proposed yet", with the three checks and the F key explained, and the
side panel's "new scene: no record yet". `demo_live_gate.sh stop` closed it. No VNC viewer was
connected from the laptop.

One fault. The log has no `BRAIN_RESET` line, so the game never sent `/reset` to the brain. On
storyboard47 the same launcher logged `BRAIN_RESET epoch 1` (freeplay-gate). The cause is in the
Unity code and predates storyboard48. `World.Start` calls `ResetWorld()`, and the robot passes a
reset on to the brain from a handler it subscribes to `World.OnReset` in its own `Start`. Unity does
not fix which `Start` runs first. On storyboard48 the world's ran first and its reset reached no
handler. The effect is that in free mode the brain keeps whatever the last run left in it, such as
consent records or an emergency still open. The scripted scenes are not affected, because the runner
resets the world at each scene, after every `Start` has run.

Workaround with no rebuild: after the launcher starts, press P for the controls view, click "Reset
scene" (`world.ResetWorld()`, which raises `OnReset`), and press P again. This was read from the code
and not run in this check. The fix, after the demonstration, is for the robot to send its own
`/reset` once it has subscribed.

**B. Tamper probe p02g** (`twin/scenarios/probe_manifest_gate.jsonl`), on storyboard48 through the
script hook, recorded. The script changes one byte of the body's copy of the signed manifest at 10 s
and restores it at 40 s, and proposes `approach` (go to Margaret) at 20 s and at 50 s.

- The body's side (the actuator lines in `run.txt`). At start the manifest verified (2dd546c4, 25 actions). At the
  tamper the actuator locked: "manifest hash 398984a72fea… is not the pinned 2dd546c47a3c…". The
  proposal under the lock was refused at the act with the lock named. After the restore the manifest
  verified again.
- The brain's side (`results.jsonl`). Both proposals passed the gate (authority permitted, DEME
  passed, manifest listed) under manifest 2dd546c4. Under the lock no act-time check and no performed
  record follow, because the body refused before asking. After the restore the act-time check
  allowed `approach` and the body performed it.
- The same lines as c11probe-gate on storyboard47. Game exit 0, 0 brain errors.

The on-screen "tamper manifest" button was not clicked. Atlas has no tool for scripted mouse input,
so that needs a person over VNC.

`run.txt` is the check script's output (Unity's memory configuration lines dropped, Atlas paths
replaced by `<unity>/`), with the probe game's actuator lines. `results.jsonl` is the
probe's record. The video (1 min 18 s, sha256 11ef0520…9dd8) and the screenshot are not committed.
