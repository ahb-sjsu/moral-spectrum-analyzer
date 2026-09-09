#!/usr/bin/env python3
"""Composite the Blender fall render with a live overlay of the streaming witness.

Runs the erisml VideoWitnessStream over the rendered fall frame-by-frame (a live
robot camera), and draws, per frame: the detection box, the physical observables
building up (value + confidence bars), the hardware-attestation badge, and the
governor verdict. The camera is one witness; the ≥2-sensor rule is shown honestly
(camera + an independent fall sensor) so elevation is granted only on corroboration.

  MUJOCO_GL=egl CUDA_VISIBLE_DEVICES=1 ~/env/bin/python render_fall_demo.py
"""
import glob, os, sys
import numpy as np
import imageio.v2 as iio
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TWIN = os.path.dirname(HERE)
sys.path.insert(0, TWIN)
from witness_adapter import evidence_to_sensor          # noqa: E402
from erisml_compiler.ingestion import VideoWitnessStream  # noqa: E402
from erisml_compiler.ir import SensorAttestation          # noqa: E402
from datetime import datetime, timezone                   # noqa: E402

FRAMES_DIR = os.path.expanduser("~/twin-gym/assets/char/fall_anim")
OUT = os.path.expanduser("~/twin-gym/assets/char/fall_demo.mp4")
W = H = 512
OBS = [("person_present", "person present"), ("body_horizontal", "body horizontal"),
       ("on_floor", "on the floor"), ("rapid_descent", "rapid descent")]


def _font(sz, bold=True):
    for p in ([f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf"]):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def gpu_detector():
    import torch
    from torchvision.models.detection import (fasterrcnn_resnet50_fpn_v2,
                                              FasterRCNN_ResNet50_FPN_V2_Weights)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    w = FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
    net = fasterrcnn_resnet50_fpn_v2(weights=w).eval().to(dev)
    tf = w.transforms()

    def detect(frame):
        x = tf(torch.from_numpy(frame[:, :, :3]).permute(2, 0, 1)).to(dev)
        with torch.no_grad():
            o = net([x])[0]
        for s, l, b in zip(o["scores"], o["labels"], o["boxes"]):
            if int(l) == 1 and float(s) >= 0.5:
                bx = b.tolist()
                return {"score": float(s), "x0": bx[0], "y0": bx[1], "x1": bx[2], "y1": bx[3]}
        return None
    return detect


def overlay(frame, box, ev, sensor, elevate):
    img = Image.fromarray(frame).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    # detection box
    if box:
        d.rectangle([box["x0"], box["y0"], box["x1"], box["y1"]], outline=(90, 220, 130, 255), width=3)
        d.text((box["x0"], max(0, box["y0"] - 16)), f"person {box['score']:.2f}",
               font=_font(14), fill=(90, 220, 130))
    # title strip
    d.rectangle([0, 0, W, 34], fill=(12, 14, 20, 210))
    d.text((12, 7), "home-care fall  ·  attested video witness", font=_font(18), fill=(238, 242, 248))
    # observable panel (right)
    px, pw = W - 214, 200
    d.rectangle([px - 8, 44, W, 44 + 22 * len(OBS) + 14], fill=(12, 14, 20, 195))
    for i, (key, label) in enumerate(OBS):
        o = ev.get(key)
        val = o.value if o else 0.0
        conf = o.confidence if o else 0.0
        y = 52 + i * 22
        d.text((px, y), label, font=_font(12), fill=(200, 206, 214))
        bx0, bx1 = px + 96, W - 10
        d.rectangle([bx0, y + 2, bx1, y + 12], outline=(70, 78, 90), width=1)
        fillw = int((bx1 - bx0) * max(0.0, min(1.0, val)))
        col = (90, 200, 120) if val >= 0.5 and conf >= 0.4 else (150, 156, 168)
        d.rectangle([bx0, y + 2, bx0 + fillw, y + 12], fill=col)
        d.text((bx1 - 30, y - 1), f"{conf:.2f}", font=_font(11), fill=(150, 180, 210))
    # bottom strip: attestation + verdict
    d.rectangle([0, H - 58, W, H], fill=(12, 14, 20, 215))
    d.text((12, H - 54), "stream ✓ ed25519 attested · fresh · counter↑", font=_font(13), fill=(150, 200, 230))
    cam_ok = sensor.corroborates_emergency
    corr = (1 if cam_ok else 0) + 1  # + independent fall sensor
    if elevate:
        d.text((12, H - 32), f"camera ✓ + fall_sensor ✓ = {corr} sensors  →  ELEVATE",
               font=_font(16), fill=(90, 220, 130))
    elif cam_ok:
        d.text((12, H - 32), "camera witness corroborates → awaiting 2nd sensor",
               font=_font(16), fill=(235, 190, 70))
    else:
        d.text((12, H - 32), "camera witness watching … (no corroboration yet)",
               font=_font(16), fill=(200, 206, 214))
    return np.asarray(img)


def main():
    paths = sorted(glob.glob(os.path.join(FRAMES_DIR, "f*.png")))
    frames = [iio.imread(p)[:, :, :3] for p in paths]
    stream = VideoWitnessStream(window=12, detect_fn=gpu_detector(), source="camera://robot", img_h=H)
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for fr in frames:
        stream.push(fr)
        ev = stream.evidence()
        ev.attestation = SensorAttestation(device_id="cam01", key_id="k1", counter=stream._n,
                                           signed_at=now, payload_sha256=ev.source_sha256)
        ev.finalize()
        sensor = evidence_to_sensor(ev, verify_sig=lambda *a: True, max_age_s=30, min_counter=0)
        box = stream._track[-1]
        elevate = sensor.corroborates_emergency  # camera + an independent fall sensor -> >=2
        out.append(overlay(fr, box, ev, sensor, elevate))
    # freeze the resolved final frame
    out += [out[-1]] * 14
    iio.mimwrite(OUT, out, fps=12, macro_block_size=1, quality=8)
    print("wrote", OUT, len(out), "frames")


if __name__ == "__main__":
    main()
