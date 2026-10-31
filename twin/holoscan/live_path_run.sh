#!/bin/bash
# The game's request path under contention: a second gate brain behind the timing proxy
# (docs/HOLOSCAN_GATE.md, step 2).
#
#   twin/holoscan/live_path_run.sh OUT_DIR N_BUSY_LOOPS [CORES]
#
# Starts its own gate brain (gtc 8073212, port 8774, its own logs) and the timing proxy (port
# 8773), runs the game headless on the scene file of the October rehearsals against the proxy, and
# pins all three, with N busy loops, to CORES (default 12-15). Everything it starts it stops. It
# never touches the live gate brain (screen gatebrain, port 8772) and refuses to start while any
# game is running, so it cannot collide with the live demo.
set -u
OUT=$1; N=$2; CORES=${3:-12-15}
U=/archive/unity; L=$U/out/stack2/libs; B=$U/builds/storyboard48
HG=$U/out/holoscan-gate; R=$HG/brain-8073212; HERE=$(cd "$(dirname "$0")" && pwd)
PY=~/env/bin/python
fail() { echo "FAIL: $1"; echo RUN_DONE; exit 1; }
pgrep -x TwinGame.x86_64 >/dev/null && fail "a game is running"
ss -ltn | grep -qE ":877[34] " && fail "port 8773 or 8774 is in use"
[ -d "$OUT" ] && fail "$OUT exists already"
[ "$(git -C $R rev-parse --short=7 HEAD)" = 8073212 ] || fail "the second brain's checkout is not 8073212"
[ "$(tr -d '\r' < $U/tools/gate_demo_cards.jsonl | sha256sum | cut -c1-16)" = 4dc25936a0d41670 ] || fail "scene file is not rehearse-gate4's"
mkdir -p "$OUT/brain/frames"
pids=()
stop_all() { [ ${#pids[@]} -gt 0 ] && kill "${pids[@]}" 2>/dev/null; wait 2>/dev/null; }
trap stop_all EXIT

# the second gate brain, as screen gatebrain runs the first (tools/gate-brain.sh), on 8774. Its
# camera models go on GPU 0: the live brain holds most of GPU 1, and a second copy there ran out of
# memory (owner, 2026-10-29: "use GPU 0 for the second brain"). The game still renders on GPU 1.
( cd $R && export PYTHONPATH=$L/erisml-lib/src:$L/erisml-compiler/src:$U/pylib CUDA_VISIBLE_DEVICES=0 \
    ERISML_LLM_API_KEY="$(cat ~/.llmtoken)" && \
  exec taskset -c "$CORES" $PY -u twin/service.py --stack --port 8774 --log "$OUT/brain/session.jsonl" \
    --frames-dir "$OUT/brain/frames" --live "$OUT/brain/live_cache.jsonl" --scene twin/stack/constitution.erisml \
    --manifest twin/manifest/constitution.manifest.json --onboard-url http://127.0.0.1:8096/v1 \
    --onboard-model gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf ) > "$OUT/brain.log" 2>&1 &
pids+=($!)
for _ in $(seq 1 300); do ss -ltn | grep -q "127.0.0.1:8774 " && break; sleep 1; done
ss -ltn | grep -q "127.0.0.1:8774 " || fail "the second brain did not start (see $OUT/brain.log)"
grep -a "^manifest:" "$OUT/brain.log" | tail -1 | grep -q 2dd546c4 || fail "the second brain is not on manifest 2dd546c4"

taskset -c "$CORES" $PY "$HERE/timing_proxy.py" --listen 8773 --brain http://127.0.0.1:8774 --log "$OUT/proxy.jsonl" > "$OUT/proxy.log" 2>&1 &
pids+=($!)
for _ in $(seq 1 20); do ss -ltn | grep -q "127.0.0.1:8773 " && break; sleep 0.5; done

for _ in $(seq 1 "$N"); do taskset -c "$CORES" python3 -c 'while True: pass' & pids+=($!); done
( while sleep 20; do echo "$(date +%T) $(cut -d' ' -f1 /proc/loadavg)"; done > "$OUT/load.txt" ) &
pids+=($!)
echo "second brain 8073212 on 8774, proxy on 8773, $N busy loops on $CORES, load $(cut -d' ' -f1 /proc/loadavg) at $(date +%T)"

cd $B
timeout 7200 xvfb-run -a -s "-screen 0 1600x900x24" taskset -c "$CORES" $U/tools/record_run.sh "$OUT/run.mp4" \
  ./TwinGame.x86_64 -force-vulkan -force-device-index 1 -screen-width 1600 -screen-height 900 \
  -service http://127.0.0.1:8773 -present -gate -scenarios $U/tools/gate_demo_cards.jsonl \
  -results "$OUT/results.jsonl" -storyboard "$OUT/frames" -shots "$OUT/shots" -logFile "$OUT/game.log"
echo "game_rc=$? brain errors: $(grep -c BRAIN_ERROR "$OUT/game.log")"
stop_all; trap - EXIT

$PY - $U/out/rehearse-gate4/results.jsonl "$OUT/results.jsonl" "$OUT/proxy.jsonl" <<'PYEOF'
import json, sys
def rows(path):
    out = []
    for line in open(path, encoding="utf-8"):
        s = json.loads(line)
        for r in s["records"]:
            rec = r["record"]
            if rec.get("kind") == "proposal" and rec.get("proposal"):
                out.append((s["id"], rec["proposal"]["action"], rec["verdict"], rec.get("stopped_by") or ""))
    return out
a, b = rows(sys.argv[1]), rows(sys.argv[2])
same = sum(i < len(a) and a[i] == y for i, y in enumerate(b))
print(f"{same} of {len(b)} verdicts as in rehearse-gate4")
for line in open(sys.argv[2], encoding="utf-8"):
    s = json.loads(line)
    for r in s["records"]:
        rec = r["record"]
        if rec.get("kind") == "reflex":
            for q in rec.get("rulings") or []:
                print("reflex", s["id"], rec["action"]["action"], "witnesses", q.get("witnesses"), (q.get("reason") or "")[:80])
p = [json.loads(l) for l in open(sys.argv[3], encoding="utf-8")]
for path in sorted({x["path"] for x in p}):
    xs = [x for x in p if x["path"] == path]
    ages = [x["age_at_arrival_s"][1] for x in xs if x["age_at_arrival_s"]]
    br = [x["brain_s"] for x in xs]
    print(f"{path:<12} {len(xs):4d} requests | oldest reading at arrival: max {max(ages):6.1f} s"
          f" (over 30 s: {sum(a > 30 for a in ages)})" if ages else f"{path:<12} {len(xs):4d} requests | no readings",
          f"| brain time max {max(br):6.1f} s | answers saying stale {sum(x['stale_in_answer'] > 0 for x in xs)}")
PYEOF
echo "load: $(awk '{s+=$2; n++; if ($2>m) m=$2} END {printf "mean %.1f max %.1f over %d samples", s/n, m, n}' "$OUT/load.txt")"
echo RUN_DONE
