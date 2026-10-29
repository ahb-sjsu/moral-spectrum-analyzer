#!/bin/bash
# The stream pipeline under CPU contention confined to its own cores (docs/HOLOSCAN_GATE.md).
#
#   twin/holoscan/contention_sweep.sh OUT_DIR [CORES] [N...]
#
# For each N, N busy loops are pinned to CORES (default 14-15), the cores the pipeline runs on, so
# the pipeline competes for them as the twin competed for Atlas under load, without loading the rest
# of the machine. The busy loops are this script's own children and are stopped after each run.
# Needs PYTHONPATH with the erisml libraries and PY pointing at a Python with Holoscan 4.6.
set -u
OUT=$1; CORES=${2:-14-15}; shift 2 2>/dev/null || shift $#
LEVELS=${*:-0 2 4 8 16}
PY=${PY:-python}
HERE=$(cd "$(dirname "$0")" && pwd)
ulimit -s 32768
mkdir -p "$OUT"
for n in $LEVELS; do
  pids=()
  for _ in $(seq 1 "$n"); do
    taskset -c "$CORES" python3 -c 'while True: pass' &
    pids+=($!)
  done
  sleep 1
  HOLOSCAN_LOG_LEVEL=ERROR taskset -c "$CORES" "$PY" "$HERE/gate_stream.py" --out "$OUT/burn$n" > "$OUT/burn$n.log" 2>&1
  rc=$?
  [ ${#pids[@]} -gt 0 ] && kill "${pids[@]}" && wait "${pids[@]}" 2>/dev/null
  echo "== $n busy loops on $CORES (exit $rc), load $(cut -d' ' -f1 /proc/loadavg)"
  tail -5 "$OUT/burn$n/run.txt" 2>/dev/null || tail -5 "$OUT/burn$n.log"
done
