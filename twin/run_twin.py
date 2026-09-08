#!/usr/bin/env python3
"""Run every scenario through the governor and measure the trust metrics.

  false-clear      = elevated when it should NOT have  (the failure that harms)
  over-restriction = refused when it SHOULD have       (the failure that neglects)

Usage:  python twin/run_twin.py [--backend stub|cached|atlas]
The stub backend is an unvalidated keyword heuristic: expect the fail-safe
default to dominate (few/no false-clears, high over-restriction) — that is the
correct behaviour of a governor that will not act on unvalidated reads. Real
discrimination needs a validated backend (cached/atlas).
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scenarios import SCENARIOS       # noqa: E402
from governor import govern           # noqa: E402
from metrics_get import evaluate as get_evaluate, report as get_report  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="stub", choices=["stub", "cached", "atlas"])
    a = ap.parse_args()

    rulings = [govern(sc, backend=a.backend) for sc in SCENARIOS]
    pos = [r for r in rulings if r.should_elevate]        # real emergencies
    neg = [r for r in rulings if not r.should_elevate]    # non-emergencies
    false_clear = [r for r in neg if r.elevate]
    over_restrict = [r for r in pos if not r.elevate]

    fc_rate = len(false_clear) / max(len(neg), 1)
    or_rate = len(over_restrict) / max(len(pos), 1)

    print(f"\nbackend={a.backend}   scenarios={len(rulings)} "
          f"(emergencies={len(pos)}, non-emergencies={len(neg)})\n")
    print(f"{'id':18} {'truth':>6} {'elevate':>8} {'gate':>12} {'ok':>3}  reason")
    for r in rulings:
        print(f"{r.scenario_id:18} {str(r.should_elevate):>6} {str(r.elevate):>8} "
              f"{r.gate:>12} {'Y' if r.correct else 'N':>3}  {r.reason}")

    print(f"\nfalse-clear rate      = {fc_rate:.3f}  "
          f"({len(false_clear)}/{len(neg)})  [elevated when it must not]"
          + (("  -> " + ", ".join(r.scenario_id for r in false_clear)) if false_clear else ""))
    print(f"over-restriction rate = {or_rate:.3f}  "
          f"({len(over_restrict)}/{len(pos)})  [refused a real emergency]"
          + (("  -> " + ", ".join(r.scenario_id for r in over_restrict)) if over_restrict else ""))
    if a.backend == "stub":
        print("\nNOTE: stub is unvalidated; the fail-safe default is expected to dominate. "
              "Run --backend cached/atlas for the discrimination result.")

    # GET evaluation (evaluator-relative distance-to-ideal); compare vs the stub
    # baseline if this is a different backend, to expose ranking-dependence.
    configs = {a.backend: (round(fc_rate, 4), round(or_rate, 4))}
    base_p = os.path.join(HERE, "twin_results_stub.json")
    if a.backend != "stub" and os.path.exists(base_p):
        b = json.load(open(base_p))
        configs["stub"] = (b["false_clear_rate"], b["over_restriction_rate"])
    get_report(configs)
    get_result = get_evaluate(configs)

    out = {"backend": a.backend, "n": len(rulings),
           "false_clear_rate": round(fc_rate, 4), "over_restriction_rate": round(or_rate, 4),
           "false_clear_ids": [r.scenario_id for r in false_clear],
           "over_restriction_ids": [r.scenario_id for r in over_restrict],
           "get_evaluation": get_result,
           "rulings": [vars(r) for r in rulings]}
    p = os.path.join(HERE, f"twin_results_{a.backend}.json")
    json.dump(out, open(p, "w"), indent=2, default=str)
    print(f"\nwrote {os.path.relpath(p)}")


if __name__ == "__main__":
    main()
