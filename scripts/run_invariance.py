"""Run the lean Phase-0.5 invariance measurement and print/write the report.

  python scripts/run_invariance.py --backend cached
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from gtc import DEME9
from gtc.invariance import invariance_report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["stub", "cached", "atlas"], default="cached")
    ap.add_argument("--out", default="out/invariance.json")
    args = ap.parse_args()

    r = invariance_report(args.backend)
    print(f"backend={r.backend}  reframe-pairs={r.n_reframe_pairs}  euphemism-pairs={r.n_euph_pairs}")
    print(f"\nOverall mean |Δ| per re-description (DEME score units, range [-1,1]):")
    print(f"  reframings (meaning-preserving, want SMALL): {r.reframe_mean}")
    print(f"  euphemism  (adversarial evasion)          : {r.euph_mean}")
    print(f"  UNRELATED content (no-invariance ceiling) : {r.baseline_mean}")
    print(f"  invariance ratio (reframe/ceiling; 0=perfect, 1=none): {r.invariance_ratio}")
    print(f"  decision stability (base vs reframing)    : {r.decision_stability:.0%}")
    print("\nper-dimension mean |Δ|      reframe   euphemism")
    for d in DEME9:
        print(f"  {d:24s} {str(r.per_dim_reframe[d]):>7s}   {str(r.per_dim_euph[d]):>7s}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(r), indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
