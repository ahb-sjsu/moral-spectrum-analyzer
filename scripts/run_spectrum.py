"""Run the Moral Spectrum Analyzer on Atlas-captured data; print report + write the spectrogram.

  python scripts/run_spectrum.py --dir <captured_dir> --out out/spectrum
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gtc.spectrum import (
    band1_named_spectrum,
    band1_theory_radar,
    band2_eigenspectrum,
    band3_residual_discovery,
    load_spectrum_data,
)
from gtc.spectrum.render import spectrogram_html, spectrogram_png


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="dir with spectrum_features.csv + spectrum_emb.npy")
    ap.add_argument("--out", default="out/spectrum")
    ap.add_argument("--radar", action="store_true", help="also run theory-radar per category (slow)")
    ap.add_argument("--radar-labels", default="", help="comma-list to limit theory-radar categories")
    args = ap.parse_args()

    data = load_spectrum_data(args.dir)
    emb = None if data.E is None else data.E.shape
    print(f"loaded N={data.X.shape[0]}  feeders={len(data.feeders)}  labels={len(data.labels)}  emb={emb}")

    M = band1_named_spectrum(data)
    print("\n=== Band 1: per-feeder AUROC vs category ===")
    print("feeder".ljust(24) + " ".join(l[:9].rjust(9) for l in data.labels))
    for i, f in enumerate(data.feeders):
        print(f.ljust(24) + " ".join(f"{M[i, j]:9.2f}" for j in range(len(data.labels))))

    b2 = band2_eigenspectrum(data)
    print(f"\n=== Band 2: eigen-spectrum ===  effective rank ≈ {b2['effective_rank_participation']}"
          f" of {b2['n_dims']}")
    print("  explained ratio:", b2["explained_ratio"])

    b3 = band3_residual_discovery(data)
    print("\n=== Band 3: feeders vs embedding (gap = missing signal) ===")
    for r in b3.get("per_category", []):
        print(f"  {r['category']:16s} feeders={r['auroc_feeders']}  emb={r['auroc_embedding']}  "
              f"gap={r['gap']}  (n_pos={r['n_pos']})")
    print("  MISSING-DIMENSION candidates:",
          [c["category"] for c in b3.get("missing_dimension_candidates", [])])

    tr = {}
    if args.radar:
        only = [s.strip() for s in args.radar_labels.split(",") if s.strip()] or data.labels
        print("\n=== Band 1: theory-radar (formula over 9 axes vs ensembles) ===")
        for lab in data.labels:
            if lab not in only:
                continue
            r = band1_theory_radar(data, lab)
            tr[lab] = r
            if "error" in r:
                print(f"  {lab:16s} {r['error']}")
            else:
                print(f"  {lab:16s} formula={r.get('formula', '-')}  f1={r.get('formula_f1')}  "
                      f"| gb={r.get('gb_f1')} rf={r.get('rf_f1')} lr={r.get('lr_f1')}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "spectrogram.html").write_text(spectrogram_html(data.feeders, data.labels, M, b2, b3),
                                          encoding="utf-8")
    png = spectrogram_png(data.feeders, data.labels, M, out / "spectrogram.png")
    (out / "spectrum.json").write_text(json.dumps({
        "feeders": data.feeders, "labels": data.labels, "band1_auroc": M.tolist(),
        "band2": b2, "band3": b3, "theory_radar": tr}, indent=2), encoding="utf-8")
    print(f"\nwrote {out}/spectrogram.html {'+ spectrogram.png ' if png else ''}+ spectrum.json")


if __name__ == "__main__":
    main()
