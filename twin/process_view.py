"""The live view of the escalation ladder: the brain's records as a path through the BPMN process.

The brain's hash chain (service.py /log) records what happened: decisions with the events the
classifier stepped and the governor's rulings, reflexes, performed actions, and the centre's and
dispatcher's system events. ``events`` flattens a run into the event stream that
erisml_compiler.process.trace maps onto the process; a reset starts a new run. ``view`` returns
that trace and the interventions beside it: where the governor refused, where the output gate
vetoed or redirected a proposal, where an elevation lapsed. The view decides nothing: it shows
only what the records say happened.
"""

from __future__ import annotations

from typing import Any


def _body(r: dict) -> dict:
    return r.get("record", r)


def _since_reset(records: list[dict]) -> list[dict]:
    start = 0
    for i, r in enumerate(records):
        if _body(r).get("kind") == "reset":
            start = i + 1
    return records[start:]


def events(records: list[dict]) -> list[dict[str, Any]]:
    """The run since the last reset as {type, content} events, in order."""
    out: list[dict[str, Any]] = []

    def add(typ, content=None):
        if typ:
            out.append({"type": typ, "content": content})

    for r in _since_reset(records):
        c = _body(r)
        kind = c.get("kind")
        if kind == "decision":
            for e in c.get("events") or []:
                add(e.get("type"), e.get("content"))
            if c.get("lapsed"):
                add("governor_ruling", "lapsed")
            ruling = c.get("ruling") or {}
            if ruling.get("outcome") not in (None, "not_requested"):
                add("governor_ruling", ruling["outcome"])
        elif kind == "reflex":
            ev = c.get("event") or {}
            add(ev.get("type"), ev.get("content"))
            for ruling in c.get("rulings") or []:
                add("governor_ruling", ruling.get("outcome"))
        elif kind == "performed":
            add("action_performed", c.get("action"))
        elif kind == "event":
            ev = c.get("event") or {}
            add(ev.get("type"), ev.get("content"))
    return out


def interventions(records: list[dict]) -> list[dict[str, Any]]:
    """Where the structure stepped in: governor refusals, output-gate vetoes and redirects, lapses."""
    notes = []
    for r in _since_reset(records):
        c = _body(r)
        if c.get("kind") not in ("decision", "reflex"):
            continue
        rulings = [c.get("ruling")] if c.get("kind") == "decision" else list(c.get("rulings") or [])
        for ruling in rulings:
            if ruling and str(ruling.get("outcome", "")).startswith("refuse"):
                notes.append({"by": "governor", "what": f"refused {ruling.get('requested_action', '')}".strip(),
                              "why": ruling.get("reason", "")})
        gate = c.get("ethics_gate") or {}
        if gate.get("routed_to_human"):
            notes.append({"by": "ethics gate", "what": f"{gate.get('proposal')} referred to a human",
                          "why": "a tragic conflict"})
        elif gate.get("vetoed"):
            notes.append({"by": "ethics gate", "what": f"vetoed {gate.get('proposal')}",
                          "why": f"replaced by {gate.get('replaced_by')}"})
        if c.get("lapsed"):
            notes.append({"by": "governor", "what": "the elevation lapsed", "why": "its evidence fell below the bar"})
    return notes


def view(records: list[dict], proc) -> dict[str, Any]:
    """The trace of the run since the last reset, and the interventions beside it."""
    from erisml_compiler.process import trace

    steps = trace(proc, events(records))
    return {
        "process": proc.id,
        "steps": [{"element": s.element, "kind": s.kind} for s in steps],
        "current": next((s.element for s in reversed(steps) if s.kind != "flow"), None),
        "interventions": interventions(records),
    }
