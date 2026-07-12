"""Build + gate the identity_attack feeder (GTC 'validated new dimension' deliverable).

Two INDEPENDENT corpora, one agreed valence convention ('-' = identity attacked, '+' = respected):
  A) Jigsaw civil_comments   identity_attack >= 0.5  -> '-' ;  clean (ia<0.05, tox<0.10) -> '+'
  B) Berkeley Measuring-Hate-Speech  hate_speech_score > 0.5 -> '-' ; < -1.0 (supportive) -> '+'

Pre-registered gate (identical policy to the 8 passing feeders): VALIDATED iff cross-dataset
held-out AUROC beats BOTH the untrained-encoder null AND a TF-IDF bag-of-words null by >= 0.10.
The null is measured on the UNTRAINED BGE-M3 before training, then frozen into the Bar (registered
today) -> the baseline is a property of (untrained model + corpus), not of the trained feeder.
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "1"          # GPU 1 only — leave GPU 0
os.environ.setdefault("HF_HOME", "/archive/cache/huggingface")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import itertools
import json
import random
import sys

sys.path.insert(0, os.path.expanduser("~/xbse/src"))

from datasets import load_dataset  # noqa: E402

OUT = "/archive/ethics-corpora/identity_attack"
CKDIR = os.path.expanduser("~/xbse_ckpt")
os.makedirs(OUT, exist_ok=True)
os.makedirs(CKDIR, exist_ok=True)


def build_civil(cap_neg=700, cap_pos=700, max_stream=450_000):
    ds = load_dataset("civil_comments", split="train", streaming=True)
    neg, pos = [], []
    for i, r in enumerate(itertools.islice(ds, max_stream)):
        ia = float(r.get("identity_attack", 0) or 0)
        tox = float(r.get("toxicity", 0) or 0)
        t = (r.get("text") or "").strip().replace("\n", " ")
        if len(t) < 12:
            continue
        if ia >= 0.5 and len(neg) < cap_neg:
            neg.append(t)
        elif ia < 0.05 and tox < 0.10 and (i % 37 == 0) and len(pos) < cap_pos:
            pos.append(t)
        if len(neg) >= cap_neg and len(pos) >= cap_pos:
            print(f"  [civil] caps met at stream row {i}", flush=True)
            break
    n = min(len(neg), len(pos))
    rows = [(t, "-") for t in neg[:n]] + [(t, "+") for t in pos[:n]]
    return rows, len(neg), len(pos)


def build_mhs(cap=2500):
    m = load_dataset("ucberkeley-dlab/measuring-hate-speech", split="train")
    seen, neg, pos = set(), [], []
    for r in m:
        t = (r.get("text") or "").strip().replace("\n", " ")
        if len(t) < 12:
            continue
        k = t.lower()[:120]
        if k in seen:
            continue
        seen.add(k)
        s = float(r.get("hate_speech_score", 0.0))
        if s > 0.5:
            neg.append(t)
        elif s < -1.0:
            pos.append(t)
    random.Random(0).shuffle(neg)
    random.Random(1).shuffle(pos)
    n = min(len(neg), len(pos), cap)
    rows = [(t, "-") for t in neg[:n]] + [(t, "+") for t in pos[:n]]
    return rows, len(neg), len(pos)


def dump(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for t, s in rows:
            f.write(json.dumps({"text": t, "sign": s}, ensure_ascii=False) + "\n")


print("=== building corpora ===", flush=True)
cc_rows, ccn, ccp = build_civil()
print(f"[civil_comments] neg(attack)={ccn} pos(clean)={ccp} -> balanced {len(cc_rows)}", flush=True)
mhs_rows, mn, mp = build_mhs()
print(f"[mhs] neg(hate)={mn} pos(supportive)={mp} -> balanced {len(mhs_rows)}", flush=True)
dump(f"{OUT}/civil_comments_identity.jsonl", cc_rows)
dump(f"{OUT}/mhs_identity.jsonl", mhs_rows)

from xbse.bar import Bar  # noqa: E402
from xbse.encoder import BSEEncoder  # noqa: E402
from xbse.instances.joint import JointPairSource  # noqa: E402
from xbse.train_adv import train_adversarial  # noqa: E402
from xbse.validate import gate  # noqa: E402

src = JointPairSource(
    name="identity_attack_joint",
    domains=[("civil_comments", cc_rows), ("mhs", mhs_rows)],
    holdout_frac=0.12,
    invariant_structure=(
        "identity-attack valence (a person or group demeaned/attacked for their identity vs "
        "treated with dignity), shared across Jigsaw civil-comments and Berkeley hate-speech"
    ),
    label_source=(
        "Jigsaw civil_comments identity_attack label (>=0.5 attack / clean respected) + "
        "Measuring-Hate-Speech hate_speech_score (>0.5 attack / <-1 supportive) — independent corpora"
    ),
)
from collections import Counter  # noqa: E402

rows = src._rows()
print(f"[identity_attack_joint] rows={len(rows)} by-domain={Counter(r[0] for r in rows)} "
      f"by-sign={Counter(r[2] for r in rows)}", flush=True)

ev = src.heldout_eval()
enc = BSEEncoder(base_model="BAAI/bge-m3", pooling="mean", max_len=128, device="cuda")

base = gate(enc, ev)  # untrained null — measured BEFORE training, frozen into the bar
null, bow0 = float(base["structure_auroc"]), float(base["bow_auroc"])
print(f"[identity_attack_joint] UNTRAINED null structure_auroc={null:.4f} bow={bow0:.4f}", flush=True)

bar = Bar(
    auroc_min=round(min(max(null + 0.10, 0.5001), 0.999), 3),
    fuzz_min=1.0,
    policy="baseline_relative",
    margin=0.10,
    baseline_auroc=round(null, 3),
    source=f"baseline-relative(margin 0.10) over untrained null {null:.3f} + BoW null",
    derivation=(
        "VALIDATED iff cross-dataset held-out AUROC beats BOTH the untrained-encoder null "
        f"({null:.3f}) and the TF-IDF bag-of-words null by >=0.10 on the same held-out pairs; "
        "nulls are properties of (untrained model + corpus), measured before training this feeder."
    ),
    registered="2026-07-11",
)
src.bar = bar

ckpt = f"{CKDIR}/identity_attack_joint.pt"
train_adversarial(
    enc, src, epochs=6, batch_size=24, lr=2e-5, max_steps=1200,
    max_lambda=0.0, checkpoint_path=ckpt, report_path=f"{OUT}/identity_attack_report.json",
)

fin = gate(enc, ev)  # trained
tr, bown = float(fin["structure_auroc"]), float(fin["bow_auroc"])
margin = tr - max(null, bown)
passed = bool(margin >= 0.10 and fin.get("fuzz_ratio", 2.0) > 1.0)
result = {
    "dim": "identity_attack_joint",
    "trained_auroc": round(tr, 4),
    "untrained_null": round(null, 4),
    "bow_null": round(bown, 4),
    "margin_vs_max_null": round(margin, 4),
    "fuzz_ratio": round(float(fin.get("fuzz_ratio", float("nan"))), 4),
    "gate_passed": passed,
    "n_rows": len(rows),
    "checkpoint": ckpt,
}
print("RESULT " + json.dumps(result), flush=True)
