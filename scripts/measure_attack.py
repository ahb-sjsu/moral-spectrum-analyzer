"""Attack-detection AUROC: does canonical distance from the base separate euphemisms from reframes?

Per variant, feature = 1 − cosine(scenario base, variant) in the BGE-M3 canonical space; label = 1 if
euphemism (oblique/softened rewording), 0 if reframe (direct paraphrase). AUROC that distance predicts
euphemism, with a bootstrap CI. NOTE: the LLM refused to generate variants for the overtly-harmful
scenarios, so this measures oblique-vs-direct rewording on non-harmful content — the harmful-content
red-team needs an uncensored / hand-authored adversarial set.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

D = Path("data/variants")


def main() -> None:
    Z = np.load(D / "variants_emb.npy")
    Z = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)
    idx = json.loads((D / "variants_emb.npy.idx.json").read_text(encoding="utf-8"))
    base = {m["id"]: i for i, m in enumerate(idx) if m["kind"] == "base"}
    dist, label = [], []
    for i, m in enumerate(idx):
        if m["kind"] in ("reframe", "euphemism") and m["id"] in base:
            dist.append(1 - float(Z[base[m["id"]]] @ Z[i]))
            label.append(1 if m["kind"] == "euphemism" else 0)
    dist, label = np.array(dist), np.array(label)
    au = roc_auc_score(label, dist)
    rng = np.random.default_rng(0)
    boots = []
    for _ in range(3000):
        b = rng.integers(0, len(label), len(label))
        if 0 < label[b].sum() < len(b):
            boots.append(roc_auc_score(label[b], dist[b]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    print(f"attack-detection AUROC (euphemism vs reframe via canonical distance) = {au:.3f}  "
          f"95% CI [{lo:.2f}, {hi:.2f}]")
    print(f"  n_euphemism={int(label.sum())}  n_reframe={int((1-label).sum())}  "
          f"(non-harmful scenarios only — harmful were refused)")
    print(f"  mean canonical distance: euphemism={dist[label==1].mean():.3f}  "
          f"reframe={dist[label==0].mean():.3f}")
    print(f"  target θ = 0.70 → {'MET' if lo >= 0.70 else ('directional' if au >= 0.70 else 'NOT met')}")


if __name__ == "__main__":
    main()
