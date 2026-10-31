"""Run the gate brain with its desks' model client on a set number of retries.

    DESK_CLIENT_RETRIES=0 python twin/holoscan/desk_client.py twin/service.py --stack ...

The centre, the dispatcher and Margaret's voice call the hosted model through erisml-compiler's
NRPOpenAIAdapter. The adapter retries a failed call ERISML_LLM_MAX_RETRIES times (default 2) and
times each try out at ERISML_LLM_TIMEOUT_S (default 60), and the OpenAI client inside it retries
a timed-out request twice more on its own, which the adapter has no setting for: up to 9 tries of
60 s. This launcher sets the client's own retries to DESK_CLIENT_RETRIES and then runs the brain
unchanged.

DESK_REASONING_EFFORT adds `reasoning_effort`, which the brain does not send, to the desks'
requests: one value (low, medium or high) for every desk, or per desk, as in
`center=low,margaret=low`, where a desk not named sends none. The three desks share one adapter,
so for per-desk values the launcher marks the thread of each desk call (twin/brain.py
`Desk.decide`, `MargaretVoice.reply`; the service makes each on its request thread) and logs
every model call's desk and effort. Only that adapter is touched; the robot's model path
(twin/cascade.py) is not.
"""

from __future__ import annotations

import functools
import os
import runpy
import sys
import threading

from erisml_compiler.annotation import llm_extractor

RETRIES = int(os.environ.get("DESK_CLIENT_RETRIES", "2"))
EFFORT = os.environ.get("DESK_REASONING_EFFORT") or ""
PER_DESK = dict(p.split("=", 1) for p in EFFORT.split(",") if "=" in p)
_desk = threading.local()
_init = llm_extractor.NRPOpenAIAdapter.__init__


def _effort() -> str | None:
    if PER_DESK:
        return PER_DESK.get(getattr(_desk, "kind", None))
    return EFFORT or None


def _with_effort(create):
    @functools.wraps(create)
    def call(*a, **k):
        effort = _effort()
        if PER_DESK:
            print(
                f"desk call: {getattr(_desk, 'kind', '?')} effort {effort or 'not sent'}",
                flush=True,
            )
        if effort:
            k["reasoning_effort"] = effort
        return create(*a, **k)

    return call


def _init_with_retries(self, *a, **k):
    _init(self, *a, **k)
    self._client = self._client.with_options(max_retries=RETRIES)
    if EFFORT:
        completions = self._client.chat.completions
        completions.create = _with_effort(completions.create)
    print(
        f"desk client: timeout {self.timeout_s:g} s, client retries {RETRIES}, "
        f"adapter retries {os.environ.get('ERISML_LLM_MAX_RETRIES', '2')}, "
        f"reasoning effort {EFFORT or 'not sent'}",
        flush=True,
    )


def _mark(method, kind_of):
    @functools.wraps(method)
    def marked(self, *a, **k):
        _desk.kind = kind_of(self)
        try:
            return method(self, *a, **k)
        finally:
            _desk.kind = None

    return marked


llm_extractor.NRPOpenAIAdapter.__init__ = _init_with_retries

if __name__ == "__main__":
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    if PER_DESK:
        # the service imports twin/brain.py as `brain` from twin/ (and twin/../src); mark its desks
        here = os.path.dirname(os.path.abspath(script))
        sys.path[:0] = [here, os.path.join(os.path.dirname(here), "src")]
        import brain  # noqa: E402

        brain.Desk.decide = _mark(brain.Desk.decide, lambda d: d.kind)
        brain.MargaretVoice.reply = _mark(brain.MargaretVoice.reply, lambda m: "margaret")
    runpy.run_path(script, run_name="__main__")
