"""Build the GTC Prototyping 1-1 check-in deck (Thu 2026-09-10) as a 16:9 PPTX.

Ten support slides for a 30-minute conversation with the GTC team, branded per
docs/brand (golden apple + refracted moral spectrum; flat fills, no gradients).
Illustrations are drawn with native shapes (pipeline, spectrum, four-gate
containment, timeline) plus frames from the twin demos (extracted with ffmpeg).
Every number is a [demonstrated] Charter claim or is labelled in-progress.

    python scripts/build_checkin_pptx.py      # -> out/gtc_checkin_2026-09-10.pptx
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_capsule_pptx import apple_png, mark_png  # noqa: E402  (brand rasters)

# ---- palette (docs/brand/README.md) -----------------------------------------
BG = RGBColor(0x0B, 0x10, 0x20)
PANEL = RGBColor(0x14, 0x1B, 0x2F)
WHITE = RGBColor(0xF2, 0xF5, 0xFA)
MUTE = RGBColor(0x8A, 0x93, 0xA8)
GOLD = RGBColor(0xF5, 0xC1, 0x47)
GREEN = RGBColor(0x3D, 0xDC, 0x97)
AMBER = RGBColor(0xF2, 0xB1, 0x3D)
RED = RGBColor(0xE5, 0x5A, 0x5A)
BLUE = RGBColor(0x4C, 0x8B, 0xF5)
IDENT = RGBColor(0xB8, 0x6B, 0xF5)
RAMP = [RGBColor(*c) for c in [
    (0xF5, 0xC1, 0x47), (0xEC, 0xA8, 0x4C), (0xCF, 0xC7, 0x55), (0x9C, 0xD1, 0x6E),
    (0x6E, 0xD1, 0x8C), (0x62, 0xCB, 0xB0), (0x5B, 0xB8, 0xD8), (0x53, 0xA0, 0xEE),
    (0x4C, 0x8B, 0xF5)]]

OUT = os.path.join("out", "gtc_checkin_2026-09-10.pptx")
FRAMES = os.path.join("out", "checkin_frames")
FONT = "Segoe UI"


# ---- primitives --------------------------------------------------------------
def blank(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    f = s.background.fill
    f.solid()
    f.fore_color.rgb = BG
    return s


def text(slide, s, l, t, w, h, size=20, color=WHITE, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, italic=False, spacing=None):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, line in enumerate(s.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
        r.font.name = FONT
    return tb


def rich(slide, runs_by_line, l, t, w, h, size=16, spacing=1.15, anchor=MSO_ANCHOR.TOP):
    """runs_by_line: list of lines; each line is a list of (text, color, bold)."""
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, line in enumerate(runs_by_line):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = spacing
        p.space_after = Pt(6)
        for (txt, col, bold) in line:
            r = p.add_run()
            r.text = txt
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.color.rgb = col
            r.font.name = FONT
    return tb


def shape(slide, kind, l, t, w, h, fill, line=None, radius=None):
    sp = slide.shapes.add_shape(kind, Inches(l), Inches(t), Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(1.25)
    sp.shadow.inherit = False
    if radius is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        sp.adjustments[0] = radius
    return sp


def rect(slide, l, t, w, h, fill, line=None):
    return shape(slide, MSO_SHAPE.RECTANGLE, l, t, w, h, fill, line)


def rrect(slide, l, t, w, h, fill, line=None, radius=0.12):
    return shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h, fill, line, radius)


def label_in(sp, s, size=14, color=WHITE, bold=False, align=PP_ALIGN.CENTER, sub=None,
             sub_size=11, sub_color=MUTE):
    tf = sp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.08)
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = s
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = FONT
    if sub:
        p2 = tf.add_paragraph()
        p2.alignment = align
        r2 = p2.add_run()
        r2.text = sub
        r2.font.size = Pt(sub_size)
        r2.font.color.rgb = sub_color
        r2.font.name = FONT
    return sp


def chip(slide, s, l, t, w, color, fg=BG, size=12, h=0.36):
    sp = rrect(slide, l, t, w, h, color, radius=0.5)
    label_in(sp, s, size=size, color=fg, bold=True)
    return sp


def arrow(slide, l, t, w, h, color=MUTE):
    sp = shape(slide, MSO_SHAPE.RIGHT_ARROW, l, t, w, h, color)
    return sp


def header(slide, title, kicker=None, n=None):
    if kicker:
        text(slide, kicker.upper(), 0.6, 0.35, 9, 0.35, size=11, color=GOLD, bold=True)
    size = 30 if len(title) <= 48 else (26 if len(title) <= 62 else 22)
    text(slide, title, 0.6, 0.62, 11.2, 0.9, size=size, bold=True)
    slide.shapes.add_picture(apple_png(), Inches(12.2), Inches(0.38), width=Inches(0.62),
                             height=Inches(0.62))
    if n is not None:
        text(slide, f"GTC Prototyping 1-1 · 2026-09-10 · {n}", 0.6, 7.05, 8, 0.3, size=9,
             color=MUTE)


def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s


# ---- demo frames -------------------------------------------------------------
def extract_frames():
    """Pull the illustration frames from the twin demo clips (needs ffmpeg)."""
    os.makedirs(FRAMES, exist_ok=True)
    want = {
        "fall_upright.png": ("twin/gym/fall_demo.mp4", 0),
        "fall_down.png": ("twin/gym/fall_demo.mp4", 30),
        "home_elevate.png": ("twin/gym/home_care_demo.mp4", 120),
        "home_hold.png": ("twin/gym/home_care_demo.mp4", 360),
    }
    ff = shutil.which("ffmpeg")
    for name, (src, frame) in want.items():
        dst = os.path.join(FRAMES, name)
        if os.path.exists(dst) or not ff or not os.path.exists(src):
            continue
        subprocess.run([ff, "-v", "error", "-y", "-i", src, "-vf", f"select=eq(n\\,{frame})",
                        "-vframes", "1", dst], check=False)
    return {k: os.path.join(FRAMES, k) for k in want if os.path.exists(os.path.join(FRAMES, k))}


def picture(slide, path, l, t, w=None, h=None, caption=None):
    if not path or not os.path.exists(path):
        ph = rrect(slide, l, t, w or 4, h or 2.5, PANEL, line=MUTE)
        label_in(ph, "(demo frame — run with ffmpeg)", size=11, color=MUTE)
        return ph
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    pic = slide.shapes.add_picture(path, Inches(l), Inches(t), **kw)
    if caption:
        text(slide, caption, l, t + pic.height / 914400 + 0.05, pic.width / 914400, 0.4,
             size=10.5, color=MUTE, align=PP_ALIGN.CENTER)
    return pic


# ---- illustrations -----------------------------------------------------------
AXES = [  # (label, reliability weight, colour, validated?)  docs/CALIBRATED_AUTHORITY.md
    ("privacy", 0.707, RAMP[0], True), ("environ.", 0.632, RAMP[1], True),
    ("care", 0.625, RAMP[2], True), ("epistemic", 0.621, RAMP[3], True),
    ("identity\nattack", 0.607, IDENT, True), ("fairness", 0.577, RAMP[4], True),
    ("legitimacy", 0.414, RAMP[5], True), ("autonomy", 0.397, RAMP[6], True),
    ("phys. harm", 0.258, RAMP[7], True), ("rights", 0.0, RAMP[8], False),
]


def spectrum(slide, left, top, width, height, show_weights=True):
    """Ten bars = the ten axes, height = registered reliability weight."""
    n = len(AXES)
    slot = width / n
    bw = slot * 0.6
    base = top + height
    rect(slide, left, base, width, 0.02, MUTE)
    for i, (lab, w, col, ok) in enumerate(AXES):
        x = left + i * slot + (slot - bw) / 2
        h = max(0.08, w * (height - 0.5))
        if ok:
            rrect(slide, x, base - h, bw, h, col, radius=0.15)
        else:  # rights: no validated feeder -> hollow bar + hard-channel tag
            sp = rrect(slide, x, base - 0.9, bw, 0.9, BG, line=RED, radius=0.15)
            label_in(sp, "hard\nrule", size=9, color=RED)
        if show_weights and ok:
            text(slide, f"{w:.2f}", x - 0.1, base - h - 0.36, bw + 0.2, 0.3, size=10,
                 color=WHITE, align=PP_ALIGN.CENTER)
        text(slide, ("✓ " if ok else "✗ ") + lab, x - slot * 0.22, base + 0.06, slot * 1.04, 0.6,
             size=9, color=(GREEN if ok else RED), align=PP_ALIGN.CENTER)


def pipeline(slide, top):
    """content -> perception -> spectrum -> contraction -> verdict+residue -> audit proof."""
    steps = [
        ("Content", "text · paraphrase · translation", PANEL, MUTE),
        ("10 validated\nencoders", "each passes a pre-registered\ncross-dataset gate", PANEL, GOLD),
        ("Moral\nspectrum", "energy per axis +\nreliability weight", PANEL, BLUE),
        ("Contraction", "OOF-validated · allow /\nremove / escalate", PANEL, GREEN),
        ("Verdict +\nresidue", "values weighed but\nnot decisive, shown", PANEL, AMBER),
        ("Audit\nproof", "hash-chained ·\nre-verifiable", PANEL, IDENT),
    ]
    n = len(steps)
    x0, gap, w = 0.6, 0.32, (12.1 - 0.32 * (n - 1)) / n
    for i, (t, sub, fill, accent) in enumerate(steps):
        x = x0 + i * (w + gap)
        box = rrect(slide, x, top, w, 1.55, fill, line=accent)
        label_in(box, t, size=15, bold=True, sub=sub, sub_size=10)
        rect(slide, x, top, w, 0.07, accent)
        if i < n - 1:
            arrow(slide, x + w + 0.03, top + 0.62, gap - 0.06, 0.3)


def gates(slide, top):
    """The four-gate structural-containment governor (twin/governor.py)."""
    items = [
        ("1 · Attestation", "read fresh at decision time\n(stale ⇒ refuse)", GOLD),
        ("2 · Witness", "≥ 2 independent PHYSICAL\nsensors corroborate\n(the only channel that can GRANT)", GREEN),
        ("3 · MSA advisory", "moral spectrum can only\nREFUSE a disproportionate act", BLUE),
        ("4 · Elevate", "granted only if 1 and 2 pass\nand 3 does not refuse", IDENT),
    ]
    x0, gap, w = 0.6, 0.3, (12.1 - 0.3 * 3) / 4
    for i, (t, sub, accent) in enumerate(items):
        x = x0 + i * (w + gap)
        box = rrect(slide, x, top, w, 1.7, PANEL, line=accent)
        label_in(box, t, size=15, bold=True, color=accent, sub=sub, sub_size=11, sub_color=WHITE)
        if i < 3:
            arrow(slide, x + w + 0.03, top + 0.7, gap - 0.06, 0.3)


def timeline(slide, top):
    """Jul → Dec GTC phases with a 'today' marker (2026-09-09)."""
    x0, x1 = 0.8, 12.5
    months = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    span = (x1 - x0) / len(months)
    rect(slide, x0, top + 0.55, x1 - x0, 0.06, MUTE)
    phases = [(0, 0.5, "Prep · charter + capsule", GOLD),
              (0.5, 3.5, "Development", BLUE),
              (3.5, 5.2, "Testing & validation", GREEN),
              (5.2, 6.0, "Visibility", IDENT)]
    for a, b, lab, col in phases:
        rrect(slide, x0 + a * span, top + 0.32, (b - a) * span - 0.05, 0.52, col, radius=0.4)
        text(slide, lab, x0 + a * span, top + 0.36, (b - a) * span, 0.45, size=11, color=BG,
             bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    for i, m in enumerate(months):
        text(slide, m, x0 + i * span, top + 0.95, span, 0.3, size=11, color=MUTE)
    tx = x0 + (2 + 9 / 30) * span
    rect(slide, tx, top + 0.1, 0.04, 1.2, RED)
    text(slide, "today · Sep 9", tx - 0.9, top - 0.25, 1.9, 0.3, size=11, color=RED, bold=True,
         align=PP_ALIGN.CENTER)
    mx = x0 + 3.5 * span
    text(slide, "▲ dev ends mid-Oct", mx - 1.0, top + 1.3, 2.0, 0.3, size=10, color=WHITE,
         align=PP_ALIGN.CENTER)
    vx = x0 + 5.2 * span
    text(slide, "▲ validation · early Dec", vx - 1.2, top + 1.3, 2.4, 0.3, size=10, color=WHITE,
         align=PP_ALIGN.CENTER)


# ---- slides ------------------------------------------------------------------
def build():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    frames = extract_frames()

    # 1 · title
    s = blank(prs)
    s.shapes.add_picture(mark_png(), Inches(0.9), Inches(1.0), width=Inches(6.2))
    text(s, "GLOBAL TRUST CHALLENGE · PROTOTYPING 1-1 · 10 SEPTEMBER 2026", 0.9, 4.35, 11, 0.4,
         size=12, color=GOLD, bold=True)
    text(s, "The Moral Spectrum Analyzer", 0.9, 4.7, 11, 0.9, size=40, bold=True)
    text(s, "Auditable, multilingual AI content evaluation — a moral spectrum, not a single score",
         0.9, 5.55, 11.5, 0.5, size=18, color=MUTE)
    text(s, "Entry jRvRdGdd · Geometric Ethics AI Lab · Andrew H. Bond, San José State University",
         0.9, 6.35, 11.5, 0.4, size=13, color=MUTE)
    text(s, "github.com/ahb-sjsu/moral-spectrum-analyzer · pip install moral-spectrum-analyzer",
         0.9, 6.7, 11.5, 0.4, size=12, color=BLUE)
    notes(s, "One line: the analyzer reads a moderation decision as a spectrum across ten validated "
             "moral axes, moderates where validated, escalates and discloses where not, and emits a "
             "hash-chained proof anyone can re-verify.")

    # 2 · where we are
    s = blank(prs)
    header(s, "Where we are on the GTC timeline", "status", 2)
    timeline(s, 1.9)
    rich(s, [
        [("Prep milestones delivered in July: ", WHITE, True),
         ("Charter, 90-second capsule, analyzer end-to-end, package on PyPI.", WHITE, False)],
        [("Five weeks to the end of development. ", WHITE, True),
         ("Everything the Charter marks [demonstrated] reproduces from committed code today; "
          "three of the [committed] items are already met.", WHITE, False)],
        [("What remains is the verification-demo vehicle ", WHITE, True),
         ("(live web demo + audit-verify), the governance annex, the efficiency number, and two "
          "harder measurements (red-team, post-route FPGA timing).", WHITE, False)],
    ], 0.6, 3.75, 12.1, 3.0, size=16)
    notes(s, "Frame the check-in: on track on substance; sequencing the demo vehicle first because "
             "that is what the verification experts touch.")

    # 3 · what the instrument does
    s = blank(prs)
    header(s, "What the prototype does — content in, receipts out", "the instrument", 3)
    pipeline(s, 1.85)
    rich(s, [
        [("Grounded  ", GOLD, True),
         ("every axis traces to an encoder that passed a pre-registered cross-dataset gate — or is "
          "flagged as a hand-specified rule. No badge, no number.", WHITE, False)],
        [("Invariant  ", BLUE, True),
         ("re-description and translation do not move the verdict: decision drift 0.219 on held-out "
          "paraphrases (bar ≤ 0.5), cross-lingual index 0.72–0.80 across es/ar/zh/hi/sw.", WHITE, False)],
        [("Contained  ", GREEN, True),
         ("moderates covered categories where confident (OOF AUROC 0.863), escalates the rest to a "
          "human with the reasons attached, discloses its own coverage limits.", WHITE, False)],
        [("Auditable  ", IDENT, True),
         ("each decision binds inputs, per-axis scores, residue and every encoder's validation record "
          "into a hash chain a third party can re-verify.", WHITE, False)],
    ], 0.6, 3.75, 12.1, 3.2, size=14.5)
    notes(s, "Composes two existing libraries (xbse encoders, erisml-compiler); nothing forked.")

    # 4 · the spectrum
    s = blank(prs)
    header(s, "Ten axes, each with a registered authority",
           "grounded perception · not a binary 'validated' bit · docs/CALIBRATED_AUTHORITY.md", 4)
    rrect(s, 0.6, 1.6, 8.1, 5.3, PANEL, radius=0.05)
    spectrum(s, 0.85, 1.75, 7.6, 4.1)
    text(s, "bar height = reliability weight = max(0, 2·AUROC − 1), from each axis's held-out gate",
         0.85, 6.55, 7.7, 0.35, size=10.5, color=MUTE, align=PP_ALIGN.CENTER)
    rich(s, [
        [("9 of 10 learned axes pass ", GREEN, True), ("the armored gate.", WHITE, False)],
        [("identity_attack ", IDENT, True),
         ("(violet) was discovered by the instrument's own coverage band, validated at held-out AUROC "
          "0.80 [0.78, 0.83], and wired in as the 10th channel. It now carries the largest weight in "
          "the contraction.", WHITE, False)],
        [("rights ", RED, True),
         ("failed its gate twice — most recently on a legal corpus in July — and stays a hand-specified "
          "hard channel. Reported, not hidden.", WHITE, False)],
        [("Since the Charter: ", GOLD, True),
         ("per-axis reliability weights and a 12×12 specificity gate now drive the decision, so a "
          "0.26 axis no longer votes with the authority of a 0.71 axis.", WHITE, False)],
    ], 8.95, 1.7, 3.9, 5.2, size=13)
    notes(s, "Weights: privacy .707, environmental .632, care .625, epistemic .621, identity_attack "
             ".607, fairness .577, legitimacy .414, autonomy .397, physical_harm .258.")

    # 5 · delivered since the charter
    s = blank(prs)
    header(s, "Delivered since the Charter, negative results named", "progress", 5)
    rows = [
        ("Decision drift θ_d ≤ 0.5 at scale", "MET", "0.219 natural · 0.301 harmful (NLLB)", GREEN),
        ("Cross-lingual invariance at scale (5 langs, incl. harmful)", "DONE", "index 0.721 / 0.804, n = 60", GREEN),
        ("Learned contraction — moderate, not just escalate", "WIRED", "OOF AUROC 0.863, leakage-controlled", GREEN),
        ("Discovery loop closed: identity_attack → gate → 10th channel", "DONE", "held-out AUROC 0.80", GREEN),
        ("Calibrated per-axis authority + specificity gate", "ADDED", "not in Charter; strengthens 'grounded'", GOLD),
        ("Adversarial-robustness pre-registration", "COMMITTED", "tighten-only; run is next", AMBER),
        ("Embodiment exhibit: analyzer as robot authority gate (sim)", "NEW", "18/18 scenarios correct", IDENT),
        ("rights_respect re-test on a legal corpus", "FAILED", "stays a hard rule, by evidence", RED),
        ("Register (euphemism) gap survives paraphrase averaging", "LIMITATION", "drives the red-team operator set", RED),
    ]
    y = 1.65
    for (item, tag, ev, col) in rows:
        rrect(s, 0.6, y, 12.1, 0.5, PANEL, radius=0.2)
        text(s, item, 0.8, y + 0.07, 6.6, 0.4, size=13.5)
        chip(s, tag, 7.5, y + 0.08, 1.35, col, size=10, h=0.34)
        text(s, ev, 9.0, y + 0.09, 3.6, 0.4, size=11.5, color=MUTE)
        y += 0.57
    notes(s, "Honesty is the pitch: negative results are in the repo with the same prominence as "
             "positives. Also mention the governor bug we found and documented (over-restriction "
             "0.667 was an escalation-trigger artifact, not a finding).")

    # 6 · embodiment
    s = blank(prs)
    header(s, "The same evaluator as a robot's authority gate",
           "september extension · supporting exhibit · software to silicon", 6)
    text(s, "Defense in depth with a fail-safe default: authority to act comes from corroborated "
            "physical evidence, never from reasoning. Each gate is independent and can only refuse; "
            "if any gate is unsure, the robot holds.", 0.6, 1.42, 12.1, 0.55, size=13, color=MUTE)
    gates(s, 2.15)
    rich(s, [
        [("Why: ", GOLD, True),
         ("a learned evaluator is a gameable surface — an agent can craft a situation that reads as "
          "justified. Sensor corroboration is ground truth it cannot talk its way past. Removing the "
          "analyzer can only make the robot more restrictive.", WHITE, False)],
        [("Two failure modes measured: ", GOLD, True),
         ("false-clear (acted when it should not — the failure that harms) and over-restriction "
          "(refused a real emergency — the failure that neglects). Result on the 18-scenario suite: "
          "0/10 and 0/8.", WHITE, False)],
        [("Path: ", GOLD, True),
         ("P1 simulation (done) → P2 veto/scorer on the U55C FPGA → P3 a physical assistive robot, "
          "human-in-the-loop. P3 is a post-challenge pilot pathway, not a December claim.", WHITE, False)],
    ], 0.6, 4.2, 12.1, 2.8, size=14)
    notes(s, "Sharpest case: routine-med — the analyzer gave 'restrain the patient to administer a "
             "vitamin' its highest satisfaction; the robot refused anyway because authority is not "
             "routed through the evaluator. An evaluator failure contained by the architecture.")

    # 7 · fall demo frames
    s = blank(prs)
    header(s, "The pixels never decide alone",
           "embodiment · attested camera witness + an independent physical sensor", 7)
    H = 2.7
    picture(s, frames.get("fall_upright.png"), 0.6, 1.5, h=H,
            caption="attested stream (ed25519, fresh, monotonic counter) — no corroboration")
    picture(s, frames.get("fall_down.png"), 3.55, 1.5, h=H,
            caption="fall event seen + impact sensor = 2 independent sensors → ELEVATE")
    picture(s, frames.get("home_elevate.png"), 6.5, 1.5, h=H,
            caption="cardiac-real: vitals + wearable corroborate → robot travels to assist")
    picture(s, frames.get("home_hold.png"), 0.6, 4.75, h=1.85, caption=None)
    text(s, "tv-drama: TV audio is not a physical witness → robot holds", 0.6, 6.62, 3.6, 0.3,
         size=9.5, color=MUTE)
    rich(s, [
        [("Push-ups and a fall have the same horizontal posture and opposite verdicts, ", WHITE, True),
         ("because a fall is an event (upright → horizontal) and push-ups are not. Yoga, sleeping, "
          "kneeling, a child on the floor: all held. Found-down-unresponsive, which the camera "
          "missed: caught by impact + wearable.", WHITE, False)],
        [("18-scenario suite: ", GREEN, True),
         ("false-clear 0/10, over-restriction 0/8. A design set that validates the architecture, "
          "not a graded benchmark — the held-out multi-sensor set is the next step.", WHITE, False)],
    ], 4.3, 4.75, 8.4, 2.1, size=12.5)
    notes(s, "Clips: twin/gym/fall_demo.mp4 (4.5 s) and home_care_demo.mp4 (21 s). Character is a "
             "CC0 three.js Soldier posed in Blender; a photoreal character improves prone detection "
             "but does not change the architecture.")

    # 8 · five-week plan
    s = blank(prs)
    header(s, "Five weeks to mid-October: remaining items in ship order", "plan · the Charter's [committed] list", 8)
    plan = [
        ("1", "Live web demo + audit-verify UI", "the verification-demo vehicle: paste → spectrum → decision → re-verify", BLUE),
        ("2", "Governance annex", "mechanism → policy instrument → framework: EU DSA / AI Act, NIST AI RMF, IEEE 7001 (transparency) · 7003 (algorithmic bias) · 7010 (well-being)", GOLD),
        ("3", "Efficiency benchmark", "throughput-per-dollar of small encoders vs LLM-based moderation", GREEN),
        ("4", "Adversarial red-team run", "pre-registered gate; defender frozen, budget fixed; default expectation 'not robust'", AMBER),
        ("5", "Post-route FPGA timing (B3)", "validated clock for the 12-cycle veto → an honest nanosecond number", IDENT),
        ("6", "Like-for-like baseline", "decision-vs-decision drift against a scalar-toxicity baseline", MUTE),
    ]
    y = 1.65
    for (n, t, sub, col) in plan:
        circ = shape(s, MSO_SHAPE.OVAL, 0.7, y + 0.06, 0.55, 0.55, col)
        label_in(circ, n, size=16, color=BG, bold=True)
        text(s, t, 1.45, y, 4.6, 0.45, size=16, bold=True)
        text(s, sub, 1.45, y + 0.38, 10.9, 0.4, size=12, color=MUTE)
        y += 0.8
    rrect(s, 0.6, 6.35, 12.1, 0.55, PANEL, radius=0.3)
    text(s, "Risk: items 5 and 6 are most exposed on a solo timeline. If one slips it is reported as "
            "slipped in the Charter, not quietly dropped. Compute and data are in hand; nothing is blocked.",
         0.8, 6.4, 11.8, 0.5, size=12, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    notes(s, "Sequencing rationale: the demo vehicle is what experts touch in verification; the "
             "annex is writing; the benchmark is cheap; the red-team and timing need Atlas GPU / Vivado time.")

    # 9 · verification demo
    s = blank(prs)
    header(s, "What the verification demo will look like", "verification · December validation", 9)
    steps = [
        ("Paste", "any content — or re-describe / translate it", GOLD),
        ("Spectrum", "ten axes light up, each with a validation badge and its authority weight", BLUE),
        ("Decision", "allow / remove / escalate with violation probability and the moral residue", GREEN),
        ("Re-verify", "one click checks the hash chain and every encoder's validation record", IDENT),
    ]
    x, w = 0.6, 2.9
    for i, (t, sub, col) in enumerate(steps):
        box = rrect(s, x + i * (w + 0.17), 1.7, w, 1.9, PANEL, line=col)
        label_in(box, t, size=20, bold=True, color=col, sub=sub, sub_size=11.5, sub_color=WHITE)
    rich(s, [
        [("Plus: ", GOLD, True),
         ("the spectrogram over a labeled corpus (what the axes can and cannot read), and the robot "
          "exhibit as a two-minute clip.", WHITE, False)],
        [("Conservative by default: ", GOLD, True),
         ("an off-distribution input escalates instead of guessing; every remove carries its out-of-fold "
          "validation. Removes are ~80% precise, so ~1 in 5 is contestable — the audit trail and human "
          "escalation are the safeguard, shown, not hidden.", WHITE, False)],
        [("An open, standardizable artifact: ", GOLD, True),
         ("the audit proof is a documented, hash-chained record (inputs, per-axis scores, residue, "
          "each encoder's validation record) that any third party can re-verify without our code — "
          "the kind of object a transparency standard can name.", WHITE, False)],
        [("Never a fake number: ", GOLD, True),
         ("the demo replays cached real encoder outputs with a live/cached badge; the stub backend is "
          "for CI only and is never presented as real.", WHITE, False)],
        [("Thirty-second fallback today: ", GOLD, True),
         ("msa moderate \"<text>\" --backend cached", BLUE, False)],
    ], 0.6, 3.8, 12.1, 3.3, size=13)
    notes(s, "Ask: what is submitted for verification, by when, in what form — and is a recorded "
             "fallback acceptable alongside the live session?")

    # 10 · asks
    s = blank(prs)
    header(s, "What would help — and what I'd like to ask", "asks", 10)
    asks = [
        ("Verification format", "What is submitted, by when, in what form (live, recorded, repo)? Is the July Charter the reference text, or can an addendum be filed for the embodiment exhibit?"),
        ("Validation session", "Duration, panel composition, whether experts bring their own content."),
        ("Pilot hosting", "A host organization or city for a real-environment pilot: a trust-and-safety team running the analyzer in shadow mode on live moderation traffic, or an assistive-care provider for the elevation scenario. Pre-registered bars, results reported as executed."),
        ("Visibility", "LinkedIn / site promotion timing; whether the capsule can be refreshed before then."),
        ("Honors list", "What 'potential impact in specific real-world contexts' is weighed on, so the governance annex speaks to it."),
    ]
    y = 1.65
    for (t, sub) in asks:
        rrect(s, 0.6, y, 12.1, 0.9, PANEL, radius=0.15)
        rect(s, 0.6, y, 0.09, 0.9, GOLD)
        text(s, t, 0.85, y + 0.08, 3.2, 0.5, size=15, bold=True, color=GOLD)
        text(s, sub, 4.0, y + 0.08, 8.5, 0.8, size=12.5, color=WHITE)
        y += 1.0
    text(s, "Not blocked on anything. Solo PI-led lab, AI-assisted engineering; open to collaboration, "
            "especially on pilots.", 0.6, 6.7, 12.1, 0.4, size=12, color=MUTE)
    notes(s, "Close with the asks; leave the last 8 minutes for their questions.")

    os.makedirs("out", exist_ok=True)
    prs.save(OUT)
    print("wrote", OUT, f"({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
