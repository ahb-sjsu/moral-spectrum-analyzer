#!/usr/bin/env python3
"""Run the scenario suite through the witness pipeline + governor, report a
confusion matrix. Vision comes from the rendered pose clips; each scenario unions
the vision Sensor with its context sensors and elevates only on >=2 corroborating
independent physical sensors.

  CUDA_VISIBLE_DEVICES=1 PYTHONPATH=src:twin python suite_run.py
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


def pose_evidence(pose):
    global _DET
    if _DET is None:
        _DET = _gpu_detector()
    frames = [iio.imread(p)[:, :, :3] for p in sorted(glob.glob(os.path.join(POSE_ROOT, f"pose_{pose}", "f*.png")))]
    if not frames:
        raise SystemExit(f"no frames for pose {pose} in {POSE_ROOT}/pose_{pose}")
    track, ih = _DET(frames)
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

    poses = sorted({s.pose for s in SUITE})
    out(f"encoding pose clips: {poses}")
    POSE_EV = {p: pose_evidence(p) for p in poses}
    for p, ev in POSE_EV.items():
        ft = ev.get("fall_transition"); pp = ev.get("person_present"); bh = ev.get("body_horizontal")
        out(f"  pose {p:8} person={pp.confidence:.2f} horizontal={bh.value:.2f} fall_transition={ft.value:.2f}(c{ft.confidence:.2f})")

    out(f"\n{'id':24}{'kind':15}{'truth':>6}{'rule':>7}{'corr':>5}  corroborating witnesses")
    tp = tn = fp = fn = 0
    for s in SUITE:
        vs = evidence_to_sensor(POSE_EV[s.pose], name="camera", verify_sig=lambda *a: True,
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

    pos = tp + fn; neg = tn + fp
    out(f"\nconfusion: TP={tp} TN={tn} FP={fp} FN={fn}  (emergencies={pos}, non-emergencies={neg})")
    out(f"false-clear (elevated a non-emergency) = {fp}/{neg} = {fp/max(neg,1):.3f}")
    out(f"over-restriction (refused an emergency) = {fn}/{pos} = {fn/max(pos,1):.3f}")
    out("ALL CORRECT" if fp == 0 and fn == 0 else "SOME MISSES -- see above")

    with open(os.path.join(HERE, "SUITE-REPORT.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
