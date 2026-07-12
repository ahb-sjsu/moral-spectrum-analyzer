"""Cross-lingual invariance AT SCALE — analysis. Reuses the demo's index definition
(index = (xling_cos − unrel_cos)/(1 − unrel_cos), `measure_xling.py`) on a larger held-out set that
**includes harmful content** (translated by NLLB, which — unlike the demo's LLM translator — does not
refuse). Reports the index overall and split harmful vs benign, per language, with a bootstrap CI.

Consumes `data/xling_scale/xling_scale_{bge,labse}.npy` + `xling_scale_idx.json` (Atlas capture).
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data" / "xling_scale"
LANGS = ["es", "ar", "zh", "hi", "sw"]


def analyze(tag: str) -> dict | None:
    npy = D / f"xling_scale_{tag}.npy"
    if not npy.exists():
        return None
    Z = np.load(npy)
    Z = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)
    idx = json.loads((D / "xling_scale_idx.json").read_text(encoding="utf-8"))
    by, harm = {}, {}
    for i, m in enumerate(idx):
        by.setdefault(m["id"], {})[m["lang"]] = i
        harm[m["id"]] = bool(m.get("harmful"))

    per_lang = {l: [] for l in LANGS}
    xling, xh, xb, en_rows = [], [], [], []
    for sid, langs in by.items():
        if "en" not in langs:
            continue
        en = Z[langs["en"]]; en_rows.append(langs["en"])
        for l in LANGS:
            if l in langs:
                c = float(en @ Z[langs[l]])
                per_lang[l].append(c); xling.append(c)
                (xh if harm[sid] else xb).append(c)
    unrel = np.array([float(Z[i] @ Z[j]) for i, j in itertools.combinations(en_rows, 2)])
    xling = np.array(xling)
    u = float(unrel.mean())

    def index(arr):
        return float((np.mean(arr) - u) / (1 - u)) if len(arr) else float("nan")

    rng = np.random.default_rng(0)
    boot = [((rng.choice(xling, len(xling)).mean() - rng.choice(unrel, len(unrel)).mean())
             / (1 - rng.choice(unrel, len(unrel)).mean())) for _ in range(2000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {
        "tag": tag, "xling_cos": round(float(xling.mean()), 3), "unrel_cos": round(u, 3),
        "index": round(index(xling), 3), "index_harmful": round(index(xh), 3),
        "index_benign": round(index(xb), 3), "ci": [round(float(lo), 2), round(float(hi), 2)],
        "per_lang": {l: round(float(np.mean(v)), 3) for l, v in per_lang.items() if v},
        "n_xling": len(xling), "n_harmful_pairs": len(xh), "n_benign_pairs": len(xb),
    }


def main() -> None:
    out = {}
    print("cross-lingual canonical invariance AT SCALE (incl. harmful; higher index = better):")
    for tag in ("bge", "labse"):
        r = analyze(tag)
        if r is None:
            print(f"  {tag}: (no embeddings)"); continue
        out[tag] = r
        name = {"bge": "BGE-M3", "labse": "LaBSE "}[tag]
        print(f"  {name}: index {r['index']} CI {r['ci']}  (harmful {r['index_harmful']} / "
              f"benign {r['index_benign']}; xling {r['xling_cos']} vs unrel {r['unrel_cos']}, "
              f"n={r['n_xling']})  per-lang {r['per_lang']}")
    (D / "xling_scale_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {D / 'xling_scale_result.json'}")


if __name__ == "__main__":
    main()
