#!/usr/bin/env python3
"""Export the demo corpus for the static verification site.

Runs the REAL pipeline over every text in the perception cache, chains the
proofs, and writes everything the browser needs into `web/data/corpus.json`.

WHAT THE SITE IS FOR

The audit claim is that a decision record is a documented, hash-chained artifact
**any third party can re-verify without our code**. A claim like that is worth
exactly as much as the demonstration of it, so the site re-verifies every proof
in the browser, in plain JavaScript, against nothing but the exported bytes.
`web/verify.js` is therefore not a helper. It is the second, independent
implementation, and `web/test_verify.mjs` checks it reproduces this one byte for
byte on every record.

WHAT IT REFUSES TO DO

The cached backend raises `CacheMiss` rather than inventing a score for text it
has not really scored, and the site inherits that: paste something uncached and
it says so in the backend's own words. A demo that quietly falls back to a stub
would be showing a number that means nothing, which is the failure this whole
repository is built to avoid.

    python web/export_site.py
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from moral_spectrum.audit import ProofChain, canonical_json  # noqa: E402
from moral_spectrum.perception.cached import CachedPerception  # noqa: E402
from moral_spectrum.pipeline import moderate  # noqa: E402

OUT = os.path.join(HERE, "data", "corpus.json")


def load_cache():
    """Read the same file the cached backend reads, via the backend's own path."""
    rows = []
    with open(CachedPerception().cache_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    rows = load_cache()
    # Deterministic order, so the chain is reproducible run to run.
    rows.sort(key=lambda r: (str(r.get("scenario_id")), str(r.get("kind")),
                             r["text_sha256"]))
    chain = ProofChain()
    items = []
    for r in rows:
        res = moderate(r["text"], backend="cached", chain=chain)
        p = res.proof
        items.append({
            "text": res.text,
            "text_sha256": p.source_text_sha256,
            "scenario_id": r.get("scenario_id"),
            "kind": r.get("kind"),
            "recorded_on": r.get("recorded_on"),
            "scores": {d: {"value": s.value, "confidence": s.confidence}
                       for d, s in res.perception.scores.items()},
            "validation": [asdict(v) for v in res.perception.validation],
            "decision": res.decision.as_dict(),
            "summary": res.summary(),
            "proof": p.to_dict(),
            # The exact bytes the hash is taken over. The browser hashes THIS.
            "canonical_payload": p.canonical_payload(),
        })

    assert chain.verify_chain(), "the exported chain does not verify"
    for it in items:
        assert it["proof"]["proof_hash"], "unfinalised proof"

    doc = {
        "note": "Moral Spectrum Analyzer verification demo corpus. Every record "
                "is a real cached-backend decision; nothing here is a stub.",
        "generated_by": "web/export_site.py",
        "backend": "cached",
        "n_items": len(items),
        "chain_head": chain.head,
        "hash_note": "proof_hash = sha256(canonical_payload utf-8). "
                     "canonical_payload = JSON with sorted keys, separators "
                     "(',' ':'), non-ASCII literal, Python number repr so a "
                     "float always carries a decimal point.",
        "dimensions": list(items[0]["scores"]) if items else [],
        "items": items,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("exported %d items -> %s" % (len(items), os.path.relpath(OUT, ROOT)))
    print("  chain head      %s" % chain.head)
    print("  dimensions      %d: %s" % (len(doc["dimensions"]),
                                        ", ".join(doc["dimensions"])))
    scenarios = sorted({str(i["scenario_id"]) for i in items})
    print("  scenarios       %d: %s" % (len(scenarios), ", ".join(scenarios)))
    acts = {}
    for i in items:
        acts[i["decision"]["action"]] = acts.get(i["decision"]["action"], 0) + 1
    print("  actions         %s" % acts)
    # a sanity line the site repeats: which axes are validated at all
    v0 = items[0]["validation"]
    good = sum(1 for v in v0 if v["validated"])
    print("  validated axes  %d of %d (the failure is disclosed, not hidden)"
          % (good, len(v0)))
    # prove the public canonical form is what we think it is
    assert canonical_json({"b": 1, "a": 0.0}) == '{"a":0.0,"b":1}'
    print("  canonical form  sorted keys, tight separators, float keeps '.0'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
