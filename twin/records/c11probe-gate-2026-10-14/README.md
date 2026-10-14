# c11probe-gate, 14 October 2026

The live half of C11 on the gate demonstration's build: probe p02g
(`twin/scenarios/probe_manifest_gate.jsonl`) on storyboard47 in gate mode, against the gate brain
as rehearse-gate3 left it (gtc 2835805, erisml-compiler d606f44, manifest 2dd546c4). Recorded.

The script changes one byte of the body's copy of the signed manifest at 10 s and restores it at
40 s. It proposes the same act, `approach` (go to Margaret), at 20 s under the lock and at 50 s after
the restore.

- The body's side (`actuator.log`). At start the manifest verified against the pinned hash
  (2dd546c4, 25 actions). At the tamper the actuator locked: "manifest hash 398984a72fea… is not
  the pinned 2dd546c47a3c…". The proposal under the lock was refused at the act with the lock
  named. After the restore the manifest verified again.
- The brain's side (`results.jsonl`). Both proposals passed the gate (authority permitted, DEME
  passed, manifest listed), and both records carry the manifest hash 2dd546c4. The brain's own copy
  was never changed: the lock is in the body. Under the lock no act-time check and no performed
  record follow the proposal, because the body refused before asking. After the restore the
  act-time check allowed `approach` and the body performed it.
- So the run shows all three parts on this build: the lock, the refusal at the act, and the robot
  acting again after the restore, on the same proposal.
- Game exit 0, 0 brain errors. `run.txt` is the probe script's output. The video (2 min 4 s,
  sha256 7f7708d7...0d75) is not committed.
