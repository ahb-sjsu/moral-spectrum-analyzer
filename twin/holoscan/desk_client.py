"""Run the gate brain with its desks' model client on a set number of retries.

    DESK_CLIENT_RETRIES=0 python twin/holoscan/desk_client.py twin/service.py --stack ...

The centre, the dispatcher and Margaret's voice call the hosted model through erisml-compiler's
NRPOpenAIAdapter. The adapter retries a failed call ERISML_LLM_MAX_RETRIES times (default 2) and
times each try out at ERISML_LLM_TIMEOUT_S (default 60), and the OpenAI client inside it retries
a timed-out request twice more on its own, which the adapter has no setting for: up to 9 tries of
60 s. This launcher sets the client's own retries to DESK_CLIENT_RETRIES and then runs the brain
unchanged. Only that adapter is touched; the robot's model path (twin/cascade.py) is not.
"""

from __future__ import annotations

import os
import runpy
import sys

from erisml_compiler.annotation import llm_extractor

RETRIES = int(os.environ.get("DESK_CLIENT_RETRIES", "2"))
_init = llm_extractor.NRPOpenAIAdapter.__init__


def _init_with_retries(self, *a, **k):
    _init(self, *a, **k)
    self._client = self._client.with_options(max_retries=RETRIES)
    print(
        f"desk client: timeout {self.timeout_s:g} s, client retries {RETRIES}, "
        f"adapter retries {os.environ.get('ERISML_LLM_MAX_RETRIES', '2')}",
        flush=True,
    )


llm_extractor.NRPOpenAIAdapter.__init__ = _init_with_retries

if __name__ == "__main__":
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name="__main__")
