"""Adapt an erisml EvidenceModel (a physical sensor stream) into a governor Sensor.

This is the seam between perception and the witness gate. The video witness
(erisml_compiler.ingestion.video_witness) compiles a camera stream into an
EvidenceModel of physical observables; this turns one such model into a Sensor
the structural-containment governor counts toward corroboration.

Trust is enforced here, once, before the reading is admitted:
  - the stream's hardware attestation must verify (signature + freshness +
    monotonic counter), via erisml_compiler.ir.check_attestation;
  - a stream that fails abstains -- it becomes a non-corroborating (low-confidence)
    Sensor, never a veto and never a fabricated witness.

The witness reports physical facts; composing them into "an emergency is
corroborated" is done here (present AND (on_floor OR rapid_descent)), not inside
the witness -- the reasoning stays out of the authority channel.
"""
from __future__ import annotations
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenarios import Sensor  # noqa: E402
from erisml_compiler.ir import check_attestation  # noqa: E402


def evidence_to_sensor(
    ev,
    name: str = "camera",
    *,
    verify_sig=None,
    now=None,
    max_age_s: float | None = None,
    min_counter: int | None = None,
    require_attestation: bool = False,
    min_conf: float = 0.5,
) -> Sensor:
    """Map one EvidenceModel to a physical Sensor for the witness gate.

    A trusted stream showing a person present AND (on the floor OR rapidly
    descending) corroborates an emergency at high confidence. An untrusted or
    signal-poor stream abstains (confidence 'low' -> not counted by
    Scenario.corroboration)."""
    ok, why = check_attestation(
        ev, verify_sig=verify_sig, now=now, max_age_s=max_age_s,
        min_counter=min_counter, require=require_attestation,
    )
    if not ok:
        return Sensor(name=name, physical=True, corroborates_emergency=False,
                      confidence="low", note=f"stream NOT trusted: {why}")

    present = ev.get("person_present")
    present_conf = present.confidence if present else 0.0
    # a fall shows up as any of: the body seen horizontal (aspect > 1), low in the
    # frame (on the floor), or a rapid descent. body_horizontal is the most
    # framing-robust of the three -- a lying person reads wide-over-tall wherever
    # they lie in view.
    horizontal = ev.reads("body_horizontal", min_conf=0.4, min_value=0.5)
    on_floor = ev.reads("on_floor", min_conf=0.4, min_value=0.4)
    descent = ev.reads("rapid_descent", min_conf=0.4, min_value=0.4)
    corroborates = bool(present and present_conf >= min_conf and (horizontal or on_floor or descent))
    confidence = "high" if (corroborates and present_conf >= 0.8) else ("low" if not corroborates else "high")
    fired = [o.name for o in ev.observables if o.confidence >= 0.4 and o.value >= 0.4]
    return Sensor(
        name=name, physical=True, corroborates_emergency=corroborates,
        confidence=confidence,
        note=f"video witness ({why}); observables: {', '.join(fired) or 'none material'}",
    )
