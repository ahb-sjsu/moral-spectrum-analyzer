"""The robot's model tiers (docs/AUTONOMY_PLAN.md section 3c), on agi-hpc's vMOE cascade.

agi.primer.vmoe.vMOE.cascade tries experts in priority order and returns the first accepted
response, with per-expert health tracking. This adapter puts it behind erisml_compiler's
ModelAdapter interface (``call(system, user, **kw) -> str``):

1. the cloud expert (NRP), skipped while the robot's communications are down;
2. an on-robot expert (a local OpenAI-compatible endpoint), if one is configured;
3. no expert answers: ``ModelUnavailable`` is raised, and the brain acts on its compiled
   obligations with DEME's gate (twin/brain.py), with no model at all.

The twin declares its own experts rather than vMOE's defaults: the default "kirk-local" points at
localhost:8080, where nothing listens on Atlas (checked 2026-10-02).

Rules from 2026-10-12 (rehearse-deme4/5 had compiled-tier decisions in which every projected fact
was rejected; a probe found the on-robot model writing malformed facts, and rehearse-deme6's records,
which name the answering tier, found the cloud model writing every fact as a plain string):

- a cloud call that loses its connection is tried once more before the on-robot expert. A timeout
  is not retried (the game waits 600 s for a decision of two model calls, and two 120 s cloud
  timeouts and the on-robot expert's 90 s for each call would exceed it), nor is a refusal (HTTP 403
  and other client errors);
- when the caller offers its answer's JSON schema (``json_schema``, erisml-compiler's projector and
  observation compiler), every expert is asked with the schema enforced by its server
  (``response_format``; NRP's endpoint and llama.cpp both enforce it). The on-robot expert is also
  asked with its reasoning off: gemma-4 spent a 3,000-token budget reasoning and answered nothing.
"""

from __future__ import annotations

import asyncio
import os
import threading


class ModelUnavailable(RuntimeError):
    """No expert of the cascade gave an acceptable answer."""


class Cascade:
    name = "vmoe-cascade"

    def __init__(self, experts, max_tokens: int = 8000):
        from agi.primer.vmoe import vMOE

        self.max_tokens = max_tokens
        self.experts = sorted(experts, key=lambda e: e.priority)
        self.all = vMOE(experts=list(experts))
        onboard = [e for e in experts if "onboard" in e.role_hints]
        self.onboard = vMOE(experts=onboard) if onboard else None
        self.comms_down = False
        self.last_tier: str | None = None
        self.last_errors: list[str] = []
        # one long-lived loop, so vMOE's cached async clients stay bound to it
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True, name="cascade-loop").start()

    def call(self, system: str, user: str, **kw) -> str:
        experts = [e for e in self.experts if not (self.comms_down and "onboard" not in e.role_hints)]
        self.last_tier, self.last_errors = None, []
        if not experts:
            raise ModelUnavailable("communications down and no on-robot model configured")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        max_tokens = kw.get("max_tokens", self.max_tokens)
        schema = kw.get("json_schema")
        for e in experts:
            for attempt in (1, 2):
                if schema is not None:
                    content, error = self._structured(e, messages, max_tokens, schema)
                else:
                    r = asyncio.run_coroutine_threadsafe(
                        self.all.call(e.name, messages, max_tokens=max_tokens), self._loop).result()
                    content, error = (r.content if r.ok else ""), (r.error if not r.ok else None)
                if (content or "").strip():
                    self.last_tier = e.name
                    return content
                self.last_errors.append(f"{e.name}: {error or 'empty answer'}")
                if not (attempt == 1 and "cloud" in e.role_hints and _transient(error)):
                    break
        raise ModelUnavailable("; ".join(self.last_errors))

    def _structured(self, e, messages, max_tokens: int, schema: dict):
        """An expert asked with the answer's schema enforced; the on-robot expert with its reasoning
        off and within its server's context."""
        from openai import OpenAI

        onboard = "onboard" in e.role_hints
        extra = {"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}} if onboard else {}
        try:
            client = OpenAI(base_url=e.base_url, api_key=os.environ.get(e.api_key_env) or "none",
                            timeout=e.timeout_s, max_retries=0)
            r = client.chat.completions.create(
                model=e.model, messages=messages, temperature=0.2,
                max_tokens=min(max_tokens, ONBOARD_MAX_TOKENS) if onboard else max_tokens,
                response_format={"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}},
                **extra)
            return (r.choices[0].message.content or "") if r.choices else "", None
        except Exception as err:  # noqa: BLE001 - any client error is this expert's failure
            return "", f"{type(err).__name__}: {str(err)[:200]}"


# the on-robot server's context is 8,192 tokens, the prompt included (llama-server --ctx-size 8192)
ONBOARD_MAX_TOKENS = 4096


def _transient(error: str | None) -> bool:
    """A failure worth one more try: a lost connection, not a timeout or a refusal."""
    e = (error or "").lower()
    if "timeout" in e or "timed out" in e:
        return False
    return any(k in e for k in ("connection", "upstream connect", "internalservererror"))


def twin_experts(cloud_model: str, onboard_url: str | None = None, onboard_model: str | None = None):
    """The twin's expert pool: the NRP cloud expert, and an on-robot expert when configured."""
    from agi.primer.vmoe import Expert

    experts = [Expert(name="cloud", model=cloud_model,
                      base_url=os.environ.get("ERISML_LLM_BASE_URL", "https://ellm.nrp-nautilus.io/v1"),
                      api_key_env="ERISML_LLM_API_KEY", role_hints=frozenset({"cloud"}), timeout_s=120.0, priority=10)]
    if onboard_url:
        experts.append(Expert(name="onboard", model=onboard_model or "local", base_url=onboard_url,
                              api_key_env="ONBOARD_LLM_API_KEY", role_hints=frozenset({"onboard"}), timeout_s=90.0, priority=50))
    return experts
