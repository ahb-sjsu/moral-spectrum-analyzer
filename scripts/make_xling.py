"""Translate the demo scenario base texts into the language mix (for cross-lingual invariance).

Writes data/xling/xling_texts.json: for each scenario, the English base + one translation per language.
Uses the NRP managed LLM (gpt-oss). Run once; the output is embedded under BGE-M3 and LaBSE on Atlas.
"""

from __future__ import annotations

import json
import os

from moral_spectrum.llm import NRPClient
from moral_spectrum.scenarios import SCENARIOS

LANGS = {"es": "Spanish", "ar": "Arabic", "zh": "Simplified Chinese", "hi": "Hindi", "sw": "Swahili"}


def main() -> None:
    c = NRPClient(model=os.environ.get("NRP_MODEL", "gpt-oss"))
    out = []
    for s in SCENARIOS:
        out.append({"id": s.id, "lang": "en", "text": s.base})
        for code, name in LANGS.items():
            t = c.translate(s.base, name)
            out.append({"id": s.id, "lang": code, "text": t})
            print(f"  {s.id:24s} {code}: {t[:56]}")
    d = os.path.join("data", "xling")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "xling_texts.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(out)} texts ({len(SCENARIOS)} scenarios × {1+len(LANGS)} languages)")


if __name__ == "__main__":
    main()
