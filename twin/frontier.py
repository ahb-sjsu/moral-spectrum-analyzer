#!/usr/bin/env python3
"""Trace the (false-clear, over-restriction) frontier by sweeping the permissive
threshold, then GET-evaluate it. Shows that the operating point a governor should
pick is evaluator-relative.

  python twin/frontier.py [--backend cached|stub]
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scenarios import SCENARIOS       # noqa: E402
from governor import govern           # noqa: E402
from metrics_get import report as get_report, evaluate as get_evaluate  # noqa: E402


def rates(backend, mode, ps):
    rul = [govern(sc, backend=backend, mode=mode, permissive_s=ps) for sc in SCENARIOS]
    pos = [r for r in rul if r.should_elevate]
    neg = [r for r in rul if not r.should_elevate]
    fc = sum(1 for r in neg if r.elevate) / max(len(neg), 1)
    orr = sum(1 for r in pos if not r.elevate) / max(len(pos), 1)
    return round(fc, 4), round(orr, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="cached", choices=["stub", "cached", "atlas"])
    a = ap.parse_args()
    configs = {"conservative": rates(a.backend, "conservative", 1.0)}
    for ps in (0.25, 0.21, 0.13):
        configs[f"permissive@{ps}"] = rates(a.backend, "permissive", ps)

    print(f"\nbackend={a.backend}  (false_clear, over_restriction) frontier:")
    for k, (fc, orr) in configs.items():
        print(f"  {k:16} fc={fc:.3f}  or={orr:.3f}")
    r = get_report(configs)
    json.dump({"backend": a.backend, "frontier": configs, "get": r},
              open(os.path.join(HERE, f"twin_frontier_{a.backend}.json"), "w"), indent=2)
    print(f"\nwrote twin_frontier_{a.backend}.json")


if __name__ == "__main__":
    main()
