"""Fit + freeze the learned contraction for a covered category (toxicity), validated OUT-OF-FOLD.

Ships the all-data coefficients but reports the honest OOF AUROC/F1 (the feeder-gate discipline: the
number that certifies it is the held-out one). Thresholds are chosen to make the *moderate* decisions
high-precision, disclosing how much it then escalates. Writes data/contraction/toxicity_contraction.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import cross_val_predict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gtc.contraction import ContractionValidation, LearnedContraction  # noqa: E402
from gtc.spectrum.analyzer import load_spectrum_data  # noqa: E402

LABEL = "toxicity"
FITTED = "2026-07-12"


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def _disjoint_mask(texts: list[str]) -> np.ndarray:
    """True for spectrum rows the identity_attack feeder did NOT train on.

    Leakage control (review-10): the identity_attack feeder is the contraction's dominant feature and
    was trained on civil_comments rows; any spectrum row inside that training set has a memorization-
    inflated identity_attack score. We exclude those rows (matched by SHA-256 of the normalized text)
    so the OOF AUROC and the identity_attack lift are measured on rows the feeder never saw.
    """
    hp = ROOT / "data" / "spectrum" / "feeder_train_hashes.json"
    hset = set(json.loads(hp.read_text())["hashes"])
    keep = np.array([hashlib.sha256(_norm(t).encode()).hexdigest() not in hset for t in texts])
    return keep


def main() -> None:
    data = load_spectrum_data(str(ROOT / "data" / "spectrum"))
    ident = np.array(json.loads(
        (ROOT / "data" / "invariance" / "identity_ci_and_rank.json").read_text()
    )["identity_spectrum_scores"])
    texts = json.loads((ROOT / "data" / "spectrum" / "spectrum_texts.json").read_text(encoding="utf-8"))
    assert len(ident) == data.X.shape[0] == len(texts), (len(ident), data.X.shape[0], len(texts))
    feats = list(data.feeders) + ["identity_attack"]     # 9 graded feeders

    keep = _disjoint_mask(texts)
    n_leak = int((~keep).sum())
    X = np.column_stack([data.X, ident])[keep]
    X8 = data.X[keep]                                    # 8-feeder baseline (for the honest lift)
    y = data.Y[:, data.labels.index(LABEL)].astype(int)[keep]
    n, pos = len(y), int(y.sum())
    print(f"[fit] disjoint N={n} (excluded {n_leak} feeder-train rows)  {LABEL} base-rate={pos/n:.3f}",
          flush=True)

    oof = cross_val_predict(LogisticRegression(max_iter=1000), X, y, cv=5,
                            method="predict_proba")[:, 1]
    auroc = float(roc_auc_score(y, oof))
    f1 = float(f1_score(y, (oof >= 0.5).astype(int)))
    oof8 = cross_val_predict(LogisticRegression(max_iter=1000), X8, y, cv=5,
                             method="predict_proba")[:, 1]
    auroc8 = float(roc_auc_score(y, oof8))
    print(f"[fit] OOF AUROC={auroc:.4f}  F1@0.5={f1:.4f}  (8-feeder baseline={auroc8:.4f}, "
          f"identity_attack lift={auroc - auroc8:+.4f})", flush=True)

    # thresholds: p_remove = lowest t whose OOF remove-precision ≥ 0.80; p_allow = highest t whose
    # OOF allow-precision (1 − violation rate among p ≤ t) ≥ 0.90.  Disclose the resulting coverage.
    grid = np.round(np.arange(0.30, 0.951, 0.01), 2)
    p_remove = 0.90
    for t in grid:
        m = oof >= t
        if m.sum() >= 10 and y[m].mean() >= 0.80:
            p_remove = float(t); break
    p_allow = 0.10
    for t in grid[::-1]:
        m = oof <= t
        if m.sum() >= 10 and (1 - y[m].mean()) >= 0.90:
            p_allow = float(t); break

    rem_mask, allow_mask = oof >= p_remove, oof <= p_allow
    remove_precision = float(y[rem_mask].mean()) if rem_mask.sum() else 0.0
    allow_precision = float(1 - y[allow_mask].mean()) if allow_mask.sum() else 0.0
    moderate_rate = float((rem_mask | allow_mask).mean())
    print(f"[fit] p_remove={p_remove}  p_allow={p_allow}  moderate_rate={moderate_rate:.3f}  "
          f"remove_precision={remove_precision:.3f}  allow_precision={allow_precision:.3f}", flush=True)

    clf = LogisticRegression(max_iter=1000).fit(X, y)          # ship all-data coefficients
    lc = LearnedContraction(
        feature_order=tuple(feats), coef=tuple(float(c) for c in clf.coef_[0]),
        intercept=float(clf.intercept_[0]), p_remove=p_remove, p_allow=p_allow,
        validation=ContractionValidation(
            label=LABEL,
            corpus="civil_comments Spectrum Band-1 corpus, N=%d disjoint (%d feeder-train rows excluded)"
                   % (n, n_leak),
            oof_auroc=round(auroc, 4), oof_f1=round(f1, 4), n=n, folds=5, fitted=FITTED,
            moderate_rate=round(moderate_rate, 4), remove_precision=round(remove_precision, 4),
            allow_precision=round(allow_precision, 4),
            baseline_auroc=round(auroc8, 4), leakage_controlled=True),
    )
    out = ROOT / "data" / "contraction" / "toxicity_contraction.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    lc.to_json(out)
    print(f"[fit] wrote {out}  validated={lc.validated}", flush=True)
    order = np.argsort(np.abs(clf.coef_[0]))[::-1]
    print("[fit] top weights: " + ", ".join(f"{feats[i]}={clf.coef_[0][i]:+.2f}" for i in order[:5]))


if __name__ == "__main__":
    main()
