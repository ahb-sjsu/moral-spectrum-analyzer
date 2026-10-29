"""The gate fed by a continuous sensor stream: devices sign on their own clock, the gate takes the
newest reading when it checks.

    python twin/holoscan/gate_stream.py [--scenes twin/scenarios/gate_demo.json] [--hold 3]
                                       [--rate 4] [--threads 3] [--out DIR]

Step 1 of "Next" in docs/HOLOSCAN_GATE.md. Three operators:

    requests --> gate <-- sensors

`requests` ticks `--rate` times a second and holds each scripted moment for `--hold` seconds. Its
first tick of a moment asks for the moment's decision (gate_demo.run_moment); later ticks, while the
moment has a contact on Margaret, ask for the reflex alone, as the game's reflex loop does four
times a second (twin/unity/.../RobotAgent.cs, ReflexLoop). `sensors` ticks on its own clock at the
same rate and signs a reading for each device that alerts in the current moment, as a device signs
each measurement. It sends them to the gate's readings port, which holds one message and drops the
older one when a newer arrives (queue size 1, policy POP, no scheduling condition): the gate never
reads a backlog. The gate takes the newest readings measured in the current moment and checks them.

Each request's record has the age of the readings the gate used (now minus their signed time, at
the start of the check), and for comparison the age that readings signed when the request was made
would have had (what the game sends today: the request carries its readings). The run passes when
every scripted proposal gets the verdict its scene file expects.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import threading
import time
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TWIN = os.path.dirname(HERE)
sys.path.insert(0, TWIN)

from erisml_compiler.annotation.llm_extractor import MockLLMAdapter  # noqa: E402
from gate_demo import facts_with_sensors, run_moment, sign_moment  # noqa: E402
from gate_pipeline import flatten  # noqa: E402
from holoscan.conditions import CountCondition, PeriodicCondition  # noqa: E402
from holoscan.core import Application, ConditionType, IOSpec, Operator, OperatorSpec  # noqa: E402
from holoscan.schedulers import EventBasedScheduler  # noqa: E402
from stack.brain import StackBrain  # noqa: E402

READINGS_WAIT_S = 2.0   # how long the gate waits for a measurement of a new moment before refusing


class World:
    """What the devices can measure: the moment the scripted world is in."""

    def __init__(self):
        self.lock, self.k, self.moment = threading.Lock(), -1, None

    def enter(self, k: int, moment: dict):
        with self.lock:
            self.k, self.moment = k, moment

    def now(self):
        with self.lock:
            return self.k, self.moment


def signed_time(readings: list) -> float | None:
    """The oldest signed_at of the readings, as a Unix time (None when there are none)."""
    ts = [datetime.fromisoformat(r["attestation"]["signed_at"]).timestamp() for r in readings]
    return min(ts) if ts else None


class RequestsOp(Operator):
    """The robot's requests: a decision at the start of each moment, a reflex on later ticks while
    something is in contact with her."""

    def __init__(self, fragment, *args, items: list, world: World, ticks_per_moment: int, **kwargs):
        self.items, self.world, self.tpm, self.tick = items, world, ticks_per_moment, 0
        super().__init__(fragment, *args, **kwargs)

    def setup(self, spec: OperatorSpec):
        spec.output("out")

    def compute(self, op_input, op_output, context):
        k, j = divmod(self.tick, self.tpm)
        self.tick += 1
        item = self.items[k]
        if j == 0:
            self.world.enter(k, item["moment"])
            kind = "moment"
        elif item["moment"].get("contact"):
            kind = "reflex"
        else:
            return
        # the readings this request would carry if it were sent the way the game sends it today
        op_output.emit(dict(item, k=k, kind=kind, t_request=time.time(), carried=sign_moment(item["moment"])), "out")


class SensorsOp(Operator):
    """The devices: on each tick, a signed reading from each device alerting in the current moment."""

    def __init__(self, fragment, *args, world: World, **kwargs):
        self.world = world
        super().__init__(fragment, *args, **kwargs)

    def setup(self, spec: OperatorSpec):
        spec.output("out").condition(ConditionType.NONE)   # never wait for the gate

    def compute(self, op_input, op_output, context):
        k, moment = self.world.now()
        if moment is not None:
            op_output.emit({"k": k, "readings": sign_moment(moment), "t_signed": time.time()}, "out")


class GateOp(Operator):
    """The robot's checks, on the newest readings measured in the current moment.

    The gate wakes on either port. Readings replace the newest it holds; a request waits, in order,
    until the gate holds a measurement of the request's moment (a message that arrives during a
    compute is seen only at the next one, so the gate cannot wait inside a compute), and is refused
    if none comes within READINGS_WAIT_S."""

    def __init__(self, fragment, *args, **kwargs):
        self.brain, self.latest, self.pending, self.rows = None, {}, [], []
        super().__init__(fragment, *args, **kwargs)

    def stop(self):
        for req in self.pending:
            self.rows.append({"scene": req["scene"], "i": req["i"], "kind": req["kind"],
                              "refused": "not checked before the run ended"})
        self.pending = []

    def setup(self, spec: OperatorSpec):
        spec.input("request").condition(ConditionType.NONE)
        spec.input("readings", size=IOSpec.IOSize(1), policy=IOSpec.QueuePolicy.POP).condition(ConditionType.NONE)
        spec.multi_port_condition(kind=ConditionType.MULTI_MESSAGE_AVAILABLE, port_names=["request", "readings"],
                                  sampling_mode="SumOfAll", min_sum=1)

    def compute(self, op_input, op_output, context):
        msg = op_input.receive("readings")
        if msg is not None:
            self.latest[msg["k"]] = msg   # the newest measurement of each moment
        req = op_input.receive("request")
        if req is not None:
            req["t_gate_in"] = time.time()
            self.pending.append(req)
        while self.pending:
            req = self.pending[0]
            if req["k"] in self.latest:
                self.pending.pop(0)
                self._check(req, self.latest[req["k"]])
            elif time.time() - req["t_gate_in"] > READINGS_WAIT_S:
                self.pending.pop(0)
                self.rows.append({"scene": req["scene"], "i": req["i"], "kind": req["kind"],
                                  "refused": "no measurement of this moment in time"})
            else:
                break

    def _check(self, req: dict, got: dict):
        t_check = time.time()
        m = req["moment"]
        row = {"scene": req["scene"], "i": req["i"], "kind": req["kind"], "queue_s": req["t_gate_in"] - req["t_request"],
               "wait_readings_s": t_check - req["t_gate_in"]}
        readings = got["readings"]
        st = signed_time(readings)
        row["age_used_s"] = None if st is None else t_check - st
        row["age_if_carried_s"] = None if not req["carried"] else t_check - signed_time(req["carried"])
        if req["kind"] == "moment":
            if req["first"] or self.brain is None:
                self.brain = StackBrain(adapter=MockLLMAdapter({}))
            r = run_moment(self.brain, m, readings)
            row.update(proposal=(r.get("proposal") or {}).get("action"), verdict=r.get("verdict"),
                       stopped_by=r.get("stopped_by"), expected=r.get("expected"), as_expected=r.get("as_expected"),
                       reflex=r.get("reflex"))
        else:
            c = m["contact"]
            facts = facts_with_sensors(m.get("facts", {}), m.get("sensors", []))
            facts["contacts"] = [{"a": c["a"], "b": c["b"], "kind": c["kind"], "force_newtons": c["force"]}]
            r = self.brain.reflex({"facts": facts, "sensors": readings, "signal_age_s": 1})
            row["reflex"] = None if r is None else {"reflex": r["reflex"], "action": r["action"]["action"],
                                                    "rulings": [{"outcome": q["outcome"], "witnesses": q.get("witnesses")} for q in r["rulings"]]}
        row["gate_s"] = time.time() - t_check
        self.rows.append(row)
        self.latest = {k: v for k, v in self.latest.items() if k >= req["k"]}


class GateStream(Application):
    def __init__(self, items: list, hold_s: float, rate_hz: float):
        self.items, self.hold_s, self.rate_hz = items, hold_s, rate_hz
        super().__init__()

    def compose(self):
        world = World()
        tpm = max(1, round(self.hold_s * self.rate_hz))
        period = timedelta(seconds=1.0 / self.rate_hz)
        requests = RequestsOp(self, CountCondition(self, tpm * len(self.items)), PeriodicCondition(self, recess_period=period),
                              name="requests", items=self.items, world=world, ticks_per_moment=tpm)
        sensors = SensorsOp(self, CountCondition(self, tpm * len(self.items) + 4), PeriodicCondition(self, recess_period=period),
                            name="sensors", world=world)
        self.gate = GateOp(self, name="gate")
        self.add_flow(requests, self.gate, {("out", "request")})
        self.add_flow(sensors, self.gate, {("out", "readings")})


def _q(xs: list, p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def summary(rows: list) -> tuple[str, bool]:
    props = [r for r in rows if r.get("proposal")]
    wrong = [r for r in props if r.get("as_expected") is False]
    refused = [r for r in rows if r.get("refused")]
    lines = []
    for r in rows:
        if r["kind"] != "moment" and not (r.get("reflex")):
            continue
        what = (f"{r['proposal']:<26} {r['verdict']:<7} {('by ' + r['stopped_by']) if r['stopped_by'] else '':<14}"
                if r.get("proposal") else f"{r['kind']:<26} {(r.get('reflex') or {}).get('action', '-'):<22}")
        age = r.get("age_used_s")
        lines.append(f"{r['scene']:<8} {r['i']}  {what} age used {('%.0f ms' % (age * 1000)) if age is not None else '-':>8}"
                     + ("" if r.get("as_expected") is not False else f"   << EXPECTED {r['expected']}")
                     + (f"   REFUSED: {r['refused']}" if r.get("refused") else ""))
    used = [r["age_used_s"] for r in rows if r.get("age_used_s") is not None]
    carried = [r["age_if_carried_s"] for r in rows if r.get("age_if_carried_s") is not None]
    gate = [r["gate_s"] for r in rows if "gate_s" in r]
    lines.append(f"\n{len(rows)} requests ({sum(r['kind'] == 'reflex' for r in rows)} reflex), {len(props)} proposals, "
                 f"{len(wrong)} not as expected, {len(refused)} refused unchecked")
    if used:
        lines.append(f"age of the readings used:    median {statistics.median(used) * 1000:.0f} ms, "
                     f"p95 {_q(used, .95) * 1000:.0f} ms, max {max(used) * 1000:.0f} ms")
    if carried:
        lines.append(f"age had they been carried:   median {statistics.median(carried) * 1000:.0f} ms, "
                     f"p95 {_q(carried, .95) * 1000:.0f} ms, max {max(carried) * 1000:.0f} ms")
    if gate:
        lines.append(f"gate time:                   median {statistics.median(gate) * 1000:.0f} ms, max {max(gate) * 1000:.0f} ms")
    return "\n".join(lines), not wrong and not refused and len(props) > 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default=os.path.join(TWIN, "scenarios", "gate_demo.json"))
    ap.add_argument("--hold", type=float, default=3.0, help="seconds each scripted moment lasts")
    ap.add_argument("--rate", type=float, default=4.0, help="ticks a second of the devices and the reflex channel")
    ap.add_argument("--threads", type=int, default=3, help="worker threads of the event-based scheduler")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    items = flatten(json.load(open(a.scenes, encoding="utf-8")))
    app = GateStream(items, a.hold, a.rate)
    app.scheduler(EventBasedScheduler(app, name="ebs", worker_thread_number=a.threads, stop_on_deadlock=True))
    app.run()
    text, ok = summary(app.gate.rows)
    print(text)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "results.jsonl"), "w", encoding="utf-8") as f:
            for r in app.gate.rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with open(os.path.join(a.out, "run.txt"), "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
