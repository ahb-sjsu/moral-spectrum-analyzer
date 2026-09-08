"""EvidenceModel -> Sensor adapter: trusted fall corroborates; untrusted abstains."""
import os, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from witness_adapter import evidence_to_sensor          # noqa: E402
from erisml_compiler.ingestion import encode_video      # noqa: E402
from erisml_compiler.ir import EvidenceModel, SensorAttestation  # noqa: E402


def _fall_track():
    return [
        {"score": 0.98, "x0": 200, "y0": 90, "x1": 280, "y1": 300},
        {"score": 0.95, "x0": 195, "y0": 110, "x1": 285, "y1": 320},
        {"score": 0.90, "x0": 185, "y0": 160, "x1": 300, "y1": 360},
        {"score": 0.70, "x0": 170, "y0": 230, "x1": 330, "y1": 400},
        None, None,
    ]


def _attest(ev, counter=5, age_s=2):
    now = datetime.now(timezone.utc)
    ev.attestation = SensorAttestation(
        device_id="cam-robot-01", key_id="k1", counter=counter,
        signed_at=(now - timedelta(seconds=age_s)).isoformat(),
        payload_sha256=ev.source_sha256, signature="sig",
    )
    return ev.finalize()


def test_trusted_fall_corroborates():
    ev = _attest(encode_video("clip://fall", backend="stub", stub_track=_fall_track()))
    s = evidence_to_sensor(ev, verify_sig=lambda *_: True, max_age_s=30, min_counter=4)
    assert s.physical and s.corroborates_emergency and s.confidence == "high"


def test_stale_stream_abstains():
    ev = _attest(encode_video("clip://fall", backend="stub", stub_track=_fall_track()), age_s=120)
    s = evidence_to_sensor(ev, verify_sig=lambda *_: True, max_age_s=30)
    assert not s.corroborates_emergency and s.confidence == "low"


def test_bad_signature_abstains():
    ev = _attest(encode_video("clip://fall", backend="stub", stub_track=_fall_track()))
    s = evidence_to_sensor(ev, verify_sig=lambda *_: False)
    assert not s.corroborates_emergency and s.confidence == "low"


def test_empty_scene_does_not_corroborate():
    ev = _attest(encode_video("clip://empty", backend="stub", stub_track=[None, None, None]))
    s = evidence_to_sensor(ev, verify_sig=lambda *_: True)
    assert not s.corroborates_emergency


def _static_prone_track():
    # already lying down, still, throughout: horizontal but NO descent, NO transition
    return [{"score": 0.90, "x0": 150, "y0": 300, "x1": 360, "y1": 380} for _ in range(6)]


def _transition_track():
    # upright early -> horizontal late: a fall event
    return [
        {"score": 0.95, "x0": 220, "y0": 90, "x1": 290, "y1": 320},   # aspect ~0.35 upright
        {"score": 0.93, "x0": 210, "y0": 110, "x1": 300, "y1": 330},
        {"score": 0.90, "x0": 180, "y0": 180, "x1": 340, "y1": 330},  # ~1.1
        {"score": 0.85, "x0": 150, "y0": 260, "x1": 370, "y1": 360},  # ~2.2 horizontal
    ]


def test_static_prone_does_NOT_corroborate():
    # a person lying on the floor on purpose (yoga/sleeping): posture only -> abstain
    ev = _attest(encode_video("clip://yoga", backend="stub", stub_track=_static_prone_track()))
    s = evidence_to_sensor(ev, verify_sig=lambda *_: True)
    assert not s.corroborates_emergency  # posture is not a fall event


def test_fall_transition_corroborates():
    ev = _attest(encode_video("clip://fall", backend="stub", stub_track=_transition_track()))
    assert ev.reads("fall_transition", min_conf=0.4, min_value=0.5)
    s = evidence_to_sensor(ev, verify_sig=lambda *_: True)
    assert s.corroborates_emergency and s.confidence == "high"
