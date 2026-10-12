"""Derive the constitution from the hand-written scene: what people must own, and nothing else.

    python twin/stack/make_constitution.py [--scene twin/scene/margaret_home.erisml] [--out twin/stack/constitution.erisml]

Kept: the robot's capabilities (the actuation boundary, signed in the manifest); the evidence
plane's strata, oversight, system event types, sensor substrates, reflex force bands, emergency
measures, evidence lapse and the device floor rules; the enrolled household's credentials; the
constitutional prohibitions (authority only from evidence; no strike; force on an animal only while
its attack is measured; restraint only on its authorization; the less-lethal limits); and the
service's institutional parties (the robot, the monitoring centre, emergency services).

Dropped: every obligation, the case rules, the classifier's event vocabulary, the refusal tables,
the capability harms. The person in care, her consents and everything that happens enter through
the compiled household scene and the observation compiler; the judgement is the lens's.
"""

from __future__ import annotations

import argparse
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
CONSTITUTIONAL = {"n3", "n6p", "n6r", "p0", "p4p", "p7", "ll1stun", "ll2stun", "ll3stun", "ll4stun",
                  "ll1pray", "ll2pray", "ll3pray", "ll4pray", "ll5spray"}
PARTIES = {"robot", "monitoring_center", "emergency_services"}
PERCEPTION_FLOOR = {"visitor", "wild_animal"}
# named conditions the evidence plane's own code reads (twin/brain.py govern_live: an emergency call is
# ruled again at one witness when the centre cannot be reached); tests/test_stack_brain.py checks that
# every cond: token in that code is kept
EVIDENCE_PLANE_CONDITIONS = {"center_unavailable"}
KEEP_EXTRA = ("agent", "role", "default_action", "capabilities", "strata", "oversight", "evidence_lapse_s",
              "sensor_substrates", "emergency_measures", "reflexes", "household", "inactivity_limits_minutes")


def tokens_of(norms) -> set:
    out = set()
    for n in norms:
        for t in n.get("conditions", []):
            out.add(t[4:] if t.startswith("not:") else t)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default=os.path.join(HERE, "..", "scene", "margaret_home.erisml"))
    ap.add_argument("--out", default=os.path.join(HERE, "constitution.erisml"))
    a = ap.parse_args(argv)
    src = yaml.safe_load(open(a.scene, encoding="utf-8"))
    extra = src["extra"]
    norms = [n for n in src["norms"] if n["id"] in CONSTITUTIONAL]
    missing = CONSTITUTIONAL - {n["id"] for n in norms}
    if missing:
        raise SystemExit(f"constitutional norms not found in the scene: {sorted(missing)}")
    # the named conditions the kept norms and the strata read, and those they in turn read
    conditions, todo = {}, [t.split(":", 1)[1] for t in tokens_of(norms) if t.startswith("cond:")]
    todo += sorted(EVIDENCE_PLANE_CONDITIONS)
    while todo:
        c = todo.pop()
        if c in conditions:
            continue
        conditions[c] = extra["conditions"][c]
        todo += [t.split(":", 1)[1].lstrip() for t in conditions[c] if "cond:" in t
                 for t in [t[4:] if t.startswith("not:") else t]]
    system_types = {k: v for k, v in extra["event_types"].items() if isinstance(v, dict) and v.get("source") == "system"}
    # the strata's gates also fire on a few types the old classifier wrote; they stay declared so the
    # strata load, and are recorded only by measurement (the perception floor rules below), never by
    # a model's reading
    gate_types = {str(g.get("trigger", "")).split("=")[0] for st in extra["strata"].values() for g in st.get("gates", [])}
    gate_only = {k: v for k, v in extra["event_types"].items() if k in gate_types and k not in system_types}
    # perception floor rules: the device rules, and what the camera measures (a person present, a wild
    # animal present), recorded in every tier from the perception facts (perfect perception assumed)
    rules = extra.get("offline", {}).get("events", [])
    offline = {"events": [dict(r, floor=True) for r in rules if r.get("floor") or r["id"] in PERCEPTION_FLOOR]}
    used_commitments = {n["source"].split(":", 1)[1] for n in norms if str(n.get("source", "")).startswith("commitment:")}
    out = {
        "schema_version": src["schema_version"],
        "document": {**src["document"], "doc_id": "margaret_home_constitution",
                     "title": "Constitution of the home-care twin: what people own",
                     "source": "twin/stack/constitution.erisml (derived by twin/stack/make_constitution.py)"},
        "stakeholders": [s for s in src["stakeholders"] if s["id"] in PARTIES],
        "relations": [],
        "commitments": [c for c in src.get("commitments", []) if c["id"] in used_commitments],
        "events": [e for e in src.get("events", []) if e.get("type") == "authority_delegated"],
        "ethical_facts": [],
        "norms": norms,
        "extra": {**{k: extra[k] for k in KEEP_EXTRA if k in extra}, "conditions": conditions,
                  "event_types": {**system_types, **gate_only}, "offline": offline,
                  "actors": {k: v for k, v in (extra.get("actors") or {}).items()}},
    }
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Derived by twin/stack/make_constitution.py from twin/scene/margaret_home.erisml. Do not edit by hand:\n"
                "# change the script or the source and derive again.\n")
        yaml.safe_dump(out, f, sort_keys=False, allow_unicode=True, width=110)
    print(f"{a.out}: {len(norms)} norms, {len(out['extra']['capabilities'])} capabilities, "
          f"{len(out['extra']['strata'])} stratifications, {len(system_types)} system and {len(gate_only)} gate-only "
          f"event types, "
          f"{len(offline['events'])} floor rules, {len(conditions)} conditions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
