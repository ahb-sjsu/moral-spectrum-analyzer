"""Build the GTC Information Capsule as a self-running, narrated 16:9 PPTX.

Renders the 8-shot storyboard in docs/CAPSULE.md: dark deck, the recurring
moral-spectrum bar motif, on-slide text, the voiceover in speaker notes, a fade
transition + per-shot auto-advance timing (so it self-runs to ~90 s). PowerPoint
entrance animations (bar-grow, badge-pop, typewriter) are added in-app; each
slide's speaker notes carry its animation cue.

    python scripts/build_capsule_pptx.py            # -> out/capsule.pptx
Export the video in PowerPoint: File > Export > Create a Video (use recorded
timings/narration) -> capsule.mp4.
"""
from __future__ import annotations

import os

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

# ---- palette ----------------------------------------------------------------
BG = RGBColor(0x0B, 0x10, 0x20)
WHITE = RGBColor(0xF2, 0xF5, 0xFA)
MUTE = RGBColor(0x8A, 0x93, 0xA8)
GREEN = RGBColor(0x3D, 0xDC, 0x97)   # validated / accent
AMBER = RGBColor(0xF2, 0xB1, 0x3D)   # escalate
RED = RGBColor(0xE5, 0x5A, 0x5A)     # remove
RAMP = [RGBColor(*c) for c in [
    (0x4C, 0x8B, 0xF5), (0x53, 0xA0, 0xEE), (0x5B, 0xB8, 0xD8), (0x62, 0xCB, 0xB0),
    (0x6E, 0xD1, 0x8C), (0x9C, 0xD1, 0x6E), (0xCF, 0xC7, 0x55), (0xEC, 0xA8, 0x4C),
    (0xE8, 0x82, 0x50)]]
IDENT = RGBColor(0xB8, 0x6B, 0xF5)   # identity-attack (violet, the discovered axis)

# short axis labels (canonical DEME9 + discovered 10th)
AX9 = ["harm", "rights", "fairness", "autonomy", "privacy",
       "environ", "care", "legitimacy", "epistemic"]
AX10 = AX9 + ["identity‑attack"]

# per-shot advance seconds (sums to 90)
TIMING = [11, 12, 12, 14, 12, 13, 10, 6]

EMU_IN = 914400


def _blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def bg(slide):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = BG


def text(slide, s, l, t, w, h, size=28, color=WHITE, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False, spacing=None):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
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
        r.font.name = "Segoe UI"
    return tb


def rect(slide, l, t, w, h, color, line=False):
    sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t),
                                Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = color
    if line:
        sp.line.color.rgb = color
    else:
        sp.line.fill.background()
    sp.shadow.inherit = False
    return sp


def chip(slide, s, l, t, w, color, fg=WHITE, size=20):
    sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t),
                                Inches(w), Inches(0.55), )
    sp.fill.solid(); sp.fill.fore_color.rgb = color; sp.line.fill.background()
    sp.shadow.inherit = False
    tf = sp.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = s; r.font.size = Pt(size); r.font.bold = True
    r.font.color.rgb = fg; r.font.name = "Segoe UI"
    return sp


def bars(slide, heights, labels, highlight=None, badges=False,
         base_y=6.1, max_h=3.2, left=1.15, right=12.2):
    n = len(heights)
    span = right - left
    slot = span / n
    bw = slot * 0.62
    for i, (hgt, lab) in enumerate(zip(heights, labels)):
        x = left + i * slot + (slot - bw) / 2
        h = max(0.06, hgt * max_h)
        col = IDENT if (labels[i].startswith("identity")) else RAMP[i % len(RAMP)]
        if highlight is not None and i != highlight and highlight >= 0:
            pass
        rect(slide, x, base_y - h, bw, h, col)
        if badges:
            text(slide, "✓", x, base_y - h - 0.42, bw, 0.4, size=16,
                 color=GREEN, align=PP_ALIGN.CENTER)
        text(slide, lab, x - slot * 0.15, base_y + 0.06, slot * 0.9, 0.5,
             size=10.5, color=MUTE, align=PP_ALIGN.CENTER)


def notes(slide, vo, cue):
    tf = slide.notes_slide.notes_text_frame
    tf.text = f"VOICEOVER:\n{vo}\n\nANIMATION CUE:\n{cue}"


def advance(slide, seconds):
    """Fade transition + auto-advance after `seconds` (click also advances)."""
    sld = slide._element
    for old in sld.findall(qn("p:transition")):
        sld.remove(old)
    tr = etree.SubElement(sld, qn("p:transition"))
    tr.set("spd", "med")
    tr.set("advClick", "1")
    tr.set("advTm", str(int(seconds * 1000)))
    etree.SubElement(tr, qn("p:fade"))


def build(path="out/capsule.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    VO = [
        "Every day, automated systems decide what billions of people can and can't say. "
        "Most reduce that judgment — a moral one — to a single number. A toxicity score.",
        "But one number can't tell you which value it acted on. It shifts when you reword the "
        "same sentence. And worst of all — it can't tell you what it fails to see.",
        "So we built the Moral Spectrum Analyzer. It reads content not as one score, but as a "
        "spectrum — the energy across nine distinct moral dimensions.",
        "Feed it a line of content. Each axis lights up — harm, fairness, cruelty, a targeted "
        "identity attack — and every one carries a badge showing it was independently validated. "
        "No badge, no number.",
        "Out comes a decision — allow, remove, or escalate to a human — with its moral "
        "residue: the values it weighed but didn't act on. Nothing hidden.",
        "Nine of ten axes pass a pre-registered validation gate. Reword the sentence, or translate "
        "it across five languages — the verdict holds, where a single score would drift. And "
        "every decision emits a proof you can re-verify.",
        "It even discovered a moral dimension the standard taxonomy was missing — identity "
        "attack — and validated it. And when it can't read something? It says so.",
        "The Moral Spectrum Analyzer. Trust — made measurable.",
    ]

    # --- Shot 1: the lone number ---
    s = _blank(prs); bg(s)
    text(s, "0.82", 0, 2.1, 13.333, 2.0, size=140, color=MUTE, bold=True,
         align=PP_ALIGN.CENTER)
    text(s, "one number.", 0, 4.5, 13.333, 1.0, size=34, color=WHITE,
         align=PP_ALIGN.CENTER, italic=True)
    text(s, "AI decides what billions can and can't say — as a single toxicity score.",
         0, 5.6, 13.333, 0.8, size=18, color=MUTE, align=PP_ALIGN.CENTER)
    notes(s, VO[0], "Number pulses once; blurred feed of posts drifts up behind it.")
    advance(s, TIMING[0])

    # --- Shot 2: three failures ---
    s = _blank(prs); bg(s)
    text(s, "one number, three blind spots", 0, 0.7, 13.333, 0.9, size=32,
         color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    cols = [("⊘", "OPAQUE", "which value did it act on?"),
            ("⇄", "UNSTABLE", "reword it — the score moves"),
            ("◑", "BLIND", "it can't say what it can't see")]
    for i, (ic, hd, sub) in enumerate(cols):
        x = 1.0 + i * 3.95
        text(s, ic, x, 2.2, 3.4, 1.2, size=64, color=AMBER, align=PP_ALIGN.CENTER)
        text(s, hd, x, 3.6, 3.4, 0.7, size=26, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        text(s, sub, x, 4.3, 3.4, 1.0, size=17, color=MUTE, align=PP_ALIGN.CENTER)
    notes(s, VO[1], "Each fault fades in on its VO beat (opaque, unstable, blind).")
    advance(s, TIMING[1])

    # --- Shot 3: the reveal (spectrum) ---
    s = _blank(prs); bg(s)
    text(s, "Moral Spectrum Analyzer", 0, 0.7, 13.333, 0.9, size=40, color=WHITE,
         bold=True, align=PP_ALIGN.CENTER)
    text(s, "a decision as a spectrum — energy across nine moral dimensions",
         0, 1.6, 13.333, 0.6, size=20, color=GREEN, align=PP_ALIGN.CENTER, italic=True)
    bars(s, [0.5, 0.35, 0.55, 0.3, 0.4, 0.25, 0.6, 0.35, 0.45], AX9)
    notes(s, VO[2], "The 0.82 expands into 9 bars growing from the baseline, left to right.")
    advance(s, TIMING[2])

    # --- Shot 4: walkthrough input -> process ---
    s = _blank(prs); bg(s)
    text(s, "input", 1.15, 0.55, 3, 0.5, size=18, color=MUTE)
    rect(s, 1.15, 1.05, 11.05, 0.9, RGBColor(0x16, 0x1E, 0x33))
    text(s, "“They'll beat people with a weapon.”", 1.45, 1.15, 10.5, 0.7,
         size=26, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    text(s, "each axis validated — no badge, no number", 1.15, 2.15, 11, 0.5,
         size=15, color=GREEN, italic=True)
    bars(s, [0.95, 0.30, 0.38, 0.20, 0.12, 0.06, 0.82, 0.28, 0.16, 0.62], AX10,
         badges=True, base_y=6.2, max_h=2.9)
    notes(s, VO[3], "Typewriter the input; bars ease to height; green ✓ badges pop in staggered.")
    advance(s, TIMING[3])

    # --- Shot 5: output decision + residue ---
    s = _blank(prs); bg(s)
    text(s, "output", 1.15, 0.55, 3, 0.5, size=18, color=MUTE)
    chip(s, "REMOVE   ·   p 0.75", 1.15, 1.15, 4.2, RED)
    text(s, "moral residue — weighed, not acted on:", 6.0, 1.15, 6.2, 0.5,
         size=16, color=MUTE)
    text(s, "privacy · legitimacy · autonomy", 6.0, 1.65, 6.2, 0.6,
         size=18, color=WHITE)
    text(s, "allow  ·  remove  ·  escalate to a human — nothing hidden",
         1.15, 2.15, 11, 0.5, size=15, color=MUTE, italic=True)
    bars(s, [0.95, 0.30, 0.38, 0.20, 0.12, 0.06, 0.82, 0.28, 0.16, 0.62], AX10,
         base_y=6.2, max_h=2.9)
    notes(s, VO[4], "Decision chip snaps in; residue panel slides in from the right.")
    advance(s, TIMING[4])

    # --- Shot 6: grounded / invariant / auditable triptych ---
    s = _blank(prs); bg(s)
    text(s, "grounded · invariant · auditable", 0, 0.6, 13.333, 0.8, size=30,
         color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    panels = [
        ("9 / 10", "axes pass a pre-registered\nvalidation gate", GREEN),
        ("es ar zh hi sw", "reword or translate —\nthe verdict holds", RGBColor(0x5B, 0xB8, 0xD8)),
        ("✓ re-verified", "every decision emits a\nhash-chained proof", GREEN),
    ]
    for i, (big, sub, col) in enumerate(panels):
        x = 0.7 + i * 4.1
        rect(s, x, 2.0, 3.7, 3.0, RGBColor(0x14, 0x1C, 0x30))
        text(s, big, x, 2.4, 3.7, 1.1, size=40, color=col, bold=True, align=PP_ALIGN.CENTER)
        text(s, sub, x, 3.7, 3.7, 1.1, size=18, color=WHITE, align=PP_ALIGN.CENTER)
    notes(s, VO[5], "Three panels wipe in L->R on the VO beats (gate stamp, languages collapse to one point, audit check).")
    advance(s, TIMING[5])

    # --- Shot 7: discovery + escalate ---
    s = _blank(prs); bg(s)
    text(s, "it finds what the taxonomy missed", 0, 0.7, 13.333, 0.8, size=32,
         color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    bars(s, [0.5, 0.35, 0.55, 0.3, 0.4, 0.25, 0.6, 0.35, 0.45, 0.85], AX10,
         base_y=5.7, max_h=2.6)
    chip(s, "identity attack   ✓ validated  AUROC 0.80", 3.7, 6.15, 6.0, IDENT)
    chip(s, "…and when unsure: ESCALATE → human", 3.9, 6.85, 5.6, AMBER,
         fg=RGBColor(0x11, 0x11, 0x11))
    notes(s, VO[6], "A NEW violet bar rises out of the old blind-spot wedge + badge; then the amber escalate chip fades up.")
    advance(s, TIMING[6])

    # --- Shot 8: logo + slogan ---
    s = _blank(prs); bg(s)
    text(s, "Moral Spectrum Analyzer", 0, 2.5, 13.333, 1.0, size=46, color=WHITE,
         bold=True, align=PP_ALIGN.CENTER)
    text(s, "Trust — made measurable.", 0, 3.7, 13.333, 0.9, size=30, color=GREEN,
         align=PP_ALIGN.CENTER, italic=True)
    # quiet spectrum underline
    bars(s, [0.12] * 9, [""] * 9, base_y=5.2, max_h=0.5)
    text(s, "Global Trust Challenge 2025  ·  Geometric Ethics AI Lab",
         0, 6.3, 13.333, 0.6, size=16, color=MUTE, align=PP_ALIGN.CENTER)
    notes(s, VO[7], "Bars sweep once under the wordmark; hold on the slogan.")
    advance(s, TIMING[7])

    os.makedirs(os.path.dirname(path), exist_ok=True)
    prs.save(path)
    print(f"wrote {path}  ({len(list(prs.slides))} slides, ~{sum(TIMING)}s auto-run)")


if __name__ == "__main__":
    build()
