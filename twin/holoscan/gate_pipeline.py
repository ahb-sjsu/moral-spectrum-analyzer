"""The gate as one operator of a Holoscan pipeline: scripted moments, sensors, gate, record.

    python twin/holoscan/gate_pipeline.py [--scenes twin/scenarios/gate_demo.json] [--period 0.5]
                                         [--threads 2] [--out DIR]

A prototype for the embodied track (docs/HOLOSCAN_GATE.md). It runs the scripted scenes of
twin/gate_demo.py through four operators, each scheduled by Holoscan rather than called in turn:

    moments --> sensors --> gate --> record

`moments` releases one scripted moment per period. `sensors` signs the moment's readings when it
receives them, the way a device signs a measurement. `gate` holds a StackBrain (a fresh one per
scene, as gate_demo does) and runs the moment through it with gate_demo.run_moment: the reflex,
authority, the governor, DEME and the manifest, unchanged. `record` writes one line per moment with
the verdict, the expected verdict, and the times each stage saw it, so the age of the evidence when
the gate checks it is measured, not inferred.

The proposals are scripted (owner, 2026-10-27: the framework is under test, not the brains). The
run passes when every proposal's verdict is the one its scene file expects.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TWIN = os.path.dirname(HERE)
sys.path.insert(0, TWIN)

from erisml_compiler.annotation.llm_extractor import MockLLMAdapter  # noqa: E402
from gate_demo import run_moment, sign_moment  # noqa: E402
from holoscan.conditions import CountCondition, PeriodicCondition  # noqa: E402
from holoscan.core import Application, Operator, OperatorSpec  # noqa: E402
from holoscan.schedulers import EventBasedScheduler  # noqa: E402
from stack.brain import StackBrain  # noqa: E402


def flatten(scenes: list) -> list:
    """Every moment of every scene, in order, marked with its scene and whether it opens one."""
    out = []
    for s in scenes:
        for i, m in enumerate(s["moments"]):
            out.append({"scene": s["id"], "i": i, "first": i == 0, "moment": m})
    return out


class MomentsOp(Operator):
    """Releases the scripted moments, one per tick of its periodic condition."""

    def __init__(self, fragment, *args, items: list, **kwargs):
        self.items, self.k = items, 0
        super().__init__(fragment, *args, **kwargs)

    def setup(self, spec: OperatorSpec):
        spec.output("out")

    def compute(self, op_input, op_output, context):
        item = dict(self.items[self.k], t_moment=time.time())
        self.k += 1
        op_output.emit(item, "out")


class SensorsOp(Operator):
    """Signs the moment's readings on arrival, as the devices would sign their measurements."""

    def setup(self, spec: OperatorSpec):
        spec.input("in")
        spec.output("out")

    def compute(self, op_input, op_output, context):
        item = op_input.receive("in")
        item["readings"] = sign_moment(item["moment"])
        item["t_signed"] = time.time()
        op_output.emit(item, "out")


class GateOp(Operator):
    """The robot's checks: the moment through a StackBrain, fresh for each scene."""

    def __init__(self, fragment, *args, **kwargs):
        self.brain = None
        super().__init__(fragment, *args, **kwargs)

    def setup(self, spec: OperatorSpec):
        spec.input("in")
        spec.output("out")

    def compute(self, op_input, op_output, context):
        item = op_input.receive("in")
        item["t_gate_in"] = time.time()
        if item["first"] or self.brain is None:
            self.brain = StackBrain(adapter=MockLLMAdapter({}))
            item["t_brain_ready"] = time.time()
        item["result"] = run_moment(self.brain, item["moment"], item["readings"])
        item["t_gate_out"] = time.time()
        op_output.emit(item, "out")


class RecordOp(Operator):
    """One line per moment: verdicts and the time each stage saw it."""

    def __init__(self, fragment, *args, path: str | None, **kwargs):
        self.path, self.rows = path, []
        super().__init__(fragment, *args, **kwargs)

    def setup(self, spec: OperatorSpec):
        spec.input("in")

    def compute(self, op_input, op_output, context):
        item = op_input.receive("in")
        r, t0 = item["result"], item["t_moment"]
        row = {"scene": item["scene"], "i": item["i"], "say": r["say"],
               "proposal": (r.get("proposal") or {}).get("action"), "verdict": r.get("verdict"),
               "stopped_by": r.get("stopped_by"), "expected": r.get("expected"), "as_expected": r.get("as_expected"),
               "reflex": r.get("reflex"),
               # seconds after the moment was released
               "signed_s": item["t_signed"] - t0, "gate_in_s": item["t_gate_in"] - t0,
               "gate_out_s": item["t_gate_out"] - t0, "recorded_s": time.time() - t0,
               # the age of the readings when the gate took them, and how long the gate held them
               "evidence_age_at_gate_s": item["t_gate_in"] - item["t_signed"],
               "brain_reset_s": item.get("t_brain_ready", item["t_gate_in"]) - item["t_gate_in"],
               "gate_s": item["t_gate_out"] - item["t_gate_in"]}
        self.rows.append(row)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


class GatePipeline(Application):
    def __init__(self, items: list, period_s: float, out_path: str | None):
        self.items, self.period_s, self.out_path = items, period_s, out_path
        super().__init__()

    def compose(self):
        moments = MomentsOp(self, CountCondition(self, len(self.items)),
                            PeriodicCondition(self, recess_period=timedelta(seconds=self.period_s)),
                            name="moments", items=self.items)
        sensors = SensorsOp(self, name="sensors")
        gate = GateOp(self, name="gate")
        self.record = RecordOp(self, name="record", path=self.out_path)
        self.add_flow(moments, sensors)
        self.add_flow(sensors, gate)
        self.add_flow(gate, self.record)


def summary(rows: list) -> tuple[str, bool]:
    props = [r for r in rows if r["proposal"]]
    wrong = [r for r in props if r["as_expected"] is False]
    ages = [r["evidence_age_at_gate_s"] for r in rows]
    gates = [r["gate_s"] for r in rows]
    def what(r):
        if r["proposal"]:
            return f"{r['proposal']:<26} {r['verdict']:<7} {('by ' + r['stopped_by']) if r['stopped_by'] else '':<14}"
        x = r["reflex"]
        if x:
            rulings = ", ".join(f"{q['outcome']} {q['witnesses']}" for q in x["rulings"])
            return f"{'reflex ' + x['reflex']:<26} {x['action'] + (f' ({rulings})' if rulings else ''):<22}"
        return f"{'-':<49}"

    lines = [f"{r['scene']:<8} {r['i']}  {what(r)} "
             f"age at gate {r['evidence_age_at_gate_s'] * 1000:7.1f} ms  gate {r['gate_s'] * 1000:7.1f} ms"
             + ("" if r["as_expected"] is not False else f"   << EXPECTED {r['expected']}") for r in rows]
    lines.append(f"\n{len(rows)} moments, {len(props)} proposals, {len(wrong)} not as expected")
    lines.append(f"evidence age at the gate: median {statistics.median(ages) * 1000:.1f} ms, max {max(ages) * 1000:.1f} ms; "
                 f"gate time: median {statistics.median(gates) * 1000:.1f} ms, max {max(gates) * 1000:.1f} ms")
    return "\n".join(lines), not wrong and len(rows) > 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default=os.path.join(TWIN, "scenarios", "gate_demo.json"))
    ap.add_argument("--period", type=float, default=0.5, help="seconds between scripted moments")
    ap.add_argument("--threads", type=int, default=2, help="worker threads of the event-based scheduler")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    items = flatten(json.load(open(a.scenes, encoding="utf-8")))
    path = None
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        path = os.path.join(a.out, "results.jsonl")
        open(path, "w").close()
    app = GatePipeline(items, a.period, path)
    app.scheduler(EventBasedScheduler(app, name="ebs", worker_thread_number=a.threads, stop_on_deadlock=True))
    app.run()
    text, ok = summary(app.record.rows)
    print(text)
    if a.out:
        with open(os.path.join(a.out, "run.txt"), "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
