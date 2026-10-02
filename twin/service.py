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
from scenarios_suite import SUITE  # noqa: E402
from moral_spectrum.audit import canonical_json  # noqa: E402

SCORED = {s.id: s for s in SCENARIOS}
# the witness suite's false alarms, for the robot's checks when Margaret is on the floor for an
# ordinary reason; their situation texts were never scored, so if a forged bus ever carried one
# of them past the witness gate, the analyzer has no real output and the ruling is a refusal
CHECKS = {s.id: s for s in SUITE if s.kind == "false-alarm"}
CHECK_ACTION = "Call emergency services and stay with the patient."
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
            body.setdefault("time", datetime.now(timezone.utc).isoformat())
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

    frames_dir = None  # when set, each ruling's frames are kept under their sha256, for review

    def sensor(self, frames_b64):
        import numpy as np
        from PIL import Image
        from witness_adapter import evidence_to_sensor
        from erisml_compiler.ingestion import encode_video
        from erisml_compiler.ir import SensorAttestation

        frames = [np.asarray(Image.open(io.BytesIO(base64.b64decode(b))).convert("RGB")).copy() for b in frames_b64[:MAX_FRAMES]]
        track, contact = self.detect(frames)
        ih = frames[0].shape[0] if frames else 512
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
        obs["person_animal_contact"] = [round(contact, 3), 1.0]
        # a fall event, or a person and an animal in contact in at least a third of the frames
        # (an attack in progress), corroborates; either is still only one witness of two
        if not s.corroborates_emergency and contact >= 1 / 3 and obs.get("person_present", [0, 0])[1] >= 0.5:
            s = Sensor("camera", True, True, "high", f"video witness: person and animal in contact in {contact:.0%} of frames")
        return s, {"frames": len(frames), "frames_sha256": digest, "observables": obs}

    def detect(self, frames):
        """One detector pass per frame: the best person box (the track the video witness reads, as
        in suite_run.py) and whether a person box and a dog or cat box overlap."""
        import torch
        from torchvision.models.detection import FasterRCNN_ResNet50_FPN_V2_Weights, fasterrcnn_resnet50_fpn_v2

        if getattr(self, "_det", None) is None:
            w = FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
            dev = "cuda" if torch.cuda.is_available() else "cpu"
            self._det = (fasterrcnn_resnet50_fpn_v2(weights=w).eval().to(dev), w.transforms(), dev)
        net, tf, dev = self._det
        track, hits = [], 0
        for fr in frames:
            with torch.no_grad():
                o = net([tf(torch.from_numpy(fr).permute(2, 0, 1)).to(dev)])[0]
            dets = [(int(lab), float(sc), b.tolist()) for b, lab, sc in zip(o["boxes"], o["labels"], o["scores"], strict=True)]
            people = [d for d in dets if d[0] == 1 and d[1] >= 0.5]
            animals = [d for d in dets if d[0] in (17, 18) and d[1] >= 0.5]
            p = people[0] if people else None  # boxes come sorted by score
            track.append({"score": p[1], "x0": p[2][0], "y0": p[2][1], "x1": p[2][2], "y1": p[2][3]} if p else None)
            if any(min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]) for _, _, a in people for _, _, b in animals):
                hits += 1
        return track, hits / max(len(frames), 1)


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
    if sid in SCORED:
        base = SCORED[sid]
    elif sid in CHECKS:
        c = CHECKS[sid]
        base = Scenario(id=c.id, situation=c.note, proposed_action=CHECK_ACTION, should_elevate=False,
                        signal_age_s=1, freshness_bound_s=30, kind=c.kind)
    else:
        raise ValueError(f"scenario_id must be a scored moment {sorted(SCORED)} or a suite check {sorted(CHECKS)}")
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
        outcome, gate = "refuse", "analyzer unavailable"
        reason = f"no real analyzer output for this situation, so no score is invented: {type(e).__name__}"[:300]
        gates = [{"gate": "3 analyzer", "result": "refuse", "input": reason}]
    body = {
        "time": datetime.now(timezone.utc).isoformat(), "event": str(req.get("event", ""))[:80], "scenario_id": sid,
        "proposed_action": sc.proposed_action, "signal_age_s": sc.signal_age_s, "outcome": outcome,
        "deciding_gate": gate, "reason": reason, "gates": gates, "camera": cam_info, "backend": backend,
    }
    return chain.append(body)


def make_handler(chain, camera, backend, brain=None):
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
                                        for k, v in SCORED.items()}
                                       | {k: {"situation": v.note, "proposed_action": CHECK_ACTION, "signal_age_s": 1, "freshness_bound_s": 30, "check": True,
                                              "sensors": [{"name": x.name, "physical": x.physical, "corroborates": x.corroborates_emergency,
                                                           "confidence": x.confidence, "note": x.note} for x in v.context]}
                                          for k, v in CHECKS.items()})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path == "/reset":
                if brain is None:
                    return self._send(503, {"error": "the autonomous brain is not running"})
                brain.reset()
                return self._send(200, chain.append({"kind": "reset", "moral_state": brain.agent.rt.machine_states()}))
            if self.path in ("/decide", "/reflex", "/performed", "/event", "/center", "/ems", "/margaret"):
                if brain is None:
                    return self._send(503, {"error": "the autonomous brain is not running (start with --scene)"})
                n = int(self.headers.get("Content-Length", "0"))
                if n <= 0 or n > MAX_BODY:
                    return self._send(413, {"error": "body missing or too large"})
                try:
                    req = json.loads(self.rfile.read(n))
                    if self.path == "/decide":
                        cam, info = None, None
                        if req.get("camera_frames"):
                            try:
                                cam, info = camera.sensor(req["camera_frames"])
                            except Exception as e:  # no detector: the camera abstains, never invented
                                cam = Sensor("camera", True, False, "low", f"camera witness unavailable: {type(e).__name__}")
                        body = brain.decide(req, cam)
                        body["camera"] = info
                    elif self.path == "/reflex":
                        # no model: the scene's reflexes on this perception update; nothing is
                        # logged when none fires
                        cam, info = None, None
                        if req.get("camera_frames"):
                            try:
                                cam, info = camera.sensor(req["camera_frames"])
                            except Exception as e:  # no detector: the camera abstains, never invented
                                cam = Sensor("camera", True, False, "low", f"camera witness unavailable: {type(e).__name__}")
                        body = brain.reflex(req, cam)
                        if body is None:
                            return self._send(200, {"fired": False})
                        body["camera"] = info
                    elif self.path == "/performed":
                        body = brain.performed(str(req["action"]))
                    elif self.path == "/center":
                        body = brain.center.decide(dict(req["facts"]))
                    elif self.path == "/ems":
                        body = brain.ems.decide(dict(req["facts"]))
                    elif self.path == "/margaret":
                        body = brain.margaret.reply(dict(req))
                    else:
                        body = brain.event(dict(req["event"]))
                    return self._send(200, chain.append(body))
                except (ValueError, KeyError, TypeError) as e:
                    return self._send(400, {"error": str(e)[:300]})
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
    ap.add_argument("--scene", help="ErisML scene; starts the autonomous brain (needs ERISML_LLM_API_KEY)")
    ap.add_argument("--live", help="score new situations with the validated feeders; a session cache file")
    ap.add_argument("--llm-model", default=os.environ.get("ERISML_LLM_MODEL", "gpt-oss"))
    ap.add_argument("--onboard-url", help="the robot's on-robot model (an OpenAI-compatible endpoint), its tier 2")
    ap.add_argument("--onboard-model", help="the on-robot model's name at that endpoint")
    a = ap.parse_args()
    chain = Chain(a.log)
    cam = CameraWitness()
    cam.frames_dir = a.frames_dir
    brain = None
    if a.scene:
        import shutil

        from brain import BigOutputAdapter, Brain
        from erisml_compiler.annotation.llm_extractor import NRPOpenAIAdapter

        scorer = None
        if a.live:
            # the session cache starts from the recorded scores and grows with live ones
            repo_cache = os.path.join(os.path.dirname(HERE), "src", "moral_spectrum", "perception", "cache.jsonl")
            if not os.path.exists(a.live):
                shutil.copy(repo_cache, a.live)
            os.environ["MSA_CACHE_PATH"] = os.path.abspath(a.live)
            from msa_live import LiveScorer

            scorer = LiveScorer(a.live)
        from cascade import Cascade, twin_experts

        robot = Cascade(twin_experts(a.llm_model, a.onboard_url, a.onboard_model))
        brain = Brain(a.scene, robot, scorer, desk_adapter=BigOutputAdapter(NRPOpenAIAdapter(model=a.llm_model)))
        print(f"brain: scene {a.scene}, robot tiers {[e.name for e in robot.all.experts.values()]} + compiled, "
              f"live scoring {'on' if scorer else 'off'}", flush=True)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(chain, cam, a.backend, brain))
    print(f"governor service on 127.0.0.1:{a.port}, backend={a.backend}, log={a.log} ({len(chain.records)} records)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
