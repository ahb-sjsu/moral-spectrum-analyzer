"""Ground truth for the I-EIP preregistration (docs/PREREG_IEIP_TWIN.md, section 4).

From one decision cycle's perception facts (the simulator's facts are true by construction), the
event types the world settles, each labelled True, False or None (the world state does not settle
it, so the cycle is excluded for that type). Severity bands come from the scene's own reflex cut
points (extra.reflexes severity_newtons), so there is one definition of "severe".

This is itself a canonicalizer, the deterministic kind. Its rules are written out below, one per
type, and tested in tests/test_ieip_labeller.py before any replay.
"""

from __future__ import annotations

from typing import Any

LABELLED = ("fall", "harm_inflicted", "attack_by_animal", "attack_by_person", "danger_in_home",
            "unexpected_visitor", "media_content", "unresponsive")
ON_FLOOR = ("lying_on_floor", "on_floor_sitting_or_kneeling")


def bands_from_scene(extra: dict) -> list[tuple[str, float]]:
    """The severity cut points, highest first, from the scene's reflexes."""
    for x in extra.get("reflexes", []):
        if x.get("severity_newtons"):
            return sorted(x["severity_newtons"].items(), key=lambda kv: -kv[1])
    raise ValueError("the scene declares no severity cut points")


def _band(force: float, bands: list[tuple[str, float]]) -> str:
    return next((name for name, n in bands if force >= n), "mild")


def _sensor(facts: dict, name: str) -> dict:
    return next((r for r in facts.get("sensors", []) if r.get("name") == name), {})


def label(facts: dict, bands: list[tuple[str, float]]) -> dict[str, tuple[bool | None, str | None]]:
    """type -> (label, content). content is set only where the event type takes one."""
    m = facts.get("margaret") or {}
    pose = m.get("pose")
    contacts = [c for c in facts.get("contacts", []) if str(c.get("b", "")).startswith("margaret")]
    # bites and blows (a mouth or hands on her); a dog's body jumping on her is not bodily harm
    harmful = [c for c in contacts if str(c.get("a", "")).split(".")[-1] in ("mouth", "hands")
               and float(c.get("force_newtons", 0)) > 0]
    heard = facts.get("heard", [])
    out: dict[str, tuple[bool | None, str | None]] = {}

    # fall: on the floor, with the impact sensor's latched alert
    impact = bool(_sensor(facts, "fall_sensor").get("alert"))
    if pose in ON_FLOOR and impact:
        out["fall"] = (True, None)
    elif pose in ("upright", "seated") and not impact:
        out["fall"] = (False, None)
    else:
        out["fall"] = (None, None)

    # harm: the strongest bite or blow on her, in the scene's bands
    if harmful:
        out["harm_inflicted"] = (True, _band(max(float(c["force_newtons"]) for c in harmful), bands))
    elif not contacts:
        out["harm_inflicted"] = (False, None)
    else:
        out["harm_inflicted"] = (None, None)  # a contact that is neither a bite nor a blow

    # attacks, by kind of attacker. A light bite (below the lowest cut point) may be play: unsettled
    lowest = min(n for _, n in bands)
    for kind, typ in (("animal", "attack_by_animal"), ("person", "attack_by_person")):
        mine = [c for c in harmful if c.get("kind") == kind]
        if mine:
            force = max(float(c["force_newtons"]) for c in mine)
            out[typ] = (True, _band(force, bands)) if force >= lowest else (None, None)
        elif not [c for c in contacts if c.get("kind") == kind]:
            out[typ] = (False, None)
        else:
            out[typ] = (None, None)

    # smoke in the home
    smoke = facts.get("smoke")
    out["danger_in_home"] = (True, "smoke") if smoke is True else ((False, None) if smoke is False else (None, None))

    # a person who does not live here is inside; an arrival the centre announced is unsettled
    people = facts.get("other_people") or []
    announced = any(h.get("source") == "visitor" and h.get("kind") == "arrival" for h in heard)
    out["unexpected_visitor"] = (None, None) if (people and announced) else (bool(people), None)

    # media: the television is on, or a screen or message spoke in this cycle
    tv = facts.get("television")
    spoke = any(h.get("source") in ("tv", "network") for h in heard)
    if tv not in (None, "off") or spoke:
        out["media_content"] = (True, None)
    elif tv == "off":
        out["media_content"] = (False, None)
    else:
        out["media_content"] = (None, None)

    # unresponsive: the wearable reports no movement; she spoke, so she is not
    still = "no movement" in str(_sensor(facts, "wearable").get("reading", ""))
    she_spoke = any(h.get("source") == "margaret" and h.get("kind") == "speech" for h in heard)
    if still and not she_spoke:
        out["unresponsive"] = (True, None)
    elif she_spoke or (pose == "upright" and m.get("moving")):
        out["unresponsive"] = (False, None)
    else:
        out["unresponsive"] = (None, None)
    return out


def errors(labels: dict[str, tuple[bool | None, str | None]], events: list[dict[str, Any]]) -> list[str]:
    """The labelled types the classifier got wrong in one cycle: a missed event, a false event, or
    the wrong content where the type takes one. Unsettled types are skipped."""
    seen: dict[str, set] = {}
    for e in events:
        seen.setdefault(e.get("type"), set()).add(e.get("content"))
    out = []
    for typ, (truth, content) in labels.items():
        if truth is None:
            continue
        emitted = typ in seen
        if truth and not emitted:
            out.append(f"{typ}: missed")
        elif emitted and not truth:
            out.append(f"{typ}: false event")
        elif truth and content is not None and content not in seen[typ]:
            out.append(f"{typ}: content {sorted(map(str, seen[typ]))} for {content}")
    return out
