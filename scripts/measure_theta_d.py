"""Measure the decision-layer invariance ratio theta_d, raw vs. the drift-projection mechanism.

theta_d = mean|ΔS|_reframe / mean|ΔS|_unrelated, where S is the contracted satisfaction scalar.
The drift subspace is fit LEAVE-SCENARIO-OUT (never on the held-out scenario's own pair), so the
number is not circular. Reports a sweep over the projection rank r. Pre-registered target: <= 0.5.

Inputs (produced on the GPU host by scratchpad/measure_all.py, one BGE-M3 pass per feeder):
  feeder_demo.npz       Z_<dim> (21x1024 feeder-space demo embeddings) + axis/center/scale per dim
  feeder_demo_idx.json  per-row {scenario, kind}
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from moral_spectrum.invariance_mechanism import CanonicalProjector, valence  # noqa: E402

INDEPENDENT = ["physical_harm", "autonomy_respect", "privacy_protection",
               "societal_environmental", "identity_attack"]
FAMILY = ["virtue_care", "fairness_equity", "legitimacy_trust", "epistemic_quality"]
DIMS = INDEPENDENT + FAMILY


def load(npz_path: str, idx_path: str):
    d = np.load(npz_path)
    idx = json.loads(Path(idx_path).read_text())
    feats = {dim: {"Z": d[f"Z_{dim}"].astype("float64"), "axis": d[f"axis_{dim}"].astype("float64"),
                   "center": float(d[f"center_{dim}"]), "scale": float(d[f"scale_{dim}"])}
             for dim in DIMS}
    return feats, idx


def scores_matrix(feats, projectors=None):
    """(n_texts, n_dims) valence per feeder; optional per-dim CanonicalProjector applied first."""
    cols = {}
    for dim in DIMS:
        Z = feats[dim]["Z"]
        if projectors and dim in projectors:
            Z = projectors[dim].project(Z)
        cols[dim] = valence(Z, feats[dim]["axis"], feats[dim]["center"], feats[dim]["scale"])
    return cols


def contract_S(cols, i):
    ind = [cols[d][i] for d in INDEPENDENT]
    fam = np.mean([cols[d][i] for d in FAMILY])
    return float(np.mean(ind + [fam]))


def main():
    D = Path(__file__).resolve().parents[1] / "data" / "invariance"
    feats, idx = load(str(D / "feeder_demo.npz"), str(D / "feeder_demo_idx.json"))
    n = len(idx)
    by_scn = {}
    for i, m in enumerate(idx):
        by_scn.setdefault(m["scenario"], {}).setdefault(m["kind"], i)
    scns = list(by_scn)
    reframe_pairs = [(s, by_scn[s]["base"], by_scn[s][k])
                     for s in scns for k in by_scn[s] if k.startswith("reframe")]
    euph_pairs = [(s, by_scn[s]["base"], by_scn[s][k])
                  for s in scns for k in by_scn[s] if k.startswith("euphemism")]
    bases = {s: by_scn[s]["base"] for s in scns}
    unrelated = list(combinations(scns, 2))
    print(f"{n} texts · {len(scns)} scenarios · {len(reframe_pairs)} reframe pairs · "
          f"{len(euph_pairs)} euphemism pairs · {len(unrelated)} unrelated base pairs\n")

    def theta(cols_full, cols_by_heldout, pair_list, pair_kind="reframe"):
        # reframe/euphemism deviations use the leave-scenario-out cols for that scenario
        dev = []
        for s, i, j in pair_list:
            cols = cols_by_heldout[s] if cols_by_heldout else cols_full
            dev.append(abs(contract_S(cols, i) - contract_S(cols, j)))
        num = float(np.mean(dev)) if dev else float("nan")
        unrel = [abs(contract_S(cols_full, bases[a]) - contract_S(cols_full, bases[b]))
                 for a, b in unrelated]
        den = float(np.mean(unrel))
        return num, den, num / den

    # ---- RAW (no projection) ----
    raw_cols = scores_matrix(feats)
    rn, rd, r_theta = theta(raw_cols, None, reframe_pairs)
    _, _, r_theta_e = theta(raw_cols, None, euph_pairs, "euphemism")
    print(f"RAW           reframe|ΔS|={rn:.4f}  unrelated|ΔS|={rd:.4f}  "
          f"theta_d={r_theta:.3f}   (euphemism theta={r_theta_e:.3f})")

    # ---- MECHANISM: leave-scenario-out drift projection, swept over rank r ----
    print("\nrank r │  reframe|ΔS|   theta_d(reframe)   theta_d(euphemism)   meets ≤0.5")
    best = None
    for r in range(1, 6):
        # For each held scenario, fit drift on the OTHER scenarios' reframe pairs (per feeder).
        cols_by_heldout = {}
        for s_held in scns:
            projectors = {}
            for dim in DIMS:
                Z = feats[dim]["Z"]
                diffs = [Z[i] - Z[j] for (s, i, j) in reframe_pairs if s != s_held]
                projectors[dim] = CanonicalProjector.fit(np.array(diffs), r)
            cols_by_heldout[s_held] = scores_matrix(feats, projectors)
        # Unrelated uses a full-fit projector (fit on ALL reframe drift — no base-base leakage).
        full_proj = {dim: CanonicalProjector.fit(
            np.array([feats[dim]["Z"][i] - feats[dim]["Z"][j] for (_s, i, j) in reframe_pairs]), r)
            for dim in DIMS}
        cols_full_proj = scores_matrix(feats, full_proj)
        rn2, rd2, th = theta(cols_full_proj, cols_by_heldout, reframe_pairs)
        _, _, th_e = theta(cols_full_proj, cols_by_heldout, euph_pairs, "euphemism")
        flag = "  ✓" if th <= 0.5 else ""
        print(f"   {r}   │   {rn2:.4f}        {th:.3f}              {th_e:.3f}          {flag}")
        if best is None or th < best[1]:
            best = (r, th, th_e)
    print(f"\nBest drift-projection: rank r={best[0]}  theta_d(reframe)={best[1]:.3f}  "
          f"theta_d(euphemism)={best[2]:.3f}  → target ≤ 0.5 {'MET' if best[1] <= 0.5 else 'NOT MET'}")

    # ---- diagnostic: in-sample drift projection (fit on ALL pairs incl. held; NOT honest, only
    #      to tell a generalisation failure from a fundamental one) ----
    in_proj = {dim: CanonicalProjector.fit(
        np.array([feats[dim]["Z"][i] - feats[dim]["Z"][j] for (_s, i, j) in reframe_pairs]), 2)
        for dim in DIMS}
    cols_in = scores_matrix(feats, in_proj)
    _, _, th_in = theta(cols_in, None, reframe_pairs)
    print(f"  [diagnostic] in-sample drift-projection (r=2) theta_d={th_in:.3f} "
          f"— {'even in-sample fails → drift is not the score-moving structure' if th_in > 0.5 else 'works in-sample → LOO generalisation is the issue'}")

    # ---- MECHANISM 2: average over the equivalence class (leave-self-out) ----
    S = {i: contract_S(raw_cols, i) for i in range(n)}
    Sinv = {}
    for s, kinds in by_scn.items():
        members = list(kinds.values())
        for i in members:
            others = [j for j in members if j != i]
            Sinv[i] = float(np.mean([S[j] for j in others])) if others else S[i]
    num = np.mean([abs(Sinv[i] - Sinv[j]) for (_s, i, j) in reframe_pairs])
    den = np.mean([abs(Sinv[bases[a]] - Sinv[bases[b]]) for a, b in unrelated])
    num_e = np.mean([abs(Sinv[i] - Sinv[j]) for (_s, i, j) in euph_pairs]) if euph_pairs else float("nan")
    print(f"\nMECHANISM 2 — equivalence-class averaging (leave-self-out proxy):")
    print(f"  reframe|ΔS|={num:.4f}  unrelated|ΔS|={den:.4f}  theta_d(reframe)={num/den:.3f}  "
          f"theta_d(euphemism)={num_e/den:.3f}  → target ≤ 0.5 {'MET' if num/den <= 0.5 else 'NOT MET'}")


if __name__ == "__main__":
    main()
