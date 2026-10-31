"""Replay a run's desk calls (centre, dispatcher, Margaret) against the model service and time
every model call. Run from a gtc checkout at 8073212 with the twin's PYTHONPATH:

    desk_probe.py RUN_DIR OUT.jsonl [--model gpt-oss] [--timeout 600] [--reasoning-effort low]

The desks are the brain's own classes (twin/brain.py Desk, MargaretVoice) on the facts recorded
in RUN_DIR/brain/session.jsonl. Each model call is made once (no retries, here or in the OpenAI
client) with the brain's settings (temperature 0.1 unless the caller sets one, max_tokens 8000
from BigOutputAdapter), so its true latency is recorded instead of being cut at 60 s. With
--reasoning-effort the request also carries `reasoning_effort` (the brain sends none). Each desk
turn's choices are written to OUT.desks.jsonl beside the choices the run recorded. The token is
read from ~/.llmtoken and never printed.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())
from openai import OpenAI  # noqa: E402

from twin.brain import Desk, MargaretVoice  # noqa: E402


class TimedAdapter:
    name = "probe"

    def __init__(self, model, timeout, out, label, reasoning_effort=None):
        key = open(os.path.expanduser("~/.llmtoken")).read().strip()
        self.client = OpenAI(
            base_url="https://ellm.nrp-nautilus.io/v1", api_key=key, timeout=timeout, max_retries=0
        )
        self.model, self.out, self.label = model, out, label
        self.extra = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}

    def call(self, system, user, **kw):
        row = {
            "label": self.label(),
            "t": time.time(),
            "system_chars": len(system),
            "user_chars": len(user),
            "max_tokens": kw.get("max_tokens", 8000),
        }
        t0 = time.time()
        try:
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=kw.get("temperature", 0.1),
                max_tokens=kw.get("max_tokens", 8000),
                **self.extra,
            )
            u = r.usage
            det = getattr(u, "completion_tokens_details", None)
            row.update(
                ok=True,
                served=r.model,
                finish=r.choices[0].finish_reason,
                prompt_tokens=u.prompt_tokens,
                completion_tokens=u.completion_tokens,
                reasoning_tokens=getattr(det, "reasoning_tokens", None) if det else None,
                content_chars=len(r.choices[0].message.content or ""),
            )
            text = (r.choices[0].message.content or "").strip()
        except Exception as e:
            row.update(ok=False, error=f"{type(e).__name__}: {str(e)[:160]}")
            text = ""
        row["latency_s"] = round(time.time() - t0, 2)
        with open(self.out, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(
            json.dumps(
                {
                    k: row.get(k)
                    for k in ("label", "latency_s", "ok", "finish", "completion_tokens", "error")
                }
            ),
            flush=True,
        )
        if not row["ok"]:
            raise RuntimeError(row["error"])
        return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("out")
    ap.add_argument("--model", default="gpt-oss")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    a = ap.parse_args()
    from erisml_compiler.ingestion.structured_loader import load_structured_input

    inventory = (load_structured_input("twin/stack/constitution.erisml").extra or {}).get(
        "sensor_substrates", {}
    )
    current = {"label": "?"}
    ad = TimedAdapter(a.model, a.timeout, a.out, lambda: current["label"], a.reasoning_effort)
    center = Desk(
        "center", "twin/scene/monitoring_center.erisml", ad, max_turns=1, inventory=inventory
    )
    ems = Desk("ems", "twin/scene/ems_dispatch.erisml", ad, max_turns=4, inventory=inventory)
    margaret = MargaretVoice(ad)
    n = 0
    for line in open(os.path.join(a.run, "brain", "session.jsonl"), encoding="utf-8"):
        rec = json.loads(line)["record"]
        k = rec.get("kind")
        if k == "reset":
            center.reset()
            ems.reset()
        if k not in ("center", "ems", "margaret"):
            continue
        n += 1
        current["label"] = f"{n:02d}-{k}"
        t0 = time.time()
        turn = {"desk_call": current["label"]}
        try:
            if k == "margaret":
                out = margaret.reply({"speaker": rec.get("speaker"), "said": rec.get("said")})
                turn.update(said=rec.get("said"), recorded=rec.get("reply"), replayed=out["reply"])
            else:
                out = (center if k == "center" else ems).decide(rec["facts"])
                turn.update(
                    recorded=[x["action"] for x in rec.get("actions", [])],
                    replayed=[x["action"] for x in out["actions"]],
                    fallback=[x.get("fallback") for x in out["actions"]],
                )
            status = "ok"
        except Exception as e:
            status = f"{type(e).__name__}: {str(e)[:120]}"
        turn["status"] = status
        with open(a.out + ".desks.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(turn, ensure_ascii=False) + "\n")
        print(
            json.dumps(
                {
                    "desk_call": current["label"],
                    "total_s": round(time.time() - t0, 1),
                    "status": status,
                }
            ),
            flush=True,
        )
    print("PROBE_DONE", flush=True)


if __name__ == "__main__":
    main()
