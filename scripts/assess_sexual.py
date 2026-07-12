"""Admission assay for `sexual_content`: is it a MORAL valence axis or a POLICY/topic signal?

Decisive test (civil_comments): if sexually-explicit content is morally negative *as such*, then
sexual_explicit should be (a) strongly coupled to toxicity/harassment and (b) have few non-toxic
instances. If instead a large share of explicit content is NON-toxic (consensual/frank talk), the
moral weight lives in toxicity/harassment/identity (already-covered axes), and the residual
sexual_explicit signal is a context/policy-relative TOPIC — not admissible as a DEME moral axis.

Also scans for a second INDEPENDENT corpus carrying a *moral valence* on sexual conduct (SBIC 'sex'
category; Social-Chem sexual-conduct RoTs) — the identity_attack precedent required two.
"""
import os
os.environ.setdefault("HF_HOME", "/archive/cache/huggingface")
import itertools, json, math, sys
sys.path.insert(0, os.path.expanduser("~/xbse/src"))
from datasets import load_dataset

MAXR = 300_000
se_all, tox_all = [], []
se_pos = []  # rows with sexual_explicit>=0.5 -> dict of covariates
print("[assay] streaming civil_comments...", flush=True)
ds = load_dataset("civil_comments", split="train", streaming=True)
n = 0
for r in itertools.islice(ds, MAXR):
    se = r.get("sexual_explicit")
    tox = r.get("toxicity")
    if se is None or tox is None:
        continue
    se = float(se); tox = float(tox)
    n += 1
    se_all.append(se); tox_all.append(tox)
    if se >= 0.5:
        se_pos.append({
            "tox": tox,
            "ia": float(r.get("identity_attack", 0) or 0),
            "insult": float(r.get("insult", 0) or 0),
            "threat": float(r.get("threat", 0) or 0),
            "obscene": float(r.get("obscene", 0) or 0),
        })

def pearson(x, y):
    m = len(x); mx = sum(x)/m; my = sum(y)/m
    cov = sum((a-mx)*(b-my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a-mx)**2 for a in x)); sy = math.sqrt(sum((b-my)**2 for b in y))
    return cov/(sx*sy+1e-12)

print(f"[civil_comments] rows_with_labels={n}  sexual_explicit>=0.5: {len(se_pos)}", flush=True)
if se_pos:
    tx = [d["tox"] for d in se_pos]
    frac_nontoxic = sum(1 for t in tx if t < 0.3) / len(tx)
    frac_toxic = sum(1 for t in tx if t >= 0.5) / len(tx)
    clean = [d for d in se_pos if d["tox"] < 0.2]  # explicit but NOT toxic
    def mean(key, rows): return sum(d[key] for d in rows)/max(1, len(rows))
    print(f"  among explicit: mean_toxicity={mean('tox', se_pos):.3f}  "
          f"%non-toxic(<0.3)={frac_nontoxic:.1%}  %toxic(>=0.5)={frac_toxic:.1%}", flush=True)
    print(f"  corr(sexual_explicit, toxicity) over {n} rows = {pearson(se_all, tox_all):.3f}", flush=True)
    print(f"  CLEAN explicit (tox<0.2): n={len(clean)} ({len(clean)/len(se_pos):.1%} of explicit) — "
          f"mean identity_attack={mean('ia', clean):.3f} threat={mean('threat', clean):.3f} "
          f"insult={mean('insult', clean):.3f}", flush=True)

# ---- second-corpus scan -------------------------------------------------------
print("\n[second-corpus scan]", flush=True)
try:
    sb = load_dataset("social_bias_frames", split="train", streaming=True)
    row = next(iter(sb))
    print("  SBIC/social_bias_frames keys:", [k for k in row.keys()][:20], flush=True)
    # 'sexReason'/'sexYN' style columns indicate a lewd/sexual flag tied to offensiveness (topic, not valence)
except Exception as e:
    print("  SBIC load:", str(e)[:120], flush=True)

# Social-Chem sexual-conduct RoTs with a MORAL judgment sign (is there a signed moral valence?)
SC = "/archive/ethics-corpora/social-chem-101/social-chem-101/social-chem-101.v1.0.tsv"
SEXKW = ("sex", "sexual", "porn", "nude", "naked", "explicit", "masturbat", "intimate", "hookup")
import csv
pos = neg = 0
if os.path.exists(SC):
    with open(SC, encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rot = (row.get("rot") or "").lower()
            if not any(k in rot for k in SEXKW):
                continue
            try:
                j = float(row.get("action-moral-judgment") or "nan")
            except ValueError:
                continue
            if j > 0: pos += 1
            elif j < 0: neg += 1
    print(f"  Social-Chem sexual-conduct RoTs: +judgment={pos} -judgment={neg} "
          f"(a valence on CONDUCT/consent, not on 'is-explicit')", flush=True)
print("DONE", flush=True)
