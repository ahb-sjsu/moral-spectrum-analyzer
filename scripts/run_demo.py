"""Moderate every demo scenario and print a scorecard. Default backend = cached real perception.

  python scripts/run_demo.py --backend cached
"""

from __future__ import annotations

import argparse

from moral_spectrum.decision import graded_validated
from moral_spectrum.pipeline import moderate
from moral_spectrum.scenarios import SCENARIOS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["stub", "cached", "atlas"], default="cached")
    args = ap.parse_args()

    print(f"{'scenario':30s} {'gold':9s} {'decision':9s} {'S':>7s}  {'val':3s} principal")
    print("-" * 88)
    agree = 0
    for s in SCENARIOS:
        r = moderate(s.base, backend=args.backend)
        d = r.decision
        gv = "yes" if graded_validated(r.perception) else "NO"
        match = "✓" if d.action == s.gold else " "
        agree += int(d.action == s.gold)
        print(f"{s.id:30s} {s.gold:9s} {d.action:9s} {d.satisfaction:+7.3f}  {gv:3s} "
              f"{r.tensor.metadata['spectral']['principal_dimension']:22s} {match}")
    print("-" * 88)
    print(f"gold-agreement: {agree}/{len(SCENARIOS)}  (heuristic thresholds; calibration is a "
          f"governance parameter)")


if __name__ == "__main__":
    main()
