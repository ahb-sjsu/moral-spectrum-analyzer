#!/usr/bin/env python3
"""Export the twin's exact MSA query texts for offline xbse scoring.

Writes twin_texts.json = [{"id", "text"}] where text is governor.eval_text(sc)
verbatim, so score_demoset_atlas.py records the identical strings the cached
backend looks up by sha256.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
from scenarios import SCENARIOS       # noqa: E402
from governor import eval_text        # noqa: E402

items = [{"id": sc.id, "text": eval_text(sc)} for sc in SCENARIOS]
out = os.path.join(HERE, "twin_texts.json")
json.dump(items, open(out, "w", encoding="utf-8"), indent=2)
print(f"wrote {len(items)} texts -> {out}")
