"""Committed out-of-fold contraction numbers for a covered category (closes the Band-1 scratchpad gap).

  python scripts/band1_contraction.py --dir data/spectrum --label toxicity
"""

from __future__ import annotations

import argparse
import json

from gtc.spectrum import band1_contraction_cv, load_spectrum_data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/spectrum")
    ap.add_argument("--label", default="toxicity")
    args = ap.parse_args()
    data = load_spectrum_data(args.dir, prefix="spectrum")
    r = band1_contraction_cv(data, label=args.label)
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
