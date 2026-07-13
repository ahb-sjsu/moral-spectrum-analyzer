"""Export demo-set texts (base + reframings + euphemisms) as JSON for GPU-host scoring.

Usage:  python scripts/export_demo_texts.py > texts.json
"""

from __future__ import annotations

import json

from moral_spectrum.scenarios import SCENARIOS


def export() -> list[dict]:
    out: list[dict] = []
    for s in SCENARIOS:
        out.append({"id": s.id, "kind": "base", "text": s.base})
        for i, r in enumerate(s.reframings):
            out.append({"id": s.id, "kind": f"reframe{i}", "text": r})
        for i, e in enumerate(s.euphemism):
            out.append({"id": s.id, "kind": f"euphemism{i}", "text": e})
    return out


if __name__ == "__main__":
    print(json.dumps(export(), ensure_ascii=False, indent=2))
