"""Confirm the discovered dimensions — category-BALANCED capture (oversamples rare categories).

The first spectrum run balanced on toxicity, leaving threat/identity_attack/sexual_explicit with
18/51/33 positives (noisy AUROCs). This streams civil_comments and collects up to CAP_POS positives
PER category (plus a clean-negative pool), so each candidate gets enough positives for a bootstrap
CI on the feeders-vs-embedding gap. Scores the 8 validated feeders + base BGE-M3 embeddings; same
output format as the spectrum capture (confirm_features.csv + confirm_emb.npy).

Env: XBSE_CKPT_DIR · DIAG_DIR · CAP_POS (250) · CAP_NEG (1500) · MAX_SCAN (300000).
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
NATIVE = ("toxicity", "severe_toxicity", "obscene", "threat", "insult",
          "identity_attack", "sexual_explicit")
RARE = ("threat", "identity_attack", "sexual_explicit")
CKPT = os.path.expanduser(os.environ.get("XBSE_CKPT_DIR", "~/xbse_ckpt"))
DIAG_DIR = os.environ["DIAG_DIR"]
CAP_POS = int(os.environ.get("CAP_POS", "250"))
CAP_NEG = int(os.environ.get("CAP_NEG", "1500"))
MAX_SCAN = int(os.environ.get("MAX_SCAN", "300000"))
BASE = "BAAI/bge-m3"


def collect():
    ds = load_dataset("civil_comments", split="train", streaming=True)
    pools = {c: [] for c in NATIVE}
    negs = []
    seen = set()
    scanned = 0
    for r in ds:
        scanned += 1
        if scanned > MAX_SCAN:
            break
        t = (r.get("text") or "").strip().replace("\n", " ")
        if not (20 <= len(t) <= 800) or t in seen:
            continue
        labs = {c: (1 if float(r.get(c, 0.0) or 0.0) >= 0.5 else 0) for c in NATIVE}
        placed = False
        for c in NATIVE:
            if labs[c] and len(pools[c]) < CAP_POS:
                pools[c].append((t, labs))
                seen.add(t)
                placed = True
                break
        if not placed and not any(labs.values()) and len(negs) < CAP_NEG:
            negs.append((t, labs))
            seen.add(t)
        if all(len(pools[c]) >= CAP_POS for c in RARE) and len(negs) >= CAP_NEG:
            break
    rows, added = [], set()
    for c in NATIVE:
        for (t, labs) in pools[c]:
            if t not in added:
                rows.append((t, labs))
                added.add(t)
    for (t, labs) in negs:
        if t not in added:
            rows.append((t, labs))
            added.add(t)
    counts = {c: sum(lb[c] for _, lb in rows) for c in NATIVE}
    print(f"[confirm] scanned {scanned}, corpus {len(rows)}, positives {counts}", flush=True)
    return [t for t, _ in rows], {c: [lb[c] for _, lb in rows] for c in NATIVE}


def embed_base(texts, batch=128):
    enc = BSEEncoder(base_model=BASE, max_len=192, device="cuda")
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
    texts, labels = collect()
    cols = {}
    for dim, feeder in DEME9:
        with open(os.path.join(CKPT, f"{feeder}_report.json")) as fh:
            report = Report(**json.load(fh))
        if not report.passed:
            continue
        src = BUILDERS[feeder]()
        enc = BSEEncoder(base_model=BASE, max_len=src.max_len, device="cuda")
        enc.load_state_dict(torch.load(os.path.join(CKPT, f"{feeder}.pt"), map_location="cuda"))
        enc.eval()
        sc = DimensionScorer.from_pairsource(enc, src, report, report.checkpoint_hash)
        cols[dim] = [float(v.value) for v in sc.score_batch(texts)]
        print(f"[confirm]   scored {dim}", flush=True)
        del enc, sc
        torch.cuda.empty_cache()
    emb = embed_base(texts)

    dims = [d for d, _ in DEME9 if d in cols]
    with open(os.path.join(DIAG_DIR, "confirm_features.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(dims + list(NATIVE))
        for i in range(len(texts)):
            w.writerow([f"{cols[d][i]:.5f}" for d in dims] + [labels[lab][i] for lab in NATIVE])
    np.save(os.path.join(DIAG_DIR, "confirm_emb.npy"), emb)
    print(f"[confirm] wrote features({len(texts)}x{len(dims)}) + emb{emb.shape} -> {DIAG_DIR}", flush=True)


if __name__ == "__main__":
    main()
