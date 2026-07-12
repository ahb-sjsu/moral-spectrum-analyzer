"""One Atlas pass covering: (A) 9 graded feeders' demo embeddings + axes for the θ_d mechanism;
(B) identity_attack held-out bootstrap AUROC CI (review-9 #3a); (C) identity_attack feeder scores
over the 1600 Band-2 texts for the effective-rank re-run (review-9 #3b)."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "1"
os.environ.setdefault("HF_HOME", "/archive/cache/huggingface")
import json, sys
import numpy as np
HOME = os.path.expanduser("~")            # runtime home (no username hard-coded in source)
sys.path.insert(0, f"{HOME}/xbse/src")
import torch
from sklearn.metrics import roc_auc_score
from xbse.encoder import BSEEncoder
from xbse.instances.joint_builders import BUILDERS
from xbse.report import Report
from xbse.scorer import DimensionScorer, _np
from xbse.validate import _sim

CKPT = f"{HOME}/xbse_ckpt"
GRADED = [
    ("physical_harm", "physharm_joint"), ("fairness_equity", "fairness_joint"),
    ("autonomy_respect", "autonomy_joint"), ("privacy_protection", "privacy_joint"),
    ("societal_environmental", "environmental_joint"), ("virtue_care", "care_joint"),
    ("legitimacy_trust", "legitimacy_joint"), ("epistemic_quality", "epistemic_joint"),
    ("identity_attack", "identity_attack_joint"),
]
demo_recs = [json.loads(l) for l in open(f"{HOME}/gtc_cache.jsonl", encoding="utf-8") if l.strip()]
demo_texts = [r["text"] for r in demo_recs]
demo_idx = [{"scenario": r.get("scenario_id"), "kind": r.get("kind")} for r in demo_recs]
spectrum_texts = json.load(open(f"{HOME}/spectrum_texts.json", encoding="utf-8"))
print(f"[measure] demo={len(demo_texts)} spectrum={len(spectrum_texts)}", flush=True)

out, results = {}, {}
for dim, feeder in GRADED:
    rep = Report(**json.load(open(f"{CKPT}/{feeder}_report.json")))
    if not rep.passed:
        print(f"[measure] skip {dim} (FAIL)", flush=True); continue
    src = BUILDERS[feeder]()
    enc = BSEEncoder(base_model="BAAI/bge-m3", max_len=src.max_len, device="cuda")
    enc.load_state_dict(torch.load(f"{CKPT}/{feeder}.pt", map_location="cuda")); enc.eval()
    sc = DimensionScorer.from_pairsource(enc, src, rep, rep.checkpoint_hash)
    Zd = _np(enc.encode(demo_texts))
    out[f"Z_{dim}"] = Zd.astype("float32"); out[f"axis_{dim}"] = sc.axis.astype("float32")
    out[f"center_{dim}"] = np.float32(sc.center); out[f"scale_{dim}"] = np.float32(sc.scale)
    print(f"[measure] {dim}: demo Z{Zd.shape}", flush=True)
    if dim == "identity_attack":
        # (B) anchor-level bootstrap CI on structure_auroc (the gate's held-out pairs)
        ev = src.heldout_eval(); sp = ev["structural_pairs"]
        A = [a for a, _b, _l in sp]; B = [b for _a, b, _l in sp]
        y = np.array([1 if l else 0 for _a, _b, l in sp])
        sim = np.asarray(_sim(enc, A, B), dtype="float64")
        au = float(roc_auc_score(y, sim))
        n_anchor = len(sp) // 2  # pairs come in (pos,neg) blocks per held anchor
        rng = np.random.default_rng(0); boots = []
        for _ in range(3000):
            anc = rng.integers(0, n_anchor, n_anchor)
            idx = np.concatenate([[2 * a, 2 * a + 1] for a in anc])
            if 0 < y[idx].sum() < len(idx):
                boots.append(roc_auc_score(y[idx], sim[idx]))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        results["identity_ci"] = {"auroc": round(au, 4), "lo": round(float(lo), 4),
                                  "hi": round(float(hi), 4), "n_pairs": int(len(y)),
                                  "n_anchors": int(n_anchor)}
        print(f"[measure] identity_attack structure_auroc {au:.4f} CI[{lo:.3f},{hi:.3f}]", flush=True)
        # (C) feeder scores over the 1600 Band-2 texts (for the effective-rank re-run)
        se = sc.score_batch(list(spectrum_texts))
        results["identity_spectrum_scores"] = [round(float(v.value), 6) for v in se]
    del enc, sc; torch.cuda.empty_cache()

np.savez(f"{HOME}/feeder_demo.npz", **out)
json.dump(demo_idx, open(f"{HOME}/feeder_demo_idx.json", "w"))
json.dump(results, open(f"{HOME}/measure_results.json", "w"))
print("SAVED feeder_demo.npz + measure_results.json", flush=True)
print("DONE ci=" + json.dumps(results.get("identity_ci")), flush=True)
