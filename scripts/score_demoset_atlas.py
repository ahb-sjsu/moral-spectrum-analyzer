"""Score the demo set with the validated xbse feeders (runs on a GPU host), record a replay cache.

Uses `xbse` directly (no erisml-compiler dependency). Loads only feeders whose re-gated report
PASSES (`require_pass` discipline — the failing `rights_respect` feeder is excluded and handled as a
deontic hard-constraint channel elsewhere). Processes ONE feeder at a time (load → score all demo
texts for that dimension → free) so peak VRAM stays ~one BGE-M3, not eight. Writes a JSONL cache
that `gtc.perception.cached.CachedPerception` replays offline; every number comes from a validated
encoder, and each dimension carries its validation provenance.

Env (so no infrastructure paths live in this public repo):
  XBSE_CKPT_DIR (default ~/xbse_ckpt) · GTC_TEXTS_JSON · GTC_CACHE_OUT
Run with xbse on PYTHONPATH and CUDA_VISIBLE_DEVICES set to the free GPU.
"""

from __future__ import annotations

import hashlib
import json
import os

import torch

from xbse.encoder import BSEEncoder
from xbse.instances.joint_builders import BUILDERS
from xbse.report import Report
from xbse.scorer import DimensionScorer

# Canonical DEME-10 k-axis order and its feeders — the compiler's DEME-9 plus the discovered-and-
# validated identity_attack (kept local to avoid an erisml-compiler import on the GPU host).
DEME10 = (
    ("physical_harm", "physharm_joint"),
    ("rights_respect", "rights_joint"),
    ("fairness_equity", "fairness_joint"),
    ("autonomy_respect", "autonomy_joint"),
    ("privacy_protection", "privacy_joint"),
    ("societal_environmental", "environmental_joint"),
    ("virtue_care", "care_joint"),
    ("legitimacy_trust", "legitimacy_joint"),
    ("epistemic_quality", "epistemic_joint"),
    # 10th axis — discovered by the Spectrum Analyzer, validated through the same gate (AUROC 0.80).
    ("identity_attack", "identity_attack_joint"),
)

CKPT = os.path.expanduser(os.environ.get("XBSE_CKPT_DIR", "~/xbse_ckpt"))
TEXTS = os.environ["GTC_TEXTS_JSON"]
OUT = os.environ["GTC_CACHE_OUT"]
BASE = "BAAI/bge-m3"


def _load_report(feeder: str) -> Report:
    with open(os.path.join(CKPT, f"{feeder}_report.json")) as fh:
        return Report(**json.load(fh))


def main() -> None:
    with open(TEXTS, encoding="utf-8") as fh:
        items = json.load(fh)
    texts = [it["text"] for it in items]
    print(f"[score] {len(texts)} texts; ckpt={CKPT}", flush=True)

    per_dim: dict[str, list] = {}
    validation: list[dict] = []
    for dim, feeder in DEME10:
        report = _load_report(feeder)
        m = report.metrics or {}
        validation.append({
            "dimension": dim,
            "feeder_name": feeder,
            "validated": bool(report.passed),
            "structure_auroc": float(m.get("structure_auroc", 0.0)),
            "bow_auroc": float(m.get("bow_auroc", 0.0)),
            "bar_registered": getattr(report, "bar_registered", ""),
            "checkpoint_hash": report.checkpoint_hash,
        })
        if not report.passed:
            print(f"[score]   skip {dim} ({feeder}) — FAIL (deontic hard channel elsewhere)", flush=True)
            continue
        src = BUILDERS[feeder]()
        enc = BSEEncoder(base_model=BASE, max_len=src.max_len, device="cuda")
        enc.load_state_dict(torch.load(os.path.join(CKPT, f"{feeder}.pt"), map_location="cuda"))
        enc.eval()
        scorer = DimensionScorer.from_pairsource(enc, src, report, report.checkpoint_hash)
        per_dim[dim] = scorer.score_batch(texts)
        print(f"[score]   scored {dim} ({feeder})", flush=True)
        del enc, scorer
        torch.cuda.empty_cache()

    with open(OUT, "w", encoding="utf-8") as out:
        for i, it in enumerate(items):
            scores = {}
            for dim, _feeder in DEME10:
                if dim in per_dim:
                    v = per_dim[dim][i]
                    scores[dim] = {"value": float(v.value), "confidence": float(v.confidence),
                                   "direction": v.direction, "validated": True,
                                   "explanation": f"xbse:{dim} cross-dataset feeder"}
                else:
                    scores[dim] = {"value": 0.0, "confidence": 0.0, "direction": "neutral",
                                   "validated": False,
                                   "explanation": f"xbse:{dim} — no validated feeder (hard channel)"}
            out.write(json.dumps({
                "text_sha256": hashlib.sha256(it["text"].encode("utf-8")).hexdigest(),
                "text": it["text"], "backend": "atlas", "recorded_on": "gpu-host",
                "scenario_id": it.get("id"), "kind": it.get("kind"),
                "scores": scores, "validation": validation,
            }, ensure_ascii=False) + "\n")
    print(f"[score] wrote {len(items)} entries -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
