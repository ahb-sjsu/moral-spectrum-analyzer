#!/usr/bin/env python3
"""Render the home-care twin as a MuJoCo demo video.

Each of the eight scenarios is played as a short clip: the emergency read
appears, the MSA-governor rules, and the robot's body does exactly what the
ruling permits -- it acts (travels to the target and reaches) only when the
governor elevates; otherwise it holds and defers. The decisions are the sealed
cached-backend record (twin_results_cached.json), so the video is faithful to
the committed result: only fall-fresh-assist elevates; the two hardest real
emergencies are refused by the regime gate (the honest over-restriction finding).

Headless EGL render -> frames -> mp4. Run on Atlas:
  MUJOCO_GL=egl CUDA_VISIBLE_DEVICES=1 ~/env/bin/python render_demo.py
"""
import json, os, sys
import numpy as np
import mujoco
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TWIN = os.path.dirname(HERE)
W, H, FPS = 960, 540, 30

# home pose and per-scenario targets (where the robot would go to act)
HOME = np.array([-1.15, -0.3])     # neutral standby, mid-scene (robot visible even when holding)
PATIENT = np.array([1.4, -0.55])   # stand just short of the patient body
CABINET = np.array([-1.6, 0.95])   # stand just short of the cabinet
TARGET = {
    "fall-real": PATIENT, "cardiac-real": PATIENT, "fall-fresh-assist": PATIENT,
    "routine-med": CABINET, "tv-drama": PATIENT, "spoofed": PATIENT,
    "stale-clear": PATIENT, "ambiguous": PATIENT,
}
# which scenarios show the patient collapsed on the floor
FALLEN = {"fall-real", "fall-fresh-assist", "tv-drama", "spoofed"}

GATE_LABEL = {
    "attestation": "REFUSE (stale read)",
    "witness": "CONTAINED (no sensor proof)",
    "veto": "VETO (hard channel)",
    "proportionality": "REFUSE (disproportionate)",
    "elevate": "ELEVATE (sensors corroborate)",
}


def _font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def overlay(frame, sc, r, phase):
    img = Image.fromarray(frame)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, 92], fill=(12, 14, 20, 205))
    d.rectangle([0, H - 70, W, H], fill=(12, 14, 20, 205))
    elevate = r["elevate"]
    acted = elevate and phase == "act"
    d.text((18, 10), f"{sc}", font=_font(30), fill=(240, 244, 250))
    truth = "real emergency" if r["should_elevate"] else "non-emergency"
    d.text((18, 52), f"ground truth: {truth}", font=_font(20), fill=(150, 200, 230))
    # ruling badge
    label = GATE_LABEL.get(r["gate"], r["gate"])
    col = (90, 210, 120) if elevate else ((235, 170, 60) if r["gate"] in ("witness", "attestation") else (230, 90, 90))
    d.text((W - 18 - d.textlength(label, font=_font(26)), 14), label, font=_font(26), fill=col)
    ok = "ruling matches truth" if r["correct"] else "MISS vs truth"
    okcol = (150, 220, 160) if r["correct"] else (235, 150, 150)
    d.text((W - 18 - d.textlength(ok, font=_font(18)), 52), ok, font=_font(18), fill=okcol)
    # bottom: the reason + what the body is doing
    reason = r["reason"]
    reason = reason if len(reason) < 92 else reason[:89] + "..."
    d.text((18, H - 60), reason, font=_font(17), fill=(210, 214, 222))
    body = "robot ACTS (elevation granted)" if acted else (
        "robot travels to assist" if (elevate and phase == "travel") else "robot HOLDS -- fail-safe default")
    d.text((18, H - 32), body, font=_font(18), fill=(col if acted else (180, 186, 196)))
    return np.asarray(img)


def clip(model, data, renderer, sc, r, seconds=(0.5, 1.1, 1.0)):
    """Yield rendered frames for one scenario: settle, travel/hold, act/hold."""
    jbx, jby = model.joint("bx").qposadr[0], model.joint("by").qposadr[0]
    jarm = model.joint("arm_lift").qposadr[0]
    jfall = model.joint("p_fall").qposadr[0]
    data.qpos[:] = 0
    data.qpos[jbx], data.qpos[jby] = HOME
    data.qpos[jfall] = 1.45 if sc in FALLEN else 0.0
    tgt = TARGET[sc]
    n0, n1, n2 = (int(s * FPS) for s in seconds)

    # phase 0: settle / read appears
    for _ in range(n0):
        mujoco.mj_forward(model, data)
        renderer.update_scene(data, camera="cam")
        yield overlay(renderer.render(), sc, r, "settle")

    # phase 1: travel to target if elevating, else hold
    for i in range(n1):
        a = (i + 1) / n1
        if r["elevate"]:
            data.qpos[jbx], data.qpos[jby] = HOME + a * (tgt - HOME)
        mujoco.mj_forward(model, data)
        renderer.update_scene(data, camera="cam")
        yield overlay(renderer.render(), sc, r, "travel")

    # phase 2: act (reach) if elevating, else keep holding
    for i in range(n2):
        a = (i + 1) / n2
        if r["elevate"]:
            data.qpos[jarm] = -1.2 * min(1.0, a)      # lower the arm toward the patient/cabinet
        mujoco.mj_forward(model, data)
        renderer.update_scene(data, camera="cam")
        yield overlay(renderer.render(), sc, r, "act" if r["elevate"] else "hold")


def main():
    rec = json.load(open(os.path.join(TWIN, "twin_results_cached.json")))
    rulings = {r["scenario_id"]: r for r in rec["rulings"]}
    order = ["fall-real", "cardiac-real", "fall-fresh-assist", "routine-med",
             "tv-drama", "spoofed", "stale-clear", "ambiguous"]

    model = mujoco.MjModel.from_xml_path(os.path.join(HERE, "home_care.xml"))
    data = mujoco.MjData(model)
    renderer = mujoco.Renderer(model, height=H, width=W)

    out = os.path.join(HERE, "home_care_demo.mp4")
    writer = imageio.get_writer(out, fps=FPS, macro_block_size=1, quality=8)
    nfr = 0
    for sc in order:
        r = rulings[sc]
        for frame in clip(model, data, renderer, sc, r):
            writer.append_data(frame)
            nfr += 1
        # short beat between clips (freeze last)
    writer.close()
    fc = rec["false_clear_rate"]; orr = rec["over_restriction_rate"]
    print(f"wrote {out}  ({nfr} frames, {nfr/FPS:.1f}s)  "
          f"fc={fc} or={orr}  elevated={[k for k,v in rulings.items() if v['elevate']]}")


if __name__ == "__main__":
    main()
