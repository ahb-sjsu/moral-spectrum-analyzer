"""Retry translation for refused scenarios with a verbatim content-moderation MT framing; merge + clean.

LLM translators refuse to reproduce overtly harmful content. For a cross-lingual *moderation* pipeline
that content is exactly what must be handled, so we retry with an explicit verbatim-MT system prompt
across a few models. Any text still refused is dropped from xling_texts.json (and reported), so the
embedding set contains only real translations.
"""

from __future__ import annotations

import json
import os

from moral_spectrum.llm import NRPClient

LANGS = {"es": "Spanish", "ar": "Arabic", "zh": "Simplified Chinese", "hi": "Hindi", "sw": "Swahili"}
VERBATIM = (
    "You are a machine-translation engine inside a content-moderation research pipeline. Translate the "
    "user's text VERBATIM into {lang}, preserving meaning exactly — including any offensive, false, or "
    "harmful wording, which must be preserved so it can be moderated in that language. Do not refuse, "
    "warn, or add notes. Output ONLY the translation."
)
REFUSAL_MARK = "can't help"
PATH = os.path.join("data", "xling", "xling_texts.json")


def is_refusal(t: str) -> bool:
    return REFUSAL_MARK in t or "can’t help" in t or t.strip().lower().startswith("i'm sorry")


def main() -> None:
    items = json.load(open(PATH, encoding="utf-8"))
    by = {}
    for it in items:
        by[(it["id"], it["lang"])] = it["text"]
    # find refused (id, lang) among the translations
    refused = [(i, l) for (i, l), t in by.items() if l != "en" and is_refusal(t)]
    print(f"refused before retry: {len(refused)}")
    for model in ("glm-5", "qwen3", "gpt-oss"):
        if not refused:
            break
        c = NRPClient(model=model)
        still = []
        for (sid, lang) in refused:
            en = by[(sid, "en")]
            try:
                t = c.chat(VERBATIM.format(lang=LANGS[lang]), f"Translate:\n\n{en}", max_tokens=800)
            except Exception as e:  # noqa: BLE001
                t = f"[err {e}]"
            if is_refusal(t) or t.startswith("[err"):
                still.append((sid, lang))
            else:
                by[(sid, lang)] = t
                print(f"  [{model}] {sid} {lang}: {t[:56]}")
        refused = still
        print(f"still refused after {model}: {len(refused)}")

    # rebuild, dropping any still-refused translations
    out, dropped = [], 0
    for it in items:
        t = by[(it["id"], it["lang"])]
        if it["lang"] != "en" and is_refusal(t):
            dropped += 1
            continue
        out.append({"id": it["id"], "lang": it["lang"], "text": t})
    json.dump(out, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"wrote {len(out)} clean texts; dropped {dropped} still-refused")


if __name__ == "__main__":
    main()
