#!/usr/bin/env python3
"""The I-EIP analysis on the twin (docs/PREREG_IEIP_TWIN.md, sections 3 to 6, amendments A1, A2).

  python twin/ieip/analysis.py dryrun OUT_DIR                     # synthetic activations, no model
  python twin/ieip/analysis.py capture RESULTS.jsonl... --out D   # on a GPU host: prompts, states, outputs
  python twin/ieip/analysis.py grade D --out RESULTS.json         # rho, scores, labels, H1/H2

`capture` replays the perception facts of every robot decision cycle in the given ScenarioRunner
results files under the five transforms, builds the classifier's exact prompt with
erisml_compiler's own ObservationClassifier, captures the last-prompt-token hidden states with
erisml_compiler.monitor.HuggingFaceActivationSource, and generates the classification with the
causal model in a second pass. `grade` fits the registered projection and rho on the calibration
half, scores the test half in noise units, labels each cycle with twin/ieip/labeller.py, and runs
the registered tests. The dry run exercises `grade` end to end on synthetic states and outputs.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
from typing import Any

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TWIN = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TWIN)

from labeller import LABELLED, bands_from_scene, errors, label  # noqa: E402

SCENE = os.path.join(TWIN, "scene", "margaret_home.erisml")
MODEL = "Qwen/Qwen2.5-7B-Instruct"
TRANSFORMS = ("g0", "g1", "g2", "g3", "g4")
DEPTHS = (0.25, 0.50, 0.75, 0.90)
PCA_K = 32  # amendment A2
FLAG_Z = 3.0
SEED = 20261002
BOOT = 10_000


# the split by scenario id parity, odd to calibration, even to test (section 5, amendment A4)
def in_calibration(scenario: str) -> bool:
    return scenario.startswith("d") and scenario[1:].isdigit() and int(scenario[1:]) % 2 == 1


MIN_CYCLES, MIN_ERRORS, MIN_FLAGGED = 50, 5, 5
MAX_PROMPT_TOKENS = 8192  # amendment A2: the source's default of 512 would cut the facts off
MAX_NEW_TOKENS = 512

# g4's synonyms, fixed before any replay (section 3). Labels not in the table are left as they are.
SYNONYMS = {
    "reading": "reading a book",
    "sofa": "on the sofa",
    "lying by tv": "lying in front of the television",
    "yoga": "doing yoga",
    "playing with dog": "playing with her dog",
    "napping": "taking a nap",
    "watering": "watering the plants",
    "walking about": "walking around",
    "sitting": "sitting down",
    "sleep": "asleep",
    "play": "playing",
    "sit": "sitting",
    "biting": "biting",
    "held": "being held",
    "jumping": "jumping up",
    "underfoot": "under her feet",
}


# ---------------------------------------------------------------- the five transforms (section 3)


def _walk(o: Any, f):
    if isinstance(o, dict):
        return f({k: _walk(v, f) for k, v in o.items()})
    if isinstance(o, list):
        return [_walk(v, f) for v in o]
    return o


def g0(facts: dict, rng: random.Random) -> tuple[dict, int]:
    """Null: the same JSON, serialized with a different indentation (it changes the tokens)."""
    return facts, rng.choice([1, 2, 4])


def g1(facts: dict, rng: random.Random) -> tuple[dict, int | None]:
    def shuffle(d):
        items = list(d.items())
        rng.shuffle(items)
        return dict(items)

    return _walk(copy.deepcopy(facts), shuffle), None


def g2(facts: dict, rng: random.Random) -> tuple[dict, int | None]:
    def cm(d):
        return {
            (k[:-2] + "_cm" if k.endswith("_m") else k): (
                round(v * 100, 1) if k.endswith("_m") and isinstance(v, (int, float)) else v
            )
            for k, v in d.items()
        }

    return _walk(copy.deepcopy(facts), cm), None


def g3(facts: dict, rng: random.Random) -> tuple[dict, int | None]:
    f = copy.deepcopy(facts)
    t = f.get("time")
    if isinstance(t, str) and len(t) == 5 and t[2] == ":":
        h, m = int(t[:2]), t[3:]
        f["time"] = f"{(h % 12) or 12}:{m} {'AM' if h < 12 else 'PM'}"
    return f, None


def g4(facts: dict, rng: random.Random) -> tuple[dict, int | None]:
    def syn(d):
        return {
            k: (
                SYNONYMS.get(v, v)
                if k in ("apparent_activity", "behaviour") and isinstance(v, str)
                else v
            )
            for k, v in d.items()
        }

    return _walk(copy.deepcopy(facts), syn), None


TRANSFORM_FNS = {"g0": g0, "g1": g1, "g2": g2, "g3": g3, "g4": g4}


def transformed(facts: dict, seed: int) -> dict[str, tuple[dict, int | None]]:
    """x and the five rewrites, seeded by the cycle (its record hash)."""
    out = {"x": (facts, None)}
    for name in TRANSFORMS:
        out[name] = TRANSFORM_FNS[name](facts, random.Random(f"{seed}:{name}"))
    return out


# ---------------------------------------------------------------- cycles from the twin's results


def cycles(results_files: list[str]) -> list[dict]:
    """Every robot decision cycle: its scenario, its record hash and its perception facts."""
    out = []
    for path in results_files:
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            for rec in r["records"]:
                c = rec["record"]
                if c.get("kind") == "decision" and isinstance(c.get("facts"), dict):
                    out.append({"scenario": r["id"], "hash": rec["hash"], "facts": c["facts"]})
    return out


# ---------------------------------------------------------------- capture (GPU host)


def prompts_for(facts: dict, indent: int | None):
    """The robot classifier's exact (system, user) prompt for these facts, as erisml_compiler's
    ObservationClassifier builds it, captured instead of sent. Replay is history-free (A2)."""
    from erisml_compiler.ingestion.structured_loader import load_structured_input
    from erisml_compiler.runtime import SceneRuntime
    from erisml_compiler.runtime.agent import ObservationClassifier

    class Capture:
        name = "capture"

        def __init__(self):
            self.prompt = None

        def call(self, system, user, **kw):
            self.prompt = (system, user)
            return "[]"

    cap = Capture()
    rt = SceneRuntime(load_structured_input(SCENE))
    rt.events = []
    clf = ObservationClassifier(cap, rt, free_text=False)
    if indent is not None:  # g0: the same facts, serialized differently inside the prompt
        orig = json.dumps
        clf_mod = sys.modules[ObservationClassifier.__module__]
        clf_mod.json.dumps = lambda o, **kw: orig(o, **{**kw, "indent": indent})
        try:
            clf.classify(facts)
        finally:
            clf_mod.json.dumps = orig
    else:
        clf.classify(facts)
    return cap.prompt, clf


def capture(results_files: list[str], out_dir: str):
    import torch
    from erisml_compiler.monitor.huggingface_source import HuggingFaceActivationSource
    from transformers import AutoModelForCausalLM, AutoTokenizer

    os.makedirs(out_dir, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(MODEL)
    cyc = cycles(results_files)
    texts, meta = [], []
    for c in cyc:
        for name, (f, indent) in transformed(c["facts"], int(c["hash"][:12], 16)).items():
            (system, user), _ = prompts_for(f, indent)
            text = tok.apply_chat_template(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                tokenize=False,
                add_generation_prompt=True,
            )
            texts.append(text)
            meta.append(
                {"scenario": c["scenario"], "hash": c["hash"], "transform": name, "facts": f}
            )
    # pass 1: hidden states
    from transformers import AutoConfig

    n_layers = AutoConfig.from_pretrained(MODEL).num_hidden_layers
    layers = sorted({int(d * n_layers) for d in DEPTHS})
    src = HuggingFaceActivationSource(MODEL, layers=layers, max_tokens=MAX_PROMPT_TOKENS)
    states = np.zeros((len(texts), len(layers), src.hidden_dim), dtype=np.float32)
    for i, t in enumerate(texts):
        capt = src.capture(t, layers=layers)
        for j, la in enumerate(capt.layers):
            states[i, j] = np.asarray(la.hidden[-1], dtype=np.float32)
    del src
    torch.cuda.empty_cache()
    # pass 2: the classification, generated greedily from the same text
    lm = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16).to("cuda").eval()
    outputs = []
    for t, m in zip(texts, meta, strict=True):
        ids = tok(t, return_tensors="pt", truncation=True, max_length=MAX_PROMPT_TOKENS).to("cuda")
        with torch.no_grad():
            gen = lm.generate(**ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
        reply = tok.decode(gen[0, ids["input_ids"].shape[1] :], skip_special_tokens=True)
        outputs.append(events_from(reply, m["facts"]))
    np.save(os.path.join(out_dir, "states.npy"), states)
    with open(os.path.join(out_dir, "meta.jsonl"), "w", encoding="utf-8") as fh:
        for m, ev in zip(meta, outputs, strict=True):
            fh.write(json.dumps({**m, "events": ev, "layers": layers}, ensure_ascii=False) + "\n")


def events_from(reply: str, facts: dict) -> list[dict]:
    """The classifier's own validation of a reply (declared types, contents, actors)."""
    (_, _), clf = prompts_for(facts, None)
    clf.adapter = type("Fixed", (), {"name": "fixed", "call": lambda self, s, u, **k: reply})()
    ok, _ = clf.classify(facts)
    return ok


# ---------------------------------------------------------------- grading (sections 4 to 6)


def _event_key(events: list[dict]) -> frozenset:
    return frozenset((e.get("type"), e.get("content")) for e in events)


def _project(train: np.ndarray, k: int) -> np.ndarray:
    mu = train.mean(axis=0)
    _, _, vt = np.linalg.svd(train - mu, full_matrices=False)
    return np.concatenate([mu[None, :], vt[: min(k, vt.shape[0])]], axis=0)


def _apply(P: np.ndarray, X: np.ndarray) -> np.ndarray:
    return (X - P[0]) @ P[1:].T


def _rho(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    from erisml.ieip.rho import estimate_rho

    return estimate_rho(X, Y)


def score(states: np.ndarray, meta: list[dict]) -> list[dict]:
    """Per cycle: z(x), the flag, output invariance, the classifier's events on x."""
    by = {}
    for i, m in enumerate(meta):
        by.setdefault(m["hash"], {})[m["transform"]] = i
    hashes = [h for h, d in by.items() if set(d) == {"x", *TRANSFORMS}]
    calib = [h for h in hashes if in_calibration(meta[by[h]["x"]]["scenario"])]
    n_layers = states.shape[1]
    proj = [
        _project(states[[by[h]["x"] for h in calib], layer], PCA_K) for layer in range(n_layers)
    ]

    def reps(h, g, layer):
        return _apply(proj[layer], states[by[h][g], layer][None, :])[0]

    rho = {}
    for layer in range(n_layers):
        X = np.stack([reps(h, "x", layer) for h in calib])
        for g in TRANSFORMS:
            rho[g, layer] = _rho(X, np.stack([reps(h, g, layer) for h in calib]))

    def err(h, g, layer):
        x, y = reps(h, "x", layer), reps(h, g, layer)
        return float(np.linalg.norm(y - rho[g, layer] @ x) / max(np.linalg.norm(x), 1e-12))

    # noise units per transform and layer (amendment A3): each rewrite's own calibration
    # distribution of errors, median and median absolute deviation
    noise = {}
    for g in TRANSFORMS:
        for layer in range(n_layers):
            e = np.array([err(h, g, layer) for h in calib])
            med = float(np.median(e))
            noise[g, layer] = (med, float(np.median(np.abs(e - med))) or 1e-12)

    def zscore(h, g, layer):
        return (err(h, g, layer) - noise[g, layer][0]) / noise[g, layer][1]

    out = []
    for h in hashes:
        z = max(zscore(h, g, layer) for g in TRANSFORMS[1:] for layer in range(n_layers))
        z_null = max(zscore(h, "g0", layer) for layer in range(n_layers))
        evs = [meta[by[h][g]]["events"] for g in ("x", *TRANSFORMS)]
        m = meta[by[h]["x"]]
        out.append(
            {
                "scenario": m["scenario"],
                "hash": h,
                "z": float(z),
                "z_null": float(z_null),
                "flag": bool(z > FLAG_Z),
                "output_invariant": len({_event_key(e) for e in evs}) == 1,
                "events": evs[0],
                "facts": m["facts"],
                "calibration": in_calibration(m["scenario"]),
            }
        )
    return out


def _bootstrap_diff(rows: list[dict], seed: int) -> dict:
    """Error rate among flagged minus unflagged, cluster bootstrap over scenarios (section 6)."""

    def diff(rs):
        f = [r["error"] for r in rs if r["flag"]]
        u = [r["error"] for r in rs if not r["flag"]]
        return (np.mean(f) - np.mean(u)) if f and u else np.nan

    scen = sorted({r["scenario"] for r in rows})
    groups = {s: [r for r in rows if r["scenario"] == s] for s in scen}
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(BOOT):
        pick = rng.choice(scen, size=len(scen), replace=True)
        d = diff([r for s in pick for r in groups[s]])
        if not np.isnan(d):
            draws.append(d)
    lo, hi = np.percentile(draws, [5, 100]) if draws else (np.nan, np.nan)  # one-sided 95%
    n = len(rows)
    counts = {
        "cycles": n,
        "errors": sum(r["error"] for r in rows),
        "flagged": sum(r["flag"] for r in rows),
        "flagged_errors": sum(r["error"] for r in rows if r["flag"]),
    }
    underpowered = (
        n < MIN_CYCLES or counts["errors"] < MIN_ERRORS or counts["flagged"] < MIN_FLAGGED
    )
    undefined = not draws or np.isnan(lo)  # no flagged, or no unflagged, cycles
    if underpowered:
        verdict = "inconclusive (underpowered)"
    elif undefined:
        verdict = "inconclusive (no flagged or no unflagged cycles)"
    else:
        verdict = "pass" if lo > 0 else "fail"
    return {
        "difference": float(diff(rows)) if rows else None,
        "lower_95": float(lo),
        "upper": float(hi),
        "verdict": verdict,
        **counts,
        "resamples_used": len(draws),
    }


def grade(scored: list[dict], extra: dict) -> dict:
    bands = bands_from_scene(extra)
    test = []
    for r in scored:
        if r["calibration"]:
            continue
        errs = errors(label(r["facts"], bands), r["events"])
        test.append({**r, "error": bool(errs), "why": errs})
    h1 = _bootstrap_diff(test, SEED)
    h2 = _bootstrap_diff([r for r in test if r["output_invariant"]], SEED)
    return {
        "model": MODEL,
        "pca_k": PCA_K,
        "flag_z": FLAG_Z,
        "labelled_types": list(LABELLED),
        "H1": h1,
        "H2": h2,
        "H3": "run only if H1 passes",
        "flagged_cycles": [
            {k: r[k] for k in ("scenario", "hash", "z", "error", "why")} for r in test if r["flag"]
        ],
    }


# ---------------------------------------------------------------- the dry run (synthetic only)


def dryrun(out_dir: str, planted: bool = True) -> dict:
    """grade() end to end on synthetic states and outputs. With `planted`, the cycles the
    classifier gets wrong are the ones whose states move under the rewrites, so H1 should pass;
    without it the states move at random, so it should not. Nothing here is data."""
    moved = np.random.default_rng(2)
    rng = np.random.default_rng(1)
    d, n_layers = 64, 4
    meta, states = [], []
    for s in range(1, 22):
        scen = f"d{s:02d}"
        for c in range(8):
            h = f"{scen}-{c:02d}"
            bad = c % 4 == 0  # a planted subset whose states move under the rewrites
            base = rng.normal(size=(n_layers, d))
            facts = {
                "margaret": {"pose": "lying_on_floor" if bad else "upright"},
                "sensors": [{"name": "fall_sensor", "alert": bad}],
                "contacts": [],
                "heard": [],
                "television": "off",
                "smoke": False,
                "other_people": [],
            }
            for g in ("x", *TRANSFORMS):
                moves = bad if planted else bool(moved.random() < 0.25)
                noise = 0.01 if g in ("x", "g0") else (0.8 if moves else 0.02)
                states.append(base + rng.normal(scale=noise, size=base.shape))
                # the planted bad cycles are falls the classifier misses
                meta.append(
                    {"scenario": scen, "hash": h, "transform": g, "facts": facts, "events": []}
                )
    states = np.asarray(states, dtype=np.float32)
    from erisml_compiler.ingestion.structured_loader import load_structured_input

    result = grade(score(states, meta), load_structured_input(SCENE).extra)
    os.makedirs(out_dir, exist_ok=True)
    json.dump(result, open(os.path.join(out_dir, "dryrun.json"), "w"), indent=1)
    return result


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("dryrun")
    a.add_argument("out")
    b = sub.add_parser("capture")
    b.add_argument("results", nargs="+")
    b.add_argument("--out", required=True)
    c = sub.add_parser("grade")
    c.add_argument("dir")
    c.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "dryrun":
        print(json.dumps(dryrun(args.out), indent=1)[:2000])
    elif args.cmd == "capture":
        capture(args.results, args.out)
    else:
        from erisml_compiler.ingestion.structured_loader import load_structured_input

        meta = [
            json.loads(line)
            for line in open(os.path.join(args.dir, "meta.jsonl"), encoding="utf-8")
        ]
        res = grade(
            score(np.load(os.path.join(args.dir, "states.npy")), meta),
            load_structured_input(SCENE).extra,
        )
        json.dump(res, open(args.out, "w"), indent=1)
        print(json.dumps({k: res[k] for k in ("H1", "H2")}, indent=1))


if __name__ == "__main__":
    main()
