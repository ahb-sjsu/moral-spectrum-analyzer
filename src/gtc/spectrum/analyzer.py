"""The three-band Moral Spectrum Analyzer (runs locally on Atlas-captured data)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class SpectrumData:
    feeders: list[str]  # F feeder-dimension names
    labels: list[str]  # L native moderation category names
    X: np.ndarray  # (N, F) feeder scores
    Y: np.ndarray  # (N, L) binary native labels
    E: np.ndarray | None  # (N, D) base BGE-M3 embeddings (Band 3), or None
    texts: list[str] | None


def load_spectrum_data(diag_dir: str | Path, prefix: str = "spectrum") -> SpectrumData:
    d = Path(diag_dir)
    with open(d / f"{prefix}_features.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    # feeders are the leading columns; the trailing columns are the native labels.
    label_names = [c for c in header if c in (
        "toxicity", "severe_toxicity", "obscene", "threat", "insult",
        "identity_attack", "sexual_explicit")]
    feeder_names = [c for c in header if c not in label_names]
    fi = [header.index(c) for c in feeder_names]
    li = [header.index(c) for c in label_names]
    data = rows[1:]
    X = np.array([[float(r[i]) for i in fi] for r in data], dtype="float64")
    Y = np.array([[int(r[i]) for i in li] for r in data], dtype="int64")
    E = None
    emb_path = d / f"{prefix}_emb.npy"
    if emb_path.exists():
        E = np.load(emb_path)
    texts = None
    tp = d / f"{prefix}_texts.json"
    if tp.exists():
        texts = json.loads(tp.read_text(encoding="utf-8"))
    return SpectrumData(feeder_names, label_names, X, Y, E, texts)


def band3_confirm(data: SpectrumData, category: str, n_boot: int = 500, seed: int = 0,
                  cv: int = 5, n_emb_pca: int = 50) -> dict:
    """Balanced, bootstrap-CI confirmation that `category` is a dimension the 9 feeders MISS.

    Balanced set = all positives + equal clean negatives (all native labels 0). Out-of-fold AUROC
    (no leakage) for a feeders-model and an embedding-model; bootstrap CI on the gap = AUROC(emb) −
    AUROC(feeders). CONFIRMED iff the gap's lower 95% CI bound > 0 (the embedding significantly beats
    the 9 axes → the moral signal exists but lives outside the current taxonomy).
    """
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import cross_val_predict

    if data.E is None:
        return {"category": category, "error": "no embeddings"}
    j = data.labels.index(category)
    yj = data.Y[:, j]
    pos_idx = np.where(yj == 1)[0]
    neg_idx = np.where(data.Y.sum(1) == 0)[0]  # clean negatives
    n = min(len(pos_idx), len(neg_idx))
    if n < 30:
        return {"category": category, "error": f"too few (pos={len(pos_idx)}, cleanneg={len(neg_idx)})"}
    rng = np.random.default_rng(seed)
    sp = rng.choice(pos_idx, n, replace=False)
    sn = rng.choice(neg_idx, n, replace=False)
    idx = np.concatenate([sp, sn])
    y = np.array([1] * n + [0] * n)

    k = min(n_emb_pca, data.E.shape[1])
    Epca = PCA(n_components=k, random_state=0).fit_transform(data.E - data.E.mean(0))
    Xf, Xe = data.X[idx], Epca[idx]
    oof_f = cross_val_predict(LogisticRegression(max_iter=1000), Xf, y, cv=cv, method="predict_proba")[:, 1]
    oof_e = cross_val_predict(LogisticRegression(max_iter=1000), Xe, y, cv=cv, method="predict_proba")[:, 1]
    af, ae = float(roc_auc_score(y, oof_f)), float(roc_auc_score(y, oof_e))

    gaps = []
    N = len(y)
    for _ in range(n_boot):
        b = rng.integers(0, N, N)
        if 0 < y[b].sum() < N:
            gaps.append(roc_auc_score(y[b], oof_e[b]) - roc_auc_score(y[b], oof_f[b]))
    lo, hi = (float(np.percentile(gaps, 2.5)), float(np.percentile(gaps, 97.5))) if gaps else (None, None)
    return {
        "category": category, "n_pos": int(len(pos_idx)), "n_balanced": int(n),
        "auroc_feeders": round(af, 4), "auroc_embedding": round(ae, 4),
        "gap": round(ae - af, 4), "gap_ci95": [round(lo, 4), round(hi, 4)] if lo is not None else None,
        "confirmed": bool(lo is not None and lo > 0),
    }


# ---------------------------------------------------------------- Band 1: named-dimension spectrum

def band1_named_spectrum(data: SpectrumData) -> np.ndarray:
    """Per-feeder AUROC vs each native category → (F, L). 0.5 = no signal; <0.5 = anti-correlated."""
    from sklearn.metrics import roc_auc_score

    F, L = len(data.feeders), len(data.labels)
    M = np.full((F, L), 0.5)
    for j in range(L):
        y = data.Y[:, j]
        if y.sum() == 0 or y.sum() == len(y):
            continue
        for i in range(F):
            try:
                M[i, j] = roc_auc_score(y, data.X[:, i])
            except ValueError:
                M[i, j] = 0.5
    return M


def band1_theory_radar(data: SpectrumData, label: str, test_frac: float = 0.3, seed: int = 0) -> dict:
    """theory-radar formula over the 9 feeder-scores for one category, vs GB/RF/LR — fair held-out F1.

    Answers the core question per band: does an interpretable formula over the existing axes suffice,
    or is a black box (→ a new encoder) needed? Returns {} if theory-radar isn't importable.
    """
    import numpy as _np
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score

    try:
        import os
        import sys
        # theory-radar is an optional local sibling checkout; probe env override, then a sibling of
        # the repo root, then the home dir — no absolute/user-specific path baked into source.
        sibling = str(Path(__file__).resolve().parents[3].parent / "theory-radar")
        for p in (os.environ.get("THEORY_RADAR_PATH", ""), sibling,
                  os.path.expanduser("~/theory-radar")):
            if p and p not in sys.path:
                sys.path.insert(0, p)
        from symbolic_search import TheoryRadar  # type: ignore
    except Exception as e:  # noqa: BLE001
        return {"error": f"theory-radar unavailable: {e}"}

    j = data.labels.index(label)
    y = data.Y[:, j]
    rng = _np.random.default_rng(seed)
    idx = rng.permutation(len(y))
    cut = int(len(y) * (1 - test_frac))
    tr, te = idx[:cut], idx[cut:]
    Xtr, Xte, ytr, yte = data.X[tr], data.X[te], y[tr], y[te]

    out: dict = {"label": label, "n_pos": int(y.sum()), "n": int(len(y))}
    try:
        # RadarResult exposes .formula + .f1 directly (in-sample search F1). We report the
        # interpretable formula + its in-sample F1; the fair generalization number is the ensemble
        # test F1 below (theory-radar's public API here has no test-replay evaluator).
        radar = TheoryRadar(Xtr, ytr, feature_names=data.feeders, projection="pca")
        res = radar.search(mode="fast", max_depth=3, verbose=False)
        out["formula"] = str(res.formula)
        out["formula_f1_insample"] = round(float(res.f1), 4)
    except Exception as e:  # noqa: BLE001
        out["formula_error"] = str(e)

    for name, clf in (("gb", GradientBoostingClassifier()),
                      ("rf", RandomForestClassifier(n_estimators=100)),
                      ("lr", LogisticRegression(max_iter=1000))):
        try:
            clf.fit(Xtr, ytr)
            out[f"{name}_f1"] = round(float(f1_score(yte, clf.predict(Xte))), 4)
        except Exception:  # noqa: BLE001
            out[f"{name}_f1"] = None
    return out


def band1_contraction_cv(data: SpectrumData, label: str = "toxicity", cv: int = 5, seed: int = 0) -> dict:
    """Out-of-fold contraction scores for a covered category — the `[demonstrated]` discipline.

    Returns the logistic contraction's OOF F1/AUROC AND the symbolic formula's own OOF AUROC (PCA fit
    per fold, unsupervised; sign-agnostic), so the Charter can cite a held-out number for the formula
    itself — not just the ensemble.
    """
    import numpy as np
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score, roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    j = data.labels.index(label)
    y = data.Y[:, j]
    X = data.X
    oof = cross_val_predict(LogisticRegression(max_iter=1000), X, y, cv=cv, method="predict_proba")[:, 1]
    fi = data.feeders.index("fairness_equity")
    formula = np.zeros(len(y))
    for tr, te in StratifiedKFold(cv, shuffle=True, random_state=seed).split(X, y):
        pc0 = PCA(1, random_state=seed).fit(X[tr]).transform(X[te])[:, 0]
        formula[te] = X[te, fi] - pc0
    fa = roc_auc_score(y, formula)
    return {
        "label": label,
        "logistic_oof_f1": round(float(f1_score(y, (oof >= 0.5).astype(int))), 4),
        "logistic_oof_auroc": round(float(roc_auc_score(y, oof)), 4),
        "formula": "fairness_equity - pc0",
        "formula_oof_auroc": round(float(max(fa, 1 - fa)), 4),
    }


# ---------------------------------------------------------------------- Band 2: eigen-spectrum

def band2_eigenspectrum(data: SpectrumData) -> dict:
    """Eigenvalues of the standardized feeder-score covariance → effective rank (participation ratio)."""
    Xs = (data.X - data.X.mean(0)) / (data.X.std(0) + 1e-9)
    C = np.cov(Xs.T)
    w = np.linalg.eigvalsh(C)[::-1]
    w = np.clip(w, 0, None)
    total = float(w.sum()) or 1.0
    participation = float((w.sum() ** 2) / (np.sum(w ** 2) + 1e-12))  # effective rank
    return {
        "eigenvalues": [round(float(v), 5) for v in w],
        "explained_ratio": [round(float(v / total), 5) for v in w],
        "cumulative": [round(float(v), 5) for v in np.cumsum(w) / total],
        "effective_rank_participation": round(participation, 3),
        "n_dims": len(w),
    }


# --------------------------------------------------------- Band 3: residual / discovery spectrum

def band3_residual_discovery(data: SpectrumData, n_emb_pca: int = 50, cv: int = 4) -> dict:
    """Per category: signal reachable from the 9 feeders vs from the raw embedding.

    gap = AUROC(embedding) − AUROC(feeders). A large gap on a category with an independent label
    (e.g. threat, sexual_explicit) = moderation signal the current 9 axes miss → a candidate MISSING
    dimension (admission-filter clean, because the native label is the independent supervision).
    """
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score

    if data.E is None:
        return {"error": "no embeddings captured (Band 3 needs spectrum_emb.npy)"}

    k = min(n_emb_pca, data.E.shape[1], data.E.shape[0] - 1)
    Epca = PCA(n_components=k, random_state=0).fit_transform(
        (data.E - data.E.mean(0)))

    def auroc_cv(Z, y):
        if y.sum() < cv or (len(y) - y.sum()) < cv:
            return None
        clf = LogisticRegression(max_iter=1000)
        return float(np.mean(cross_val_score(clf, Z, y, cv=cv, scoring="roc_auc")))

    rows = []
    for j, lab in enumerate(data.labels):
        y = data.Y[:, j]
        a_feed = auroc_cv(data.X, y)
        a_emb = auroc_cv(Epca, y)
        gap = None if (a_feed is None or a_emb is None) else round(a_emb - a_feed, 4)
        rows.append({
            "category": lab,
            "n_pos": int(y.sum()),
            "auroc_feeders": None if a_feed is None else round(a_feed, 4),
            "auroc_embedding": None if a_emb is None else round(a_emb, 4),
            "gap": gap,  # embedding − feeders; large ⇒ candidate missing dimension
        })
    # rank candidates by gap (only where the embedding actually has signal)
    candidates = sorted(
        [r for r in rows if r["gap"] is not None and r["auroc_embedding"] and r["auroc_embedding"] > 0.65],
        key=lambda r: -(r["gap"] or 0),
    )
    return {"per_category": rows, "missing_dimension_candidates": candidates}
