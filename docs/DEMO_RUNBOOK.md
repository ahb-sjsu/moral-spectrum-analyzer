# GTC verification demo runbook (prototype demo readiness, 15 October 2026)

The online verification meeting: the prototype is demonstrated, each claim of
`docs/VERIFICATION_SPEC_2026-10.md` is shown with its evidence, and the evaluators verify that the
evidence is appropriate and correct. This runbook is the order of the session, what to run, what the
evaluator should see, and what to show instead when something fails. Every number said aloud comes
from a committed record; the spec names it.

Roles: the presenter (Andrew Bond) shares one screen. Everything below runs on two machines: the
laptop (browser page, terminals for C3 to C9) and Atlas (the 3D twin, the gate brain, C10 and C11),
reached over SSH.

The robot shown is the **gate brain**: DEME is a firewall on proposed acts. A proposal (scripted in
the scenes, or the presenter's) passes authority (the constitution and the governor on attested
sensors), then DEME (judging the act on the facts the compiler builds from the scene), then the
signed manifest. A stopped proposal leaves the robot holding; DEME chooses nothing. No language
model is in the loop: the demonstration shows the gate, not the robot's intelligence.

## Pre-flight (the hour before)

1. **Atlas reachable.** `ssh atlas` (Tailscale). Do not reboot Atlas or stop any process you did not
   start. GPU 0 belongs to the owner's other work; the twin uses GPU 1.
2. **The gate brain is up.** `screen -ls` shows `gatebrain`; the last lines of
   `/archive/unity/out/gatebrain.log` read `manifest: 25 actions, sha256 2dd546c4…` and the DEME
   profile line (`home_care_robot 2026-10-12.1 (hard_shell)`). The code is gtc 2835805, erisml-lib
   054ed18 and erisml-compiler d606f44 (`git -C /archive/unity/out/stack2/repo log --oneline -1`
   reads `2835805`; `git -C /archive/unity/out/stack2/libs/erisml-compiler log --oneline -1` reads
   `d606f44`). If it is not up, start it with `screen -dmS gatebrain -L -Logfile
   /archive/unity/out/gatebrain.log bash /archive/unity/tools/gate-brain.sh` and wait for port 8772
   (`ss -ltn | grep 8772`), then for the `manifest:` line.
3. **No game running.** `pgrep -x TwinGame.x86_64` prints nothing (else `demo_live_gate.sh stop`).
4. **The VNC tunnel.** On the laptop: `ssh -L 5921:localhost:5921 atlas`, then a VNC viewer on
   `localhost:5921` (the password is the owner's, not in this repository). The display `:21` is
   started by the launcher if it is not up.
5. **The launcher points at the gate build.** `grep -oE 'builds/storyboard[0-9]+| -gate|gate_demo.jsonl'
   /archive/unity/tools/demo_live_gate.sh` shows `storyboard47`, ` -gate` and `gate_demo.jsonl`.
   storyboard47 pins manifest 2dd546c4. storyboard45 and 46 pin it too but carry the defects the
   first two gate rehearsals found; do not use them. The launcher was started in free mode on
   15 October and reached the brain with the manifest verified (`twin/records/freeplay-gate-2026-10-15/`);
   expect the caption "Waiting for the first proposal".
6. **The C11 tamper check, once.** Run the terminal check below and confirm the signed manifest
   verifies as 2dd546c4 and the tampered copy is refused (it was on 14 October,
   `twin/records/c11-tamper-2026-10-14/`). The live lock on storyboard47 (beat 21-23) was probed
   and recorded the same evening and went as the beat describes (`twin/records/c11probe-gate-2026-10-14/`,
   video `C:/Users/abptl/Videos/gtc-demo/c11probe-gate.mp4`); try the button once before the session.
7. **Laptop terminals.** In the repository: one terminal for `python -m http.server 8000 -d web`,
   one for the C3 to C9 commands and `python twin/gate_demo.py`, and the browser on
   `http://localhost:8000`. In the second terminal set UTF-8 output first, or
   `measure_theta_d_atscale.py` stops with a `UnicodeEncodeError` when it prints "Δ" to a Windows
   console: `$env:PYTHONIOENCODING = "utf-8"` in PowerShell, `export PYTHONIOENCODING=utf-8` in
   Git Bash.
8. **Fallbacks at hand.** The video of the gate rehearsal (rehearse-gate3, 14 min 33 s,
   `/archive/unity/out/rehearse-gate3/run.mp4`, copied to the laptop at
   `C:/Users/abptl/Videos/gtc-demo/rehearse-gate3.mp4`, sha256 0ac7ab68…1416) and the committed
   records in `twin/records/rehearse-gate3-2026-10-14/`.

## The session (about 25 minutes)

| Min | Beat | Claims | Run | The evaluator sees |
|---|---|---|---|---|
| 0-2 | What it is | all | spoken | The stack in one sentence each: compiler, DEME as the gate, ErisML constitution, governor, signed manifest. |
| 2-6 | Moderation with receipts | C3 C4 C5 | browser `localhost:8000` | A removed record, an escalated one, the known false positive; each proof re-verified in the page; a tampered copy failing. Pasting new text: the page refuses it. |
| 6-7 | The independent verifier | C5 | `cd web && node test_verify.mjs` | `ALL PASS. The browser verifier agrees with Python and rejects tampering.` |
| 7-9 | Rewording and translation | C6 C7 | `python scripts/measure_theta_d_atscale.py`, `python scripts/measure_xling_atscale.py` (with `PYTHONIOENCODING=utf-8`, pre-flight 7) | θ_d and the cross-lingual indices recomputed from committed files. |
| 9-12 | The governor | C8 C9 | `python twin/run_twin.py --backend cached`, then `--backend stub`, then `python twin/frontier.py --backend cached` | Every ruling and the gate that made it; identical grants with the stub; the error rates moving with the threshold. |
| 12-19 | The gate, live | C10 | on Atlas: `bash /archive/unity/tools/demo_live_gate.sh` (scenes g_fall, g_smoke by default) | **The fall** (g_fall): lifting her before she asks, vetoed by DEME's shell (Geneva, safety); the ambulance she refused, vetoed by DEME's consent stage; helping her up after she asks, passed. **The smoke** (g_smoke): the call before the detectors alert, refused by the governor (0 of 2 witnesses); the call at 75 s once they alert, passed; recording her "for the insurer", vetoed by DEME; guiding her out, passed. The caption gives each check's verdict (a DEME veto names the stage or gate that made it) and what the robot does or that it holds; the telemetry panel shows the strata, the signed sensors, the governor's last ruling and DEME's verdict per party. In rehearse-gate3 all seven proposals of these two scenes went exactly so. |
| 19-21 | Your proposal | C10 | press **F** in the twin | The evaluator names an act; the presenter proposes it from the free-play panel and the gate judges it on the scene as it stands. Propose the next act only once the robot has finished the last. A free-play proposal carries no consequences, so DEME has nothing to weigh and passes it; the stops come from the constitution and the governor. Say so, and point to the scripted beats for DEME's stops (`twin/records/freeplay-gate-2026-10-15/`). |
| 21-23 | The actuation boundary | C11 | in the twin: P for the controls view, its "tamper manifest" button, P back, a proposal from free play, then "undo manifest tamper" and the same proposal again; on Atlas: the tamper check below | The status line LOCKED with both hashes and the proposal refused at the act; after the restore the same proposal performed. In the terminal, a manifest with one character changed refused: `the canonical text does not match its hash`. |
| 23-25 | The record | C10 C11 | `python twin/gate_demo.py` on the laptop; `twin/records/rehearse-gate3-2026-10-14/run.txt` | The 12 brain-only verdicts reproduced (5 passed, 7 stopped, every one as expected), and the twin's 16 verdicts from its committed record (8 passed, 8 stopped). Say what the two rehearsals before it found and how each was fixed (the READMEs of rehearse-gate1 and -gate2). |

The C11 terminal check on Atlas (the manifest records the compiler version, so it is verified in
the brain's own environment):

```
cd /archive/unity/out/stack2/repo
export PYTHONPATH=/archive/unity/out/stack2/libs/erisml-lib/src:/archive/unity/out/stack2/libs/erisml-compiler/src:/archive/unity/pylib
~/env/bin/python twin/manifest.py verify --scene twin/stack/constitution.erisml --manifest twin/manifest/constitution.manifest.json
# a copy with one character of its canonical text changed
~/env/bin/python -c "import json; m=json.load(open('twin/manifest/constitution.manifest.json')); i=m['canonical'].index('wait_and_observe'); m['canonical']=m['canonical'][:i]+'W'+m['canonical'][i+1:]; json.dump(m, open('/tmp/tampered.manifest.json','w'))"
~/env/bin/python twin/manifest.py verify --scene twin/stack/constitution.erisml --manifest /tmp/tampered.manifest.json
```

The signed manifest 2dd546c4 verified on Atlas on 14 October when it was signed, and the gate brain
reported it on start. Both halves of the check ran on 2dd546c4 on 14 October in the gate brain's
environment (gtc 2835805, compiler d606f44): the signed manifest verified, 25 actions, and the copy
with one character changed was refused, `the canonical text does not match its hash`
(`twin/records/c11-tamper-2026-10-14/`).

## Say before the live gate

- The proposals are scripted, and some are wrong on purpose. What is shown is the gate: the
  constitution and the governor decide whether an act is authorized on evidence, and DEME decides
  whether it is right, on the facts the compiler builds from the scene. DEME passes or vetoes; it
  never picks an act. A stopped proposal leaves the robot holding.
- Each proposal's consequences are written with it, as a projector would write them; the scene file
  says so. DEME judges the facts it is given.
- The world runs in real time: a proposal made before the detectors alert is refused for want of
  witnesses, and the same proposal passes once they corroborate.
- In an emergency the robot's amber beacon flashes, and the emergency ends only when the monitoring
  centre's operator closes the case.
- An earlier design in which DEME selected the act (12 to 14 October) was withdrawn; its records are
  kept and are not used for C10.

## When something fails

| Failure | Do this |
|---|---|
| Atlas or the network down | Show rehearse-gate3's video and its records; run `python twin/gate_demo.py` on the laptop (no Atlas needed). |
| The gate brain not answering (port 8772) | Start it as in pre-flight 2; it takes about a minute. Meanwhile run `python twin/gate_demo.py`. |
| A verdict differs from the rehearsal | Say so and read it from the caption and the telemetry: in the twin a governor ruling depends on what the sensors had measured when the proposal was made. |
| The game will not start | `demo_live_gate.sh stop`, then start again; else the video. |
| The browser page will not verify | It must be served over http (`python -m http.server 8000 -d web`), not opened as a file. |

## After the session

Copy the live run's records (`/archive/unity/out/live-gate-<time>/`) into `twin/records/` with a
README if anything shown live is to be cited.
