"""Live analyzer scoring for the autonomous twin, on the GPU host.

The governor's gate 3 reads analyzer scores through the replay backend, which refuses any text
without a recorded real encoder output. For a situation nobody wrote in advance (the dog bites
Margaret) there is no recorded output, so the robot could never be cleared by the analyzer. This
module closes that gap without weakening the rule: it keeps the validated xbse feeders loaded,
scores a new text with them, and appends the real outputs to the replay cache before the ruling
reads it. The record has the same schema as scripts/score_demoset_atlas.py writes, plus
`recorded_live`, so a live score can be replayed and audited later like any other.

Only feeders whose re-gated report passes are loaded (the failing rights feeder is excluded, as in
the scoring script). Set MSA_CACHE_PATH to the cache file both this and the governor use.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone

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
    ("identity_attack", "identity_attack_joint"),
)
BASE = "BAAI/bge-m3"


class LiveScorer:
    def __init__(self, cache_path: str, ckpt_dir: str | None = None, device: str = "cuda"):
        import torch
        from xbse.encoder import BSEEncoder
        from xbse.instances.joint_builders import BUILDERS
        from xbse.report import Report
        from xbse.scorer import DimensionScorer

        self.cache_path, self.lock = cache_path, threading.Lock()
        ckpt = os.path.expanduser(ckpt_dir or os.environ.get("XBSE_CKPT_DIR", "~/xbse_ckpt"))
        self.scorers, self.validation = {}, []
        for dim, feeder in DEME10:
            with open(os.path.join(ckpt, f"{feeder}_report.json")) as fh:
                report = Report(**json.load(fh))
            m, cal = report.metrics or {}, getattr(report, "calibration", None) or {}
            self.validation.append({
                "dimension": dim, "feeder_name": feeder, "validated": bool(report.passed),
                "structure_auroc": float(m.get("structure_auroc", 0.0)), "bow_auroc": float(m.get("bow_auroc", 0.0)),
                "bar_registered": getattr(report, "bar_registered", ""), "checkpoint_hash": report.checkpoint_hash,
                "reliability_weight": float(cal.get("reliability_weight", 1.0)), "calibration_ece": cal.get("calibration_ece"),
            })
            if not report.passed:
                continue
            src = BUILDERS[feeder]()
            enc = BSEEncoder(base_model=BASE, max_len=src.max_len, device=device)
            enc.load_state_dict(torch.load(os.path.join(ckpt, f"{feeder}.pt"), map_location=device))
            enc.eval()
            self.scorers[dim] = DimensionScorer.from_pairsource(enc, src, report, report.checkpoint_hash)
        self.known = set()
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as fh:
                self.known = {json.loads(line)["text_sha256"] for line in fh if line.strip()}

    def ensure(self, text: str, note: str = "") -> bool:
        """Score `text` with every validated feeder and record it, unless it is recorded already.
        Returns True when a new record was written."""
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with self.lock:
            if sha in self.known:
                return False
            scores = {}
            for dim, _f in DEME10:
                if dim in self.scorers:
                    v = self.scorers[dim].score_batch([text])[0]
                    scores[dim] = {"value": float(v.value), "confidence": float(v.confidence), "direction": v.direction,
                                   "validated": True, "explanation": f"xbse:{dim} cross-dataset feeder"}
                else:
                    scores[dim] = {"value": 0.0, "confidence": 0.0, "direction": "neutral", "validated": False,
                                   "explanation": f"xbse:{dim} - no validated feeder (hard channel)"}
            rec = {"text_sha256": sha, "text": text, "backend": "atlas", "recorded_on": "gpu-host",
                   "recorded_live": datetime.now(timezone.utc).isoformat(), "scenario_id": None, "kind": note or "live",
                   "scores": scores, "validation": self.validation}
            with open(self.cache_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.known.add(sha)
            return True
