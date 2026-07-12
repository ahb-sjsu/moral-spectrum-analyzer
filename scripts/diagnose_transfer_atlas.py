"""Moral Spectrum Analyzer — Atlas data capture (one pass).

Scores a balanced sample of a real moderation corpus (civil_comments — NOT a feeder training set, so
this is an honest zero-shot transfer test) and captures everything the three-band analyzer needs:

  - X: the 8 validated feeder scores per item          (Band 1: named-dimension spectrum)
  - labels: civil_comments' OWN native sub-labels       (Band 1 targets + Band 3 admission labels)
      toxicity, severe_toxicity, obscene, threat, insult, identity_attack, sexual_explicit
  - E: base BGE-M3 embeddings per item                  (Band 3: residual / discovery substrate)

Outputs (env DIAG_DIR): spectrum_features.csv (8 feeders + 7 labels), spectrum_emb.npy (N×D base
embeddings), spectrum_texts.json. Analysis + spectrogram render run locally.

Env: XBSE_CKPT_DIR · DIAG_DIR · N (default 1600).  Run with xbse on PYTHONPATH, CUDA_VISIBLE_DEVICES, HF_HOME.
"""

from __future__ import annotations

import csv
import json
import os

import numpy as np
import torch
from datasets import load_dataset

from xbse.encoder import BSEEncoder
from xbse.instances.joint_builders import BUILDERS
from xbse.report import Report
from xbse.scorer import DimensionScorer

DEME9 = (
    ("physical_harm", "physharm_joint"), ("rights_respect", "rights_joint"),
    ("fairness_equity", "fairness_joint"), ("autonomy_respect", "autonomy_joint"),
    ("privacy_protection", "privacy_joint"), ("societal_environmental", "environmental_joint"),
    ("virtue_care", "care_joint"), ("legitimacy_trust", "legitimacy_joint"),
    ("epistemic_quality", "epistemic_joint"),
)
NATIVE_LABELS = ("toxicity", "severe_toxicity", "obscene", "threat", "insult",
                 "identity_attack", "sexual_explicit")
CKPT = os.path.expanduser(os.environ.get("XBSE_CKPT_DIR", "~/xbse_ckpt"))
DIAG_DIR = os.environ["DIAG_DIR"]
N = int(os.environ.get("N", "1600"))
BASE = "BAAI/bge-m3"


def load_sample(n: int):
    """Balanced-on-toxicity sample; return texts + all native labels (binarized at 0.5)."""
    ds = load_dataset("civil_comments", split="train", streaming=True)
    half = n // 2
    pos, neg = [], []  # (text, {label: 0/1})
    for r in ds:
        t = (r.get("text") or "").strip().replace("\n", " ")
        if not (20 <= len(t) <= 800):
            continue
        rec = (t, {lab: (1 if float(r.get(lab, 0.0) or 0.0) >= 0.5 else 0) for lab in NATIVE_LABELS})
        bucket = pos if rec[1]["toxicity"] else neg
        if len(bucket) < half:
            bucket.append(rec)
        if len(pos) >= half and len(neg) >= half:
            break
    rows = pos[:half] + neg[:half]
    texts = [t for t, _ in rows]
    labels = {lab: [lb[lab] for _, lb in rows] for lab in NATIVE_LABELS}
    return texts, labels


def embed_base(texts, batch=128):
    enc = BSEEncoder(base_model=BASE, max_len=192, device="cuda")  # no checkpoint = base BGE-M3
    enc.eval()
    out = []
    for i in range(0, len(texts), batch):
        z = enc.encode(texts[i:i + batch])
        z = z.detach().cpu().numpy() if hasattr(z, "detach") else np.asarray(z)
        out.append(z.astype("float32"))
    del enc
    torch.cuda.empty_cache()
    return np.concatenate(out, 0)


def main() -> None:
    os.makedirs(DIAG_DIR, exist_ok=True)
    texts, labels = load_sample(N)
    print(f"[spectrum] {len(texts)} texts; toxic={sum(labels['toxicity'])}", flush=True)

    cols = {}
    for dim, feeder in DEME9:
        with open(os.path.join(CKPT, f"{feeder}_report.json")) as fh:
            report = Report(**json.load(fh))
        if not report.passed:
            print(f"[spectrum]   skip {dim} (FAIL)", flush=True)
            continue
        src = BUILDERS[feeder]()
        enc = BSEEncoder(base_model=BASE, max_len=src.max_len, device="cuda")
        enc.load_state_dict(torch.load(os.path.join(CKPT, f"{feeder}.pt"), map_location="cuda"))
        enc.eval()
        sc = DimensionScorer.from_pairsource(enc, src, report, report.checkpoint_hash)
        cols[dim] = [float(v.value) for v in sc.score_batch(texts)]
        print(f"[spectrum]   scored {dim}", flush=True)
        del enc, sc
        torch.cuda.empty_cache()

    print("[spectrum] base embeddings...", flush=True)
    emb = embed_base(texts)

    dims = [d for d, _ in DEME9 if d in cols]
    with open(os.path.join(DIAG_DIR, "spectrum_features.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(dims + list(NATIVE_LABELS))
        for i in range(len(texts)):
            w.writerow([f"{cols[d][i]:.5f}" for d in dims] + [labels[lab][i] for lab in NATIVE_LABELS])
    np.save(os.path.join(DIAG_DIR, "spectrum_emb.npy"), emb)
    with open(os.path.join(DIAG_DIR, "spectrum_texts.json"), "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False)
    print(f"[spectrum] wrote features({len(texts)}x{len(dims)}) + emb{emb.shape} -> {DIAG_DIR}", flush=True)


if __name__ == "__main__":
    main()
