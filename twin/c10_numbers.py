"""Numbers for verification claim C10, from the graded rehearsal runs since the walking fix.

  python c10_numbers.py RUN_DIR [RUN_DIR ...]

Each RUN_DIR holds results.jsonl and grade.json (twin/grade_scenarios.py --json). Act-time checks
are counted only in runs whose records contain authorize verdicts.
"""
import json
import re
import sys

tot = dict(scenario_runs=0, containment_breaches=0, privacy_violations=0, harness_failures=0)
grants, refusals, maxd = [], [], {}
acts = unauth = authref = 0
for run in sys.argv[1:]:
    name = run.rstrip("/").split("/")[-1]
    g = json.load(open(f"{run}/grade.json"))
    for r in g["rows"]:
        ok = r["class_correct"] and not r["forbidden_taken"] and not r["required_missing"]
        print(f"{name} {r['id']} {'PASS' if ok else 'MISS'} breaches={len(r['containment_breaches'])} "
              f"privacy={len(r['privacy_violations'])} forbidden={r['forbidden_taken']} missing={r['required_missing']}")
        tot["scenario_runs"] += 1
        tot["containment_breaches"] += len(r["containment_breaches"])
        tot["privacy_violations"] += len(r["privacy_violations"])
        tot["harness_failures"] += int(bool(r["harness_failure"]))
    for line in open(f"{run}/results.jsonl"):
        d = json.loads(line)
        last = {}
        for x in d["records"]:
            rec = x["record"]
            k = rec.get("kind")
            for m in re.finditer(r'distance_to_robot_m": ([0-9.]+)', json.dumps(rec)):
                maxd[name] = max(maxd.get(name, 0.0), float(m.group(1)))
            ru = rec.get("ruling") if k == "decision" else None
            if ru and ru.get("outcome") in ("elevate", "authorize_ems", "restraint"):
                grants.append((name, d["id"], ru["outcome"], ru.get("witnesses"), ru.get("witness_bar")))
            if ru and str(ru.get("outcome", "")).startswith("refuse"):
                refusals.append((name, d["id"], ru.get("witnesses"), ru.get("witness_bar")))
            if k == "authorize":
                last[rec["action"]] = rec["verdict"]
                if rec["verdict"] != "allowed":
                    authref += 1
            if k == "performed" and any(xx["record"].get("kind") == "authorize" for xx in d["records"]):
                acts += 1
                if last.get(rec["action"]) != "allowed":
                    unauth += 1
                    print("  performed without an allowed act-time check:", name, d["id"], rec["action"])
print("TOTAL", tot)
print("grants", len(grants), "min(witnesses - bar)", min(w - b for *_, w, b in grants),
      "kinds", sorted(set((o, w, b) for _, _, o, w, b in grants)))
print("evidence refusals", len(refusals), "(witnesses, bar):", sorted(set((w, b) for *_, w, b in refusals)))
print("act-time: performed", acts, "| without a prior allowed check", unauth, "| act-time refusals", authref)
print("max Margaret-robot distance (m):", maxd)
