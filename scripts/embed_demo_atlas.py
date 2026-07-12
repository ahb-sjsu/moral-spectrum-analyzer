"""Embed the demo texts (base + reframings + euphemisms) with base BGE-M3 — the canonicalizer's space.

Lets us test BIP invariance at the layer that is *supposed* to provide it: does the canonicalizer map
meaning-preserving re-descriptions close together (high cosine) vs. unrelated content (low)? Writes
demo_emb.npy + demo_emb.npy.idx.json (id, kind per row).

Env: GTC_TEXTS_JSON · DEMO_EMB_OUT.  Run with xbse on PYTHONPATH, CUDA_VISIBLE_DEVICES, HF_HOME.
"""

from __future__ import annotations

import json
import os

import numpy as np
import torch

from xbse.encoder import BSEEncoder

TEXTS = os.environ["GTC_TEXTS_JSON"]
OUT = os.environ["DEMO_EMB_OUT"]
BASE_MODEL = os.environ.get("BASE_MODEL", "BAAI/bge-m3")  # A/B: bge-m3 vs sentence-transformers/LaBSE

with open(TEXTS, encoding="utf-8") as fh:
    items = json.load(fh)
texts = [it["text"] for it in items]

enc = BSEEncoder(base_model=BASE_MODEL, max_len=192, device="cuda")
enc.eval()
z = enc.encode(texts)
z = z.detach().cpu().numpy().astype("float32") if hasattr(z, "detach") else np.asarray(z, "float32")
np.save(OUT, z)
with open(OUT + ".idx.json", "w", encoding="utf-8") as fh:
    json.dump([{k: v for k, v in it.items() if k != "text"} for it in items], fh)
print(f"[embed] wrote {OUT} {z.shape}", flush=True)
