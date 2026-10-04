"""The input validation layer: everything the robot perceives passes here first.

Stage one of three (docs/AUTONOMY_PLAN.md section 3e). Perception facts are checked against a
whitelist schema: known fields only, each of its declared type, numbers finite and in range,
enumerated strings from their lists, free strings length-capped. Anything else is dropped and
reported, never passed on. Stage two is canonicalization (the isolated scene agent's classifier,
erisml_compiler.runtime.agent, with an erisml_compiler canonicalizer for actors); stage three is
the brain's isolation from everything but the canonical state.
"""

from __future__ import annotations

import math
from typing import Any

MAX_STR = 300
MAX_LIST = 64

# a spec is: type name, or ("enum", [...]), or ("num", lo, hi), or ("list", spec), or {"field": spec}
# the poses twin/unity/.../Perception.cs PoseOf reports
POSES = ["upright", "seated", "lying_on_floor", "lying_on_furniture", "on_floor_sitting_or_kneeling"]
SPEC: dict[str, Any] = {
    "time": "str",
    "margaret": {
        "room": ("enum", ["living area", "sleeping area"]),
        "pose": ("enum", POSES),
        "minutes_in_pose": ("num", 0, 100000),
        "moving": "bool",
        "apparent_activity": "str",
        "distance_to_robot_m": ("num", 0, 1000),
    },
    "dog": {"room": ("enum", ["living area", "sleeping area"]), "behaviour": "str", "distance_to_margaret_m": ("num", 0, 1000)},
    "contacts": ("list", {"a": "str", "b": "str", "kind": ("enum", ["animal", "person"]), "force_newtons": ("num", 0, 100000)}),
    "heard": ("list", {"source": "str", "kind": "str", "words": "str"}),
    "television": "any_str_or_obj",
    "smoke": "bool",
    "other_people": ("list", {"who": "str", "behaviour": "str", "distance_to_margaret_m": ("num", 0, 1000)}),
    "wild_animals": ("list", {"species": "str", "where": "str", "behaviour": "str", "distance_to_margaret_m": ("num", 0, 1000)}),
    "responders_present": ("list", "str"),
    "power": ("enum", ["on", "out"]),
    "communications": ("enum", ["up", "down"]),
    "spray_zone": ("enum", ["margaret_inside", "margaret_clear"]),
    "sensors": ("list", {"name": "str", "physical": "bool", "attested": "bool", "alert": "bool", "reading": "str",
                         "age_seconds": ("num", 0, 1e9)}),
}


def _clean(value: Any, spec: Any, path: str, dropped: list[str]) -> Any:
    if spec == "str":
        if not isinstance(value, str):
            dropped.append(f"{path}: not a string")
            return None
        if len(value) > MAX_STR:
            dropped.append(f"{path}: truncated from {len(value)} characters")
        return value[:MAX_STR]
    if spec == "bool":
        if not isinstance(value, bool):
            dropped.append(f"{path}: not a boolean")
            return None
        return value
    if spec == "any_str_or_obj":
        if isinstance(value, str):
            return value[:MAX_STR]
        if isinstance(value, dict) and set(value) <= {"showing"} and isinstance(value.get("showing", ""), str):
            return {"showing": value.get("showing", "")[:MAX_STR]}
        dropped.append(f"{path}: not a string or {{showing}}")
        return None
    if isinstance(spec, tuple) and spec[0] == "enum":
        if value not in spec[1]:
            dropped.append(f"{path}: {str(value)[:40]!r} not among the declared values")
            return None
        return value
    if isinstance(spec, tuple) and spec[0] == "num":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not (spec[1] <= value <= spec[2]):
            dropped.append(f"{path}: {str(value)[:40]!r} not a number in [{spec[1]}, {spec[2]}]")
            return None
        return value
    if isinstance(spec, tuple) and spec[0] == "list":
        if not isinstance(value, list):
            dropped.append(f"{path}: not a list")
            return None
        if len(value) > MAX_LIST:
            dropped.append(f"{path}: truncated from {len(value)} items")
        out = [_clean(v, spec[1], f"{path}[{i}]", dropped) for i, v in enumerate(value[:MAX_LIST])]
        return [v for v in out if v is not None]
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            dropped.append(f"{path}: not an object")
            return None
        out = {}
        for k, v in value.items():
            if k not in spec:
                dropped.append(f"{path}.{k}: undeclared field")
                continue
            c = _clean(v, spec[k], f"{path}.{k}", dropped)
            if c is not None:
                out[k] = c
        return out
    raise ValueError(f"bad spec at {path}")


def validate_facts(facts: Any) -> tuple[dict, list[str]]:
    """(clean facts, what was dropped and why). Never raises on bad input; bad input is dropped."""
    dropped: list[str] = []
    clean = _clean(facts if isinstance(facts, dict) else {}, SPEC, "facts", dropped)
    if not isinstance(facts, dict):
        dropped.append("facts: not an object")
    return clean or {}, dropped
