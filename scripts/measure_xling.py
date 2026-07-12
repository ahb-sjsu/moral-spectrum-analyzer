"""Cross-lingual invariance A/B: does the canonicalizer map a text and its translation close?

For each model (BGE-M3, LaBSE): cross-lingual cosine = cos(English base, its translation); ceiling =
cos(English base_i, English base_j) unrelated. Cross-lingual index = (xling - ceiling)/(1 - ceiling).
Per-language breakdown + bootstrap CI. LaBSE (translation-trained) is expected to win here.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np

D = Path("data/xling")
LANGS = ["es", "ar", "zh", "hi", "sw"]


def analyze(tag: str) -> dict:
    Z = np.load(D / f"xling_emb_{tag}.npy")
    Z = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)
    idx = json.loads((D / f"xling_emb_{tag}.npy.idx.json").read_text(encoding="utf-8"))
    by = {}
    for i, m in enumerate(idx):
        by.setdefault(m["id"], {})[m["lang"]] = i
    per_lang = {l: [] for l in LANGS}
    xling = []
    en_rows = []
    for sid, langs in by.items():
        if "en" not in langs:
            continue
        en = Z[langs["en"]]; en_rows.append(langs["en"])
        for l in LANGS:
            if l in langs:
                c = float(en @ Z[langs[l]])
                per_lang[l].append(c); xling.append(c)
    unrel = [float(Z[i] @ Z[j]) for i, j in itertools.combinations(en_rows, 2)]
    xling, unrel = np.array(xling), np.array(unrel)
    rng = np.random.default_rng(0)
    boot = [((rng.choice(xling, len(xling)).mean() - rng.choice(unrel, len(unrel)).mean())
             / (1 - rng.choice(unrel, len(unrel)).mean())) for _ in range(2000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {
        "tag": tag,
        "xling_cos": round(float(xling.mean()), 3),
        "unrel_cos": round(float(unrel.mean()), 3),
        "index": round(float((xling.mean() - unrel.mean()) / (1 - unrel.mean())), 3),
        "ci": [round(float(lo), 2), round(float(hi), 2)],
        "per_lang": {l: round(float(np.mean(v)), 3) for l, v in per_lang.items() if v},
        "n_xling": len(xling),
    }


def main() -> None:
    print("cross-lingual canonical invariance (text vs its translation; higher index = better):")
    for tag in ("bge", "labse"):
        r = analyze(tag)
        name = {"bge": "BGE-M3", "labse": "LaBSE "}[tag]
        print(f"  {name}: index {r['index']} CI {r['ci']}  (xling {r['xling_cos']} vs unrelated "
              f"{r['unrel_cos']}, n={r['n_xling']})  per-lang {r['per_lang']}")


if __name__ == "__main__":
    main()
