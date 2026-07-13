"""Bootstrap confirmation of the discovered missing dimensions (balanced capture).

  python scripts/confirm_dims.py --dir data/confirm
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from moral_spectrum.spectrum import band3_confirm, load_spectrum_data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default="out/spectrum/confirm.json")
    ap.add_argument("--cats", default="threat,identity_attack,sexual_explicit,obscene,toxicity,insult")
    args = ap.parse_args()

    data = load_spectrum_data(args.dir, prefix="confirm")
    emb = None if data.E is None else data.E.shape
    print(f"loaded N={data.X.shape[0]}  labels={data.labels}  emb={emb}")
    print("\ncategory          feeders   embed     gap    CI95              verdict     (n_pos)")
    print("-" * 84)
    res = {}
    for c in [s.strip() for s in args.cats.split(",") if s.strip()]:
        if c not in data.labels:
            continue
        r = band3_confirm(data, c)
        res[c] = r
        if "error" in r:
            print(f"{c:16s}  {r['error']}")
        else:
            verdict = "CONFIRMED" if r["confirmed"] else "not confirmed"
            print(f"{c:16s}  {r['auroc_feeders']:.3f}   {r['auroc_embedding']:.3f}  "
                  f"{r['gap']:+.3f}  {str(r['gap_ci95']):16s}  {verdict:12s} ({r['n_pos']})")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
