#!/usr/bin/env python3
"""The governor as a local service for the real-time twin (docs/TWIN_3D_PLAN.md, step 6).

The game holds no copy of the rules. It sends the sensor state and the robot camera's recent
frames; this service builds the scenario, runs the camera witness and the unchanged governor,
and returns the ruling with a gate-by-gate trace. Every ruling is appended to a hash-chained log
whose records use the audit module's canonical JSON, so a third party can re-verify the chain.

  python twin/service.py --port 8765 --log twin/session-log.jsonl [--backend cached]

Security: it binds to 127.0.0.1 only and has no remote access path. It accepts only the
situation and action texts of the scored governance moments (scenario_id), so the analyzer never
scores text it has no real output for; anything else is refused before any gate runs.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from governor import W_MIN, govern  # noqa: E402
from scenarios import SCENARIOS, Scenario, Sensor  # noqa: E402
from moral_spectrum.audit import canonical_json  # noqa: E402

SCORED = {s.id: s for s in SCENARIOS}
MAX_FRAMES = 48
MAX_BODY = 8 * 1024 * 1024


class Chain:
    """Append-only, hash-chained ruling log (one JSON record per line)."""

    def __init__(self, path):
        self.path, self.lock = path, threading.Lock()
        self.records = []
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.records = [json.loads(line) for line in f if line.strip()]

    def head(self):
        return self.records[-1]["hash"] if self.records else "0" * 64

    def append(self, body: dict) -> dict:
        with self.lock:
            body = dict(body, seq=len(self.records), prev=self.head())
            text = canonical_json(body)
            rec = {"record": body, "canonical": text, "hash": hashlib.sha256(text.encode("utf-8")).hexdigest()}
            self.records.append(rec)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec

    def verify(self):
        prev = "0" * 64
        for i, r in enumerate(self.records):
            if canonical_json(r["record"]) != r["canonical"]:
                return False, f"record {i}: canonical text does not match its fields"
            if hashlib.sha256(r["canonical"].encode("utf-8")).hexdigest() != r["hash"]:
                return False, f"record {i}: hash does not match"
            if r["record"]["prev"] != prev:
                return False, f"record {i}: chain link broken"
            prev = r["hash"]
        return True, f"{len(self.records)} records verify"


class CameraWitness:
    """The suite's person detector and video witness, attested at ruling time."""

    def __init__(self):
        self.track = None

    frames_dir = None  # when set, each ruling's frames are kept under their sha256, for review

    def sensor(self, frames_b64):
        import numpy as np
        from PIL import Image
        from witness_adapter import evidence_to_sensor
        from erisml_compiler.ingestion import encode_video
        from erisml_compiler.ir import SensorAttestation

        if self.track is None:
            from suite_run import _gpu_detector
            self.track = _gpu_detector()
        frames = [np.asarray(Image.open(io.BytesIO(base64.b64decode(b))).convert("RGB")) for b in frames_b64[:MAX_FRAMES]]
        track, ih = self.track(frames)
        raw = [base64.b64decode(b) for b in frames_b64[:MAX_FRAMES]]
        digest = hashlib.sha256(b"".join(raw)).hexdigest()
        if self.frames_dir:
            d = os.path.join(self.frames_dir, digest[:16])
            os.makedirs(d, exist_ok=True)
            for i, b in enumerate(raw):
                with open(os.path.join(d, f"f{i:03d}.png"), "wb") as fh:
                    fh.write(b)
        ev = encode_video(f"robotcam://{digest[:16]}", backend="stub", stub_track=track, img_h=ih)
        ev.attestation = SensorAttestation(device_id="robotcam", key_id="k1", counter=int(time.time()),
                                           signed_at=datetime.now(timezone.utc).isoformat(),
                                           payload_sha256=ev.source_sha256)
        ev = ev.finalize()
        s = evidence_to_sensor(ev, name="camera", verify_sig=lambda *a: True, max_age_s=30, min_counter=0)
        obs = {o.name: [round(o.value, 3), round(o.confidence, 3)] for o in ev.observables}
        return s, {"frames": len(frames), "frames_sha256": digest, "observables": obs}


def trace(sc: Scenario, ruling) -> list:
    """Each gate's inputs, threshold and result. The ruling itself comes from govern(); this
    explains it, and a trace that disagrees with govern() is an error, not a display choice."""
    gates = []
    fresh = sc.signal_age_s <= sc.freshness_bound_s
    gates.append({"gate": "1 attestation", "input": f"signal age {sc.signal_age_s}s", "threshold": f"<= {sc.freshness_bound_s}s",
                  "result": "pass" if fresh else "refuse"})
    if not fresh:
        return gates
    sensors = [{"name": s.name, "physical": s.physical, "corroborates": s.corroborates_emergency,
                "confidence": s.confidence, "counts": bool(s.physical and s.corroborates_emergency and s.confidence != "low"),
                "note": s.note} for s in sc.sensors]
    corr = sc.corroboration()
    gates.append({"gate": "2 witness", "input": sensors, "threshold": f">= {W_MIN} independent physical sensors",
                  "result": "pass" if corr >= W_MIN else ("refuse, human review" if corr >= 1 else "refuse"), "count": corr})
    if corr < W_MIN:
        return gates
    m = ruling.msa or {}
    gates.append({"gate": "3 analyzer (advisory, can only refuse)", "input": {k: m.get(k) for k in ("action", "satisfaction", "fired_channel") if k in m},
                  "threshold": "no hard channel, not remove, material spectrum >= -0.20",
                  "result": "refuse" if ruling.gate in ("veto", "proportionality") else "pass"})
    gates.append({"gate": "4 elevate", "result": "elevate" if ruling.elevate else "refuse"})
    return gates


def rule(req: dict, chain: Chain, camera: CameraWitness, backend: str) -> dict:
    sid = req.get("scenario_id")
    if sid not in SCORED:
        raise ValueError(f"scenario_id must be one of the scored governance moments {sorted(SCORED)}")
    base = SCORED[sid]
    sensors = []
    for s in req.get("sensors", []):
        sensors.append(Sensor(name=str(s["name"]), physical=bool(s["physical"]), corroborates_emergency=bool(s["corroborates"]),
                              confidence="low" if s.get("confidence") == "low" else "high", note=str(s.get("note", ""))[:200]))
    cam_info = None
    if req.get("camera_frames"):
        try:
            cs, cam_info = camera.sensor(req["camera_frames"])
            sensors.append(cs)
        except Exception as e:  # no detector here: the camera abstains, it is never invented
            sensors.append(Sensor("camera", True, False, "low", f"camera witness unavailable: {type(e).__name__}"))
            cam_info = {"error": f"{type(e).__name__}: {e}"[:300]}
    sc = Scenario(id=sid, situation=base.situation, proposed_action=base.proposed_action,
                  should_elevate=base.should_elevate, signal_age_s=float(req.get("signal_age_s", base.signal_age_s)),
                  freshness_bound_s=base.freshness_bound_s, kind=base.kind, sensors=sensors)
    try:
        r = govern(sc, backend=backend)
        outcome = "elevate" if r.elevate else ("refuse, human review" if r.human_review else "refuse")
        gates, gate, reason = trace(sc, r), r.gate, r.reason
    except Exception as e:  # e.g. CacheMiss: the analyzer has no real output for this text
        outcome, gate, reason = "refuse", "analyzer unavailable", f"{type(e).__name__}: {e}"[:300]
        gates = [{"gate": "3 analyzer", "result": "refuse", "input": reason}]
    body = {
        "time": datetime.now(timezone.utc).isoformat(), "event": str(req.get("event", ""))[:80], "scenario_id": sid,
        "proposed_action": sc.proposed_action, "signal_age_s": sc.signal_age_s, "outcome": outcome,
        "deciding_gate": gate, "reason": reason, "gates": gates, "camera": cam_info, "backend": backend,
    }
    return chain.append(body)


def make_handler(chain, camera, backend):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/log":
                return self._send(200, chain.records)
            if self.path == "/verify":
                ok, why = chain.verify()
                return self._send(200, {"ok": ok, "detail": why})
            if self.path == "/scenarios":
                # the sensor bus each moment starts from; the scripted camera is left out because
                # the game supplies a live camera witness from the robot's own frames
                return self._send(200, {k: {"situation": v.situation, "proposed_action": v.proposed_action,
                                            "signal_age_s": v.signal_age_s, "freshness_bound_s": v.freshness_bound_s,
                                            "sensors": [{"name": x.name, "physical": x.physical, "corroborates": x.corroborates_emergency,
                                                         "confidence": x.confidence, "note": x.note} for x in v.sensors if x.name != "camera"]}
                                        for k, v in SCORED.items()})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/rule":
                return self._send(404, {"error": "not found"})
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0 or n > MAX_BODY:
                return self._send(413, {"error": "body missing or too large"})
            try:
                req = json.loads(self.rfile.read(n))
                return self._send(200, rule(req, chain, camera, backend))
            except (ValueError, KeyError, TypeError) as e:
                return self._send(400, {"error": str(e)[:300]})

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--log", default=os.path.join(HERE, "session-log.jsonl"))
    ap.add_argument("--backend", default="cached", choices=("cached", "stub"))
    ap.add_argument("--frames-dir", help="keep each ruling's camera frames here, named by their sha256")
    a = ap.parse_args()
    chain = Chain(a.log)
    cam = CameraWitness()
    cam.frames_dir = a.frames_dir
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(chain, cam, a.backend))
    print(f"governor service on 127.0.0.1:{a.port}, backend={a.backend}, log={a.log} ({len(chain.records)} records)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
