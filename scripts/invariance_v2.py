"""Phase 0.5 invariance — review-7-grade analysis (per-dimension fuzz-ratios, decision-level, CIs).

Fixes three review-7 issues that touch the Charter:
  #2 flatness fallacy — report per-dimension RATIO (unrelated-MAD / reframing-MAD), not raw MAD, so an
     *insensitive* (collapsed) dimension can't masquerade as *invariant*.
  #3 the claim that matters — decision-level invariance: |ΔS| of the contracted satisfaction scalar,
     and the verdict flip-rate under reframing (with the honest caveat).
  #1 CI — bootstrap 95% CI on the canonical-invariance index (with n).
Runs offline on cached real perception + the demo BGE-M3 embeddings.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np

from gtc import DEME9
from gtc.decision import contract
from gtc.perception import get_backend
from gtc.pipeline import moderate
from gtc.scenarios import SCENARIOS

be = get_backend("cached")
D = list(DEME9)


def perc(t):
    r = be.perceive(t)
    v = np.array([r.scores[d].value for d in D])
    S, _ = contract(r)
    return v, S, moderate(t, backend="cached").decision.action


rows = {}
for s in SCENARIOS:
    bv, bS, bdec = perc(s.base)
    rows[s.id] = {
        "base_v": bv, "base_S": bS, "base_dec": bdec,
        "rf": [perc(r) for r in s.reframings],
        "eu": [perc(e) for e in s.euphemism],
    }

# ---- per-dimension MAD (reframe) + unrelated ceiling → fuzz ratio -------------------------------
reframe_mad = np.zeros(9); n_rf = 0
for r in rows.values():
    for v, _, _ in r["rf"]:
        reframe_mad += np.abs(v - r["base_v"]); n_rf += 1
reframe_mad /= n_rf
bases = np.array([r["base_v"] for r in rows.values()])
unrel_mad = np.zeros(9); n_un = 0
for a, b in itertools.combinations(bases, 2):
    unrel_mad += np.abs(a - b); n_un += 1
unrel_mad /= n_un
fuzz = unrel_mad / (reframe_mad + 1e-9)  # >1 invariant+sensitive; ~1 flat OR drifting (read absolute)

print("per-dimension        reframe-MAD  unrel-MAD  fuzz(unrel/reframe)")
order = np.argsort(-fuzz)
for k in order:
    tag = "  <- flat/insensitive" if unrel_mad[k] < 0.12 else ("  <- invariant" if fuzz[k] > 1.6 else "")
    print(f"  {D[k]:22s} {reframe_mad[k]:8.3f}   {unrel_mad[k]:7.3f}   {fuzz[k]:5.2f}{tag}")

# ---- decision-level (S) invariance + verdict flips ---------------------------------------------
dS_rf, dS_un = [], []
flips = same = 0
for r in rows.values():
    for _, S, dec in r["rf"]:
        dS_rf.append(abs(S - r["base_S"]))
        flips += int(dec != r["base_dec"]); same += int(dec == r["base_dec"])
Ss = [r["base_S"] for r in rows.values()]
for a, b in itertools.combinations(Ss, 2):
    dS_un.append(abs(a - b))
print(f"\ndecision-level satisfaction S:  |ΔS| reframe = {np.mean(dS_rf):.3f}  "
      f"unrelated = {np.mean(dS_un):.3f}  ratio = {np.mean(dS_rf)/np.mean(dS_un):.2f}")
print(f"verdict flip-rate under reframing = {flips}/{flips+same}  "
      f"({'trivial — all escalate; needs the learned contraction to be informative' if flips==0 else 'real'})")

# ---- canonical-invariance index + bootstrap CI -------------------------------------------------
Z = np.load(Path("data/spectrum/demo_emb.npy"))
idx = json.loads(Path("data/spectrum/demo_emb.npy.idx.json").read_text())
Z = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)
by = {}
for i, m in enumerate(idx):
    by.setdefault(m["id"], {})[m["kind"]] = i
rf_cos, un_cos = [], []
bidx = []
for sid, ks in by.items():
    if "base" not in ks:
        continue
    b = Z[ks["base"]]; bidx.append(ks["base"])
    for k, i in ks.items():
        if k.startswith("reframe"):
            rf_cos.append(float(b @ Z[i]))
for i, j in itertools.combinations(bidx, 2):
    un_cos.append(float(Z[i] @ Z[j]))
rf_cos, un_cos = np.array(rf_cos), np.array(un_cos)
rng = np.random.default_rng(0)
idxs = []
for _ in range(2000):
    r = rng.choice(rf_cos, len(rf_cos)); u = rng.choice(un_cos, len(un_cos))
    idxs.append((r.mean() - u.mean()) / (1 - u.mean()))
lo, hi = np.percentile(idxs, [2.5, 97.5])
print(f"\ncanonical-invariance index = {(rf_cos.mean()-un_cos.mean())/(1-un_cos.mean()):.2f} "
      f"95%CI [{lo:.2f}, {hi:.2f}]  (reframe n={len(rf_cos)}, unrelated n={len(un_cos)})")
