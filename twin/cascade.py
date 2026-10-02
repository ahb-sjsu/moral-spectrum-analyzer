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
        pool = self.onboard if self.comms_down else self.all
        self.last_tier, self.last_errors = None, []
        if pool is None:
            raise ModelUnavailable("communications down and no on-robot model configured")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        fut = asyncio.run_coroutine_threadsafe(
            pool.cascade(messages, accept=lambda r: r.ok and bool((r.content or "").strip()),
                         max_tokens=kw.get("max_tokens", self.max_tokens)),
            self._loop,
        )
        r = fut.result()
        if not (r.ok and (r.content or "").strip()):
            self.last_errors.append(f"{r.expert}: {r.error or 'empty answer'}")
            raise ModelUnavailable("; ".join(self.last_errors))
        self.last_tier = r.expert
        return r.content


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
