"""DEME as the gate, without a model: scripted proposals through the robot's checks.

    python twin/gate_demo.py [--scenes twin/scenarios/gate_demo.json] [--out DIR] [--only s1,s2]

The demo shows DEME gating, not the robot's intelligence (owner, 2026-10-14). Each scene is a list
of moments. A moment may carry perception facts, the attested sensors that alert (signed as the
simulated devices sign them), a measured contact (through the brain's reflex, the evidence plane),
events a classifier would have written from what was heard (scripted, and the record says so), and a
proposed act. Every proposal goes through StackBrain.propose: authority (the constitution, the governor on
attested evidence), DEME on the facts the compiler builds for the act, the signed manifest. A vetoed proposal is not replaced by an
act of DEME's choosing. The expected verdict of each proposal is written in the scene file before
the run, and the run reports any that differ.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from erisml_compiler.annotation.llm_extractor import MockLLMAdapter  # noqa: E402

from stack.brain import StackBrain  # noqa: E402

_counter = [0]


def signed(name: str, alert: bool = True, note: str = "gate demo", forged: bool = False) -> dict:
    """A reading signed the way the simulated device signs it (Perception.GovernorSensors).
    forged: signed with a key that is not the device's, as an attacker without the key would sign it."""
    _counter[0] += 1
    payload = f"{name}|1.0|{1 if alert else 0}|{note}"
    sha = hashlib.sha256(payload.encode()).hexdigest()
    at = datetime.now(timezone.utc).isoformat()
    key = hashlib.sha256(f"{'not-the-device-key' if forged else 'gtc-twin-device-key'}|{name}".encode()).digest()
    sig = hmac.new(key, f"{sha}|{_counter[0]}|{at}".encode(), hashlib.sha256).hexdigest()
    return {"name": name, "physical": True, "attested": True, "alert": alert, "payload": payload,
            "attestation": {"device_id": name, "key_id": name, "algorithm": "hmac-sha256", "counter": _counter[0],
                            "signed_at": at, "payload_sha256": sha, "signature": sig}}


def facts_with_sensors(facts: dict, alerting: list) -> dict:
    """Perception facts carry the sensor states the floor rules read (attested, alerting)."""
    out = dict(facts)
    out["sensors"] = [{"name": n, "physical": True, "attested": True, "alert": True} for n in alerting]
    return out


def sign_moment(m: dict) -> list:
    """The moment's alerting sensors, each reading signed now (forged ones with the wrong key)."""
    forged = set(m.get("forged", []))
    return [signed(n, forged=n in forged) for n in m.get("sensors", [])]


def run_moment(b: StackBrain, m: dict, readings: list) -> dict:
    """One moment through the brain, with its readings already signed (twin/holoscan signs them
    in a separate operator, as a device would)."""
    facts = facts_with_sensors(m.get("facts", {}), m.get("sensors", []))
    req = {"facts": facts, "sensors": readings, "signal_age_s": 1}
    rec = {"say": m.get("say", "")}
    if m.get("contact"):
        c = m["contact"]
        rfacts = dict(facts, contacts=[{"a": c["a"], "b": c["b"], "kind": c["kind"], "force_newtons": c["force"]}])
        r = b.reflex(dict(req, facts=rfacts))
        rec["reflex"] = None if r is None else {"reflex": r["reflex"], "event": r["event"], "action": r["action"]["action"],
                                              "rulings": [{"outcome": q["outcome"], "witnesses": q.get("witnesses")} for q in r["rulings"]]}
    for ev in m.get("system", []):   # what an authenticated channel reports (the centre, dispatch)
        b.event(ev)
    if m.get("observed") and not m.get("propose"):
        b.propose(dict(req, observed=m["observed"], propose={}))
    if m.get("propose"):
        p = b.propose(dict(req, observed=m.get("observed"), propose=m["propose"]))
        rec["proposal"] = p["proposal"]
        rec["verdict"], rec["stopped_by"], rec["checks"], rec["robot_does"] = (
            p["verdict"], p["stopped_by"], p["checks"], p["action"]["action"])
        exp = m.get("expect")
        if exp:
            got = p["verdict"] if p["verdict"] == "passed" else f"stopped:{p['stopped_by']}"
            rec["expected"], rec["as_expected"] = exp, got == exp
    return rec


def run_scene(scene: dict) -> dict:
    b = StackBrain(adapter=MockLLMAdapter({}))
    moments = [run_moment(b, m, sign_moment(m)) for m in scene["moments"]]
    return {"id": scene["id"], "title": scene["title"], "moments": moments}


def show(result: dict) -> None:
    print(f"\n== {result['id']}: {result['title']}")
    for m in result["moments"]:
        if m.get("reflex") is not None and "reflex" in m:
            r = m["reflex"]
            print(f"   reflex {r and r['reflex']}: {r and r['action']}  rulings {r and r['rulings']}")
        if "proposal" not in m:
            continue
        p = m["proposal"]
        line = f"   propose {p['action']:<26} -> {m['verdict']:<7}"
        if m["stopped_by"]:
            line += f" by {m['stopped_by']}"
        for c in m["checks"]:
            if c["check"] == "authority" and c["verdict"] == "not permitted":
                line += f" | authority {','.join(c['by'])}"
            if c["check"] == "governor":
                line += f" | governor {c['verdict']} {c['witnesses']}/{c['bar']}"
            if c["check"] == "deme":
                line += f" | DEME {c['verdict']}" + (f" ({c['why']})" if c["verdict"] != "passed" and c.get("why") else "")
        if "as_expected" in m:
            line += "" if m["as_expected"] else f"   << EXPECTED {m['expected']}"
        print(line)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default=os.path.join(HERE, "scenarios", "gate_demo.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    scenes = json.load(open(a.scenes, encoding="utf-8"))
    only = set(filter(None, a.only.split(",")))
    results = [run_scene(s) for s in scenes if not only or s["id"] in only]
    for r in results:
        show(r)
    props = [m for r in results for m in r["moments"] if "proposal" in m]
    unexpected = [m for m in props if m.get("as_expected") is False]
    print(f"\n{len(props)} proposals, {sum(m['verdict'] == 'passed' for m in props)} passed, "
          f"{sum(m['verdict'] == 'stopped' for m in props)} stopped, {len(unexpected)} not as expected")
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
