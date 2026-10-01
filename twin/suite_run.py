#!/usr/bin/env python3
"""Run the scenario suite through the witness pipeline + governor, report a
confusion matrix. Vision comes from the rendered pose clips; each scenario unions
the vision Sensor with its context sensors and elevates only on >=2 corroborating
independent physical sensors.

  CUDA_VISIBLE_DEVICES=1 PYTHONPATH=src:twin python suite_run.py

CLIP_KEY=id reads one clip per scenario (POSE_ROOT/pose_<scenario id>, the layout the Unity
renderer of docs/TWIN_3D_PLAN.md writes) instead of the six shared pose clips, and SUITE_REPORT
names the report file. The rule is the same either way.
"""
import glob, os, sys
import imageio.v2 as iio
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scenarios_suite import SUITE                     # noqa: E402
from witness_adapter import evidence_to_sensor        # noqa: E402
from erisml_compiler.ingestion import encode_video    # noqa: E402
from erisml_compiler.ir import SensorAttestation      # noqa: E402

POSE_ROOT = os.path.expanduser(os.environ.get("POSE_ROOT", "~/twin-gym/assets/char"))
CLIP_KEY = os.environ.get("CLIP_KEY", "pose")  # "pose": shared pose clips; "id": one clip per scenario
REPORT = os.environ.get("SUITE_REPORT", "SUITE-REPORT.txt")
W_MIN = 2


def _gpu_detector():
    import torch
    from torchvision.models.detection import (fasterrcnn_resnet50_fpn_v2,
                                              FasterRCNN_ResNet50_FPN_V2_Weights)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    w = FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
    net = fasterrcnn_resnet50_fpn_v2(weights=w).eval().to(dev)
    tf = w.transforms()

    def track(frames):
        out = []
        for fr in frames:
            x = tf(torch.from_numpy(fr[:, :, :3]).permute(2, 0, 1)).to(dev)
            with torch.no_grad():
                o = net([x])[0]
            best = None
            for s, l, b in zip(o["scores"], o["labels"], o["boxes"]):
                if int(l) == 1 and float(s) >= 0.5:
                    bx = b.tolist()
                    best = {"score": float(s), "x0": bx[0], "y0": bx[1], "x1": bx[2], "y1": bx[3]}
                    break
            out.append(best)
        return out, (frames[0].shape[0] if frames else 512)
    return track


_DET = None
_TRACKS = {}


def pose_evidence(pose):
    """The camera's evidence for one clip, attested now.

    The detector runs once per clip and its track is cached; the attestation is stamped each
    time the evidence is built. Build it immediately before the ruling that reads it: a reading
    attested when the whole suite was encoded goes stale (over max_age_s) before the later
    rulings, and the freshness check then rightly refuses it (run 1 of the 3D suite).
    """
    global _DET
    if pose not in _TRACKS:
        if _DET is None:
            _DET = _gpu_detector()
        frames = [iio.imread(p)[:, :, :3] for p in sorted(glob.glob(os.path.join(POSE_ROOT, f"pose_{pose}", "f*.png")))]
        if not frames:
            raise SystemExit(f"no frames for pose {pose} in {POSE_ROOT}/pose_{pose}")
        _TRACKS[pose] = _DET(frames)
    track, ih = _TRACKS[pose]
    # feed the GPU-computed track through the stub backend -> identical observables, fast
    ev = encode_video(f"pose://{pose}", backend="stub", stub_track=track, img_h=ih)
    ev.attestation = SensorAttestation(device_id="cam01", key_id="k1", counter=7,
                                       signed_at=datetime.now(timezone.utc).isoformat(),
                                       payload_sha256=ev.source_sha256)
    return ev.finalize()


def corroboration(sensors):
    seen = set()
    for s in sensors:
        if s.physical and s.corroborates_emergency and s.confidence != "low":
            seen.add(s.name)
    return seen


def main():
    L = []
    def out(s=""):
        print(s, flush=True); L.append(s)

    clip = (lambda s: s.id) if CLIP_KEY == "id" else (lambda s: s.pose)
    poses = sorted({clip(s) for s in SUITE})
    out(f"encoding clips ({CLIP_KEY}) from {POSE_ROOT}: {poses}")
    POSE_EV = {p: pose_evidence(p) for p in poses}
    for p, ev in POSE_EV.items():
        ft = ev.get("fall_transition"); pp = ev.get("person_present"); bh = ev.get("body_horizontal")
        def v(o, attr):  # an observable the detector could not produce is reported, not assumed
            return "n/a" if o is None else f"{getattr(o, attr):.2f}"
        out(f"  clip {p:24} person={v(pp, 'confidence')} horizontal={v(bh, 'value')} "
            f"fall_transition={v(ft, 'value')}(c{v(ft, 'confidence')})")

    out(f"\n{'id':24}{'kind':15}{'truth':>6}{'rule':>7}{'corr':>5}  corroborating witnesses")
    tp = tn = fp = fn = 0
    for s in SUITE:
        vs = evidence_to_sensor(pose_evidence(clip(s)),  # attested at ruling time name="camera", verify_sig=lambda *a: True,
                                max_age_s=30, min_counter=0)
        sensors = list(s.context) + [vs]
        corr = corroboration(sensors)
        elevate = len(corr) >= W_MIN
        ok = elevate == s.should_elevate
        tp += elevate and s.should_elevate
        tn += (not elevate) and (not s.should_elevate)
        fp += elevate and (not s.should_elevate)
        fn += (not elevate) and s.should_elevate
        mark = "" if ok else "  <-- MISS"
        out(f"{s.id:24}{s.kind:15}{('ELEV' if s.should_elevate else 'hold'):>6}"
            f"{('ELEV' if elevate else 'hold'):>7}{len(corr):>5}  {','.join(sorted(corr)) or '(none)'}{mark}")
        out(f"{'':24}camera: {vs.note}")

    pos = tp + fn; neg = tn + fp
    out(f"\nconfusion: TP={tp} TN={tn} FP={fp} FN={fn}  (emergencies={pos}, non-emergencies={neg})")
    out(f"false-clear (elevated a non-emergency) = {fp}/{neg} = {fp/max(neg,1):.3f}")
    out(f"over-restriction (refused an emergency) = {fn}/{pos} = {fn/max(pos,1):.3f}")
    out("ALL CORRECT" if fp == 0 and fn == 0 else "SOME MISSES -- see above")

    with open(os.path.join(HERE, REPORT), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
