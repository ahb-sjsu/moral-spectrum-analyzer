#!/usr/bin/env python3
"""Count what the paper and the monograph cite about the robot's scene and the dev set, so the
fact sheets (paper/aies2027/kit/FACTS.md) are recounted, not remembered.

  python twin/scene_counts.py [--scene twin/scene/margaret_home.erisml] [--dev twin/scenarios/dev.jsonl]

Needs erisml_compiler on PYTHONPATH."""
from __future__ import annotations

import argparse
import json
from collections import Counter

from erisml_compiler.ingestion.structured_loader import load_structured_input


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="twin/scene/margaret_home.erisml")
    ap.add_argument("--dev", default="twin/scenarios/dev.jsonl")
    a = ap.parse_args()
    ir = load_structured_input(a.scene)
    ex = ir.extra or {}
    robot = [n for n in ir.norms if n.actor == "robot"]
    mod = Counter(n.modality for n in ir.norms)
    print(f"rules: {len(ir.norms)} ({mod['obligation']} obligations, {mod['prohibition']} prohibitions, "
          f"{mod['permission']} permissions); non-defeasible {sum(not n.defeasible for n in ir.norms)}; robot's {len(robot)}")
    et = ex.get("event_types", {})
    system = [k for k, v in et.items() if isinstance(v, dict) and v.get("source") == "system"]
    print(f"event types: {len(et)}, of which {len(system)} system-only")
    caps = ex.get("capabilities", [])
    elevated = [c["action"] for c in caps if c.get("elevated")]
    governed = [c["action"] for c in caps if c.get("governed") and not c.get("elevated")]
    print(f"capabilities: {len(caps)}; {len(elevated)} elevated, {len(governed)} governed ({len(elevated) + len(governed)} need the governor)")
    refusals = ex.get("refusals", {})
    print(f"refusal kinds: {len(refusals)} ({', '.join(sorted(refusals))})")
    strata = ex.get("strata", {})
    states = sum(len(s.get("states", [])) for s in strata.values())
    gates = sum(len(s.get("gates", [])) for s in strata.values())
    print(f"strata: {len(strata)} stratifications, {states} strata, {gates} gates")
    subs = ex.get("sensor_substrates", {})
    print(f"devices: {len(subs)} on {len(set(subs.values()))} substrates")
    off = (ex.get("offline") or {}).get("events", [])
    print(f"offline rules: {len(off)}, of which {sum(bool(r.get('floor')) for r in off)} floor rules")
    rows = [json.loads(l) for l in open(a.dev) if l.strip()]
    cls = Counter(r["response_class"] for r in rows)
    print(f"dev scenarios: {len(rows)} ({', '.join(f'{cls[k]} {k}' for k in sorted(cls))})")


if __name__ == "__main__":
    main()
