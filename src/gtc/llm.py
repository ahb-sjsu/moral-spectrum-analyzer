"""NRP managed-LLM client — OpenAI-compatible, zero-dependency (urllib).

Black-box target model for the invariance/containment work: translations (cross-lingual invariance),
euphemism/reframe generation at scale (attack-detection AUROC), and an LLM toxicity baseline. Auth +
endpoint come from the environment / git-ignored secret only (see `gtc.config`); nothing is hardcoded.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from gtc.config import NRP_LLM_BASE_URL, nrp_token


class NRPClient:
    def __init__(self, model: str = "gpt-oss", base_url: str | None = None,
                 token: str | None = None, timeout: int = 90):
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
            self.base_url + "/models", headers={"Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return sorted(m["id"] for m in json.load(r).get("data", []))

    def chat(self, system: str, user: str, temperature: float = 0.0, max_tokens: int = 1024) -> str:
        d = self._post("/chat/completions", {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature, "max_tokens": max_tokens,
        })
        return d["choices"][0]["message"]["content"].strip()

    def translate(self, text: str, language: str) -> str:
        return self.chat(
            "You are a professional translator. Output ONLY the translation — no notes, no quotes.",
            f"Translate the following into {language}:\n\n{text}",
        )
