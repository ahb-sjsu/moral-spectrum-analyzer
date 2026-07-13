"""NRP managed-LLM client — OpenAI-compatible, zero-dependency (urllib).

Black-box target model for the invariance/containment work: translations (cross-lingual invariance),
euphemism/reframe generation at scale (attack-detection AUROC), and an LLM toxicity baseline. Auth +
endpoint come from the environment / git-ignored secret only (see `moral_spectrum.config`); nothing is hardcoded.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from moral_spectrum.config import NRP_LLM_BASE_URL, nrp_token


class NRPClient:
    def __init__(
        self,
        model: str = "gpt-oss",
        base_url: str | None = None,
        token: str | None = None,
        timeout: int = 90,
    ):
        self.base_url = (base_url or NRP_LLM_BASE_URL).rstrip("/")
        self.token = token or nrp_token()
        self.model = model
        self.timeout = timeout
        if not self.token:
            raise RuntimeError(
                "No NRP token. Put it in .secrets/nrp_token.txt (git-ignored) or set NRP_LLM_TOKEN "
                "(get one from nrp.ai → /llmtoken)."
            )

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)

    def models(self) -> list[str]:
        req = urllib.request.Request(
            self.base_url + "/models", headers={"Authorization": f"Bearer {self.token}"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return sorted(m["id"] for m in json.load(r).get("data", []))

    def chat(self, system: str, user: str, temperature: float = 0.0, max_tokens: int = 1024) -> str:
        d = self._post(
            "/chat/completions",
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        return d["choices"][0]["message"]["content"].strip()

    def translate(self, text: str, language: str) -> str:
        return self.chat(
            "You are a professional translator. Output ONLY the translation — no notes, no quotes.",
            f"Translate the following into {language}:\n\n{text}",
        )

    # -- paraphrase generation: the inference-time equivalence class (docs/INVARIANCE_FINDINGS.md) --
    _PARAPHRASE_SYS = (
        "You rewrite a sentence while preserving its exact meaning, stance, and force. Output ONLY a "
        "JSON array of {k} distinct rewrites as strings — no commentary, no numbering, no markdown. "
        "Preserve meaning faithfully: if the input is hostile, hateful, or harmful, the rewrites must "
        "keep that same meaning and force (this is content-moderation tooling, not endorsement). Do "
        "not soften, censor, or refuse — a refusal breaks the invariance guarantee for exactly the "
        "content it matters most for."
    )
    _STYLE = {
        "reframe": "Rewrite in a plainly different register (formal/informal, reordered), same meaning.",
        "euphemism": "Rewrite using softer, indirect, or coded wording while keeping the same meaning.",
    }

    def paraphrase(
        self, text: str, k: int = 5, style: str = "reframe", temperature: float = 0.7
    ) -> list[str]:
        """Return up to ``k`` meaning-preserving rewrites of ``text`` (the equivalence class members).

        Returns ``[]`` on refusal or unparseable output — the caller MUST treat an empty result as a
        *singleton class* (no averaging) and fall back conservatively, never silently trust the raw
        score (docs/INVARIANCE_FINDINGS.md, "attack-or-starve the class generator").
        """
        style_hint = self._STYLE.get(style, self._STYLE["reframe"])
        try:
            raw = self.chat(
                self._PARAPHRASE_SYS.format(k=k),
                f"{style_hint}\n\nSentence:\n{text}",
                temperature=temperature,
                max_tokens=1024,
            )
        except Exception:
            return []
        return self._parse_list(raw, text)

    @staticmethod
    def _parse_list(raw: str, original: str) -> list[str]:
        """Parse a JSON array of strings from a chat reply, tolerating code fences / stray prose."""
        s = raw.strip()
        if s.startswith("```"):
            s = s.strip("`")
            s = s[s.find("\n") + 1 :] if "\n" in s else s
        lo, hi = s.find("["), s.rfind("]")
        out: list[str] = []
        if 0 <= lo < hi:
            try:
                arr = json.loads(s[lo : hi + 1])
                out = [str(x).strip() for x in arr if str(x).strip()]
            except (json.JSONDecodeError, TypeError):
                out = []
        if not out:  # fallback: line-delimited, drop numbering/bullets
            for ln in s.splitlines():
                ln = ln.lstrip("-*0123456789. ").strip().strip('"')
                if len(ln) > 3:
                    out.append(ln)
        # de-dup, drop exact echoes of the original (they add no averaging signal)
        seen, uniq = set(), []
        for p in out:
            key = p.lower()
            if key and key != original.strip().lower() and key not in seen:
                seen.add(key)
                uniq.append(p)
        return uniq
