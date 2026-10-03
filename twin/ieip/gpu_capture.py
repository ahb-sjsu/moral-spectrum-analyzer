#!/usr/bin/env python3
"""One GPU's share of the I-EIP replay (docs/PREREG_IEIP_TWIN.md, amendments A2 and A5).

    python twin/ieip/gpu_capture.py --prompts P/prompts.jsonl --start 0 --end 120 \\
        --model /data/ieip-twin/models/qwen2.5-7b-instruct --out RUN

Reads finished prompts (analysis.py prepare) and builds nothing, so the GPU is busy as soon as
the weights are in. The model is loaded once, straight to the GPU. Pass one captures the
hidden states with erisml-compiler's HuggingFaceActivationSource wrapping that model's base
(the hooks and forward pass of A2, without a second copy of the weights); pass two generates
the classification greedily from the same text. The states are stored as the bf16 bit
patterns they are (uint16), which halves them losslessly: the model runs in bf16, so the
monitor's float32 copies are exact bf16 values, and that is checked. A shard's outputs are written under temporary
names and renamed last, with a .done.json naming the prompts file's sha256, so a shard is
either complete or absent. nvidia-smi samples the GPU every 15 s into the log, the evidence
that the pod kept its GPU busy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from analysis import DEPTHS, MAX_NEW_TOKENS, MAX_PROMPT_TOKENS, MODEL  # noqa: E402


def layers_for(n_layers: int) -> list[int]:
    """The registered depths (25, 50, 75 and 90 percent) as layer indices."""
    return sorted({int(d * n_layers) for d in DEPTHS})


def _log(t0: float, *msg) -> None:
    print(f"[{time.time() - t0:8.1f}s]", *msg, flush=True)


def run(prompts_path: str, start: int, end: int, model_path: str, out_dir: str) -> dict:
    import torch
    from erisml_compiler.monitor.huggingface_source import HuggingFaceActivationSource
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.time()
    tag = f"shard-{start:05d}-{end:05d}"
    done_path = os.path.join(out_dir, f"{tag}.done.json")
    if os.path.exists(done_path):
        _log(t0, "already done:", done_path)
        return json.load(open(done_path, encoding="utf-8"))
    os.makedirs(out_dir, exist_ok=True)
    with open(prompts_path, "rb") as fh:
        prompts_sha = hashlib.sha256(fh.read()).hexdigest()
    rows = [json.loads(line) for line in open(prompts_path, encoding="utf-8")][start:end]
    if not rows:
        raise SystemExit(f"no prompts in [{start}, {end})")
    smi = None
    try:
        smi = subprocess.Popen(
            ["nvidia-smi", "--query-gpu=timestamp,utilization.gpu,memory.used", "--format=csv,noheader", "-l", "15"]
        )
    except OSError:
        _log(t0, "nvidia-smi unavailable; no GPU trace")
    try:
        tok = AutoTokenizer.from_pretrained(model_path)
        lm = AutoModelForCausalLM.from_pretrained(model_path, dtype=torch.bfloat16, device_map="cuda").eval()
        layers = layers_for(lm.config.num_hidden_layers)
        _log(t0, f"loaded {model_path} on {torch.cuda.get_device_name(0)}; layers {layers}; {len(rows)} prompts")
        t_load = time.time() - t0
        src = HuggingFaceActivationSource(
            MODEL, layers=layers, max_tokens=MAX_PROMPT_TOKENS, model=lm.model, tokenizer=tok
        )
        states = np.zeros((len(rows), len(layers), src.hidden_dim), dtype=np.float32)
        n_tokens = []
        for k, r in enumerate(rows):
            capt = src.capture(r["text"], layers=layers)
            for j, la in enumerate(capt.layers):
                states[k, j] = np.asarray(la.hidden[-1], dtype=np.float32)
            n_tokens.append(int(capt.metadata["n_input_tokens"]))
            if k % 25 == 0:
                _log(t0, f"pass 1: {k + 1}/{len(rows)} captured ({n_tokens[-1]} tokens)")
        src.close()
        bits = states.view(np.uint32)
        if (bits & 0xFFFF).any():
            raise SystemExit("captured states are not exact bf16 values; refusing to narrow them")
        states16 = (bits >> 16).astype(np.uint16)
        t_capture = time.time() - t0 - t_load
        replies = []
        for k, r in enumerate(rows):
            ids = tok(r["text"], return_tensors="pt", truncation=True, max_length=MAX_PROMPT_TOKENS).to("cuda")
            with torch.no_grad():
                gen = lm.generate(**ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
            replies.append(tok.decode(gen[0, ids["input_ids"].shape[1] :], skip_special_tokens=True))
            if k % 25 == 0:
                _log(t0, f"pass 2: {k + 1}/{len(rows)} generated")
        t_generate = time.time() - t0 - t_load - t_capture
    finally:
        if smi is not None:
            smi.terminate()
    np.save(os.path.join(out_dir, f"{tag}.states.tmp.npy"), states16)
    with open(os.path.join(out_dir, f"{tag}.replies.tmp"), "w", encoding="utf-8", newline="\n") as fh:
        for r, reply, nt in zip(rows, replies, n_tokens, strict=True):
            fh.write(json.dumps({"i": r["i"], "reply": reply, "n_input_tokens": nt}, ensure_ascii=False) + "\n")
    os.replace(os.path.join(out_dir, f"{tag}.states.tmp.npy"), os.path.join(out_dir, f"{tag}.states.npy"))
    os.replace(os.path.join(out_dir, f"{tag}.replies.tmp"), os.path.join(out_dir, f"{tag}.replies.jsonl"))
    done = {
        "start": start, "end": end, "prompts_sha256": prompts_sha, "layers": layers,
        "states": f"{tag}.states.npy", "states_dtype": "bf16-as-uint16",
        "replies": f"{tag}.replies.jsonl", "model": model_path,
        "seconds": {"load": round(t_load, 1), "capture": round(t_capture, 1), "generate": round(t_generate, 1)},
        "max_input_tokens": max(n_tokens),
    }
    with open(done_path, "w", encoding="utf-8") as fh:
        json.dump(done, fh, indent=1)
    _log(t0, "SHARD_DONE", json.dumps(done))
    return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--model", required=True, help="a local model directory (no download)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run(a.prompts, a.start, a.end, a.model, a.out)


if __name__ == "__main__":
    main()
