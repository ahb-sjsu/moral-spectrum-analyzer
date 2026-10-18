"""One input changed: does the verdict change with it?

    python twin/counterfactual.py [--cases twin/scenarios/counterfactual.json] [--out DIR]

Each case is a base and a variant that differ in exactly one input the brain reads: one sensor,
one signature, one heard event, or one report from an authenticated channel. The runner refuses a
case whose base and variant differ in more than that (the narration and the expected verdict are
not inputs). Each side runs in a fresh StackBrain through gate_demo.run_scene, the same path as the
brain-only gate demo. The expected verdicts are written in the case file before the run, and the
run reports any that differ.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gate_demo import run_scene  # noqa: E402

NOT_INPUTS = {"say", "expect"}


def differences(a, b, path="") -> list:
    """Paths where two scene values differ, ignoring narration and expectations."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k in NOT_INPUTS:
                continue
            if k not in a or k not in b:
                out.append(f"{path}/{k}")
            else:
                out += differences(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) == len(b):
            return [
                d
                for i, (x, y) in enumerate(zip(a, b, strict=True))
                for d in differences(x, y, f"{path}[{i}]")
            ]
        ja, jb = [json.dumps(x, sort_keys=True) for x in a], [
            json.dumps(x, sort_keys=True) for x in b
        ]
        return [f"{path}{{{x}}}" for x in sorted(set(ja) ^ set(jb))]
    return [] if a == b else [path]


def verdict(m: dict) -> str:
    return m["verdict"] if m["verdict"] == "passed" else f"stopped:{m['stopped_by']}"


def run_case(case: dict) -> dict:
    diff = differences(case["base"], case["variant"])
    if len(diff) != 1:
        raise SystemExit(
            f"case {case['id']}: base and variant differ in {len(diff)} inputs, not one: {diff}"
        )
    out = {
        "id": case["id"],
        "title": case["title"],
        "changed": case["changed"],
        "differs_at": diff[0],
    }
    for side in ("base", "variant"):
        r = run_scene({"id": f"{case['id']}-{side}", "title": case["title"], "moments": case[side]})
        last = [m for m in r["moments"] if "proposal" in m][-1]
        out[side] = {
            "verdict": verdict(last),
            "expected": last.get("expected"),
            "as_expected": last.get("as_expected"),
            "checks": last["checks"],
            "robot_does": last["robot_does"],
            "moments": r["moments"],
        }
    out["verdict_changed"] = out["base"]["verdict"] != out["variant"]["verdict"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(HERE, "scenarios", "counterfactual.json"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    cases = json.load(open(a.cases, encoding="utf-8"))
    results = [run_case(c) for c in cases]
    for r in results:
        print(f"\n== {r['id']}: {r['title']}\n   changed: {r['changed']}  ({r['differs_at']})")
        for side in ("base", "variant"):
            s = r[side]
            mark = "" if s["as_expected"] else f"   << EXPECTED {s['expected']}"
            print(f"   {side:<8} {s['verdict']:<18}{mark}")
        print(f"   verdict changed: {'yes' if r['verdict_changed'] else 'NO'}")
    off = [(r["id"], s) for r in results for s in ("base", "variant") if not r[s]["as_expected"]]
    print(
        f"\n{len(results)} cases, {sum(r['verdict_changed'] for r in results)} verdicts changed with the one input, "
        f"{len(off)} sides not as expected{': ' + ', '.join(f'{i}/{s}' for i, s in off) if off else ''}"
    )
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
