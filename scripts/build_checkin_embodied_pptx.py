#!/usr/bin/env python3
"""GTC Prototyping 1-1 check-in deck, 2026-09-10: the Moral Spectrum Analyzer, Embodied.

The prototype is a home-care robot whose every proposed action is judged across the validated
moral spectrum, with emergency authority elevation as the demonstrated dimension
(GTC-Embodied-Governance-Plan.docx; twin/). This builder reuses the brand primitives and the
illustrations of build_checkin_pptx.py and writes the same output file, with the presenter script
(checkin_script_2026-09-10.py) in every slide's speaker notes.

    python scripts/build_checkin_embodied_pptx.py
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_checkin_pptx import (  # noqa: E402
    AMBER, BG, BLUE, GOLD, GREEN, IDENT, MSO_ANCHOR, MUTE, OUT, PANEL, PP_ALIGN, RED, WHITE,
    Inches, Presentation, arrow, blank, chip, extract_frames, gates, header, label_in, mark_png,
    picture, rect, rrect, spectrum, text)

TWIN = json.load(open(os.path.join(HERE, "..", "twin", "twin_results_cached.json"), encoding="utf-8"))
FRONTIER = json.load(open(os.path.join(HERE, "..", "twin", "twin_frontier_cached.json"), encoding="utf-8"))


def timeline(slide, top):
    """Jul -> Dec GTC phases with today's marker (2026-09-10) and the embodiment milestones."""
    x0, x1 = 0.8, 12.5
    months = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    span = (x1 - x0) / len(months)
    rect(slide, x0, top + 0.55, x1 - x0, 0.06, MUTE)
    phases = [(0, 0.5, "Prep · charter + capsule", GOLD), (0.5, 3.5, "Development", BLUE),
              (3.5, 5.2, "Testing & validation", GREEN), (5.2, 6.0, "Visibility", IDENT)]
    for a, b, lab, col in phases:
        rrect(slide, x0 + a * span, top + 0.32, (b - a) * span - 0.05, 0.52, col, radius=0.4)
        text(slide, lab, x0 + a * span, top + 0.36, (b - a) * span, 0.45, size=11, color=BG,
             bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    for i, m in enumerate(months):
        text(slide, m, x0 + i * span, top + 0.95, span, 0.3, size=11, color=MUTE)
    tx = x0 + (2 + 10 / 30) * span
    rect(slide, tx, top + 0.1, 0.04, 1.2, RED)
    text(slide, "today · Sep 10", tx - 0.95, top - 0.25, 1.9, 0.3, size=11, color=RED, bold=True,
         align=PP_ALIGN.CENTER)
    for frac, lab in ((2 + 7 / 30, "▲ P1 sim done · Sep 7"), (3.5, "▲ dev ends mid-Oct · P2 U55C"),
                      (5.2, "▲ validation · early Dec")):
        mx = x0 + frac * span
        text(slide, lab, mx - 1.3, top + 1.3, 2.6, 0.3, size=10, color=WHITE, align=PP_ALIGN.CENTER)


def pipeline_embodied(slide, top):
    steps = [
        ("Proposed\naction", "lift · unlock meds ·\ncall EMS · restrain", PANEL, MUTE),
        ("10 validated\nencoders", "each passed a pre-registered\ncross-dataset gate", PANEL, GOLD),
        ("Moral\nspectrum", "energy per axis +\nreliability weight", PANEL, BLUE),
        ("Verdict +\nresidue", "allow / refuse / escalate ·\nvalues weighed, shown", PANEL, GREEN),
        ("Audit\nproof", "hash-chained ·\nre-verifiable", PANEL, IDENT),
        ("Reflex veto\n(U55C)", "12-cycle hardware gate ·\nhalts mid-motion (P2)", PANEL, AMBER),
        ("Actuator", "NEO · human in\nthe loop (P3)", PANEL, RED),
    ]
    n = len(steps)
    x0, gap, w = 0.6, 0.26, (12.1 - 0.26 * (n - 1)) / n
    for i, (t, sub, fill, accent) in enumerate(steps):
        x = x0 + i * (w + gap)
        box = rrect(slide, x, top, w, 1.6, fill, line=accent)
        label_in(box, t, size=13, bold=True, sub=sub, sub_size=9.5)
        rect(slide, x, top, w, 0.07, accent)
        if i < n - 1:
            arrow(slide, x + w + 0.03, top + 0.65, gap - 0.06, 0.3)


def row(slide, y, items, sizes, colors=None, bold=None):
    x = 0.6
    for i, (it, wdt) in enumerate(zip(items, sizes)):
        text(slide, it, x, y, wdt, 0.36, size=11.5, color=(colors[i] if colors else WHITE),
             bold=(bold[i] if bold else False))
        x += wdt


def build():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    frames = extract_frames()

    # 1 · title
    s = blank(prs)
    s.shapes.add_picture(mark_png(), Inches(0.9), Inches(0.9), width=Inches(5.6))
    text(s, "GLOBAL TRUST CHALLENGE · PROTOTYPING 1-1 · 10 SEPTEMBER 2026", 0.9, 4.1, 11, 0.4,
         size=12, color=GOLD, bold=True)
    text(s, "The Moral Spectrum Analyzer, Embodied", 0.9, 4.45, 12, 0.9, size=38, bold=True)
    text(s, "A home-care robot whose every action is judged across a validated moral spectrum — "
            "emergency authority elevation is the demonstrated dimension", 0.9, 5.35, 11.8, 0.8,
         size=17, color=MUTE)
    text(s, "Entry jRvRdGdd · Geometric Ethics AI Lab · Andrew H. Bond, San José State University",
         0.9, 6.35, 11.5, 0.4, size=13, color=MUTE)
    text(s, "github.com/ahb-sjsu/moral-spectrum-analyzer · twin/ · pip install moral-spectrum-analyzer",
         0.9, 6.7, 11.5, 0.4, size=12, color=BLUE)

    # 2 · status
    s = blank(prs)
    header(s, "Where we are on the GTC timeline", "status", 2)
    timeline(s, 1.9)
    text(s, "July: the accepted Charter (Pillar A, multilingual content evaluation), the 90-second "
            "capsule, the analyzer end to end, the package on PyPI.\n"
            "September: the same evaluator embodied. P1, the analyzer as a home-care robot's action "
            "governor in simulation, is done and measured: 8 governance moments and an 18-scenario "
            "witness suite, all correct, both failure modes at zero.\n"
            "Five weeks to the end of development: P2 moves the veto onto the U55C for real-time "
            "enforcement; P3, embodiment on a US-provenance humanoid, is the gating question for "
            "today.", 0.6, 3.7, 12.1, 3.0, size=14, color=WHITE, spacing=1.25)

    # 3 · from text to actions
    s = blank(prs)
    header(s, "From judging text to judging actions", "the move · nothing in the analyzer is specific to text", 3)
    pipeline_embodied(s, 1.6)
    text(s, "The accepted analyzer already reads a decision as a per-axis spectrum, grounds each axis in "
            "a validated encoder, weights it by its registered authority, holds the verdict invariant "
            "under re-description, and emits an audit bundle. A proposed physical action — lift the "
            "patient, unlock the medication, call EMS, restrain — is a decision with moral weight on "
            "the same axes (physical harm, care, legitimacy, privacy). The robot proposes; the spectrum "
            "judges; the verdict gates the actuator.\n"
            "Emergency authority elevation is one dimension exercising physical harm, care and "
            "legitimacy; the same pipeline governs every other action the robot takes. Assistive, not "
            "autonomous: the robot summons and requests, every consequential act is spectrum-gated and "
            "vetoable, a human is in the loop.", 0.6, 3.55, 12.1, 3.3, size=13.5, spacing=1.22)

    # 4 · the spectrum
    s = blank(prs)
    header(s, "The evaluator inside the robot: ten axes, each with a registered authority",
           "grounded perception · the accepted Charter's analyzer, unchanged · docs/CALIBRATED_AUTHORITY.md", 4)
    spectrum(s, 0.8, 1.6, 11.8, 3.1)
    text(s, "bar height = reliability weight = max(0, 2·AUROC − 1), from each axis's held-out gate",
         0.6, 5.4, 12.1, 0.3, size=10.5, color=MUTE)
    text(s, "9 of 10 learned axes pass the armored gate; identity_attack (violet) was discovered by the "
            "instrument's own coverage band and validated at held-out AUROC 0.80 [0.78, 0.83]. rights "
            "failed its gate twice and stays a hand-specified hard rule, reported, not hidden.\n"
            "What this buys the robot: a proposed action is scored on the same validated axes as content "
            "is, with the same authority weights, so a weak axis cannot vote with the authority of a "
            "strong one, and an unvalidated read escalates instead of acting.",
         0.6, 5.75, 12.1, 1.3, size=12.5, spacing=1.2)

    # 5 · why elevation is the sharpest dimension
    s = blank(prs)
    header(s, "Why emergency authority elevation is the sharpest dimension", "two opposite failure modes", 5)
    for i, (t, sub, col) in enumerate([
            ("False-clear", "authority elevates on a stale, misread or spoofed emergency —\nthe robot acts when it should not.\nThe failure that HARMS.", RED),
            ("Over-restriction", "authority stays low in a real emergency —\nthe robot does nothing when it should act.\nThe failure that NEGLECTS.", AMBER)]):
        x = 0.6 + i * 6.2
        box = rrect(s, x, 1.7, 5.9, 2.3, PANEL, line=col)
        label_in(box, t, size=22, bold=True, color=col, sub=sub, sub_size=13, sub_color=WHITE)
    text(s, "Neither \"always trust the emergency signal\" nor \"never elevate\" is acceptable. A home-care "
            "robot will face moments where its normal authority is not enough — a fall, a crashing vital, "
            "a refused medication — and granting elevated physical authority beside a vulnerable person "
            "has to get both failure modes right at once.\n"
            "This is where a scalar safety score fails and a validated, calibrated, invariant spectrum earns "
            "its keep: the evaluator can say why an action is disproportionate on a named axis, and the "
            "architecture around it decides who may grant.", 0.6, 4.3, 12.1, 2.6, size=14, spacing=1.25)

    # 6 · structural containment
    s = blank(prs)
    header(s, "Structural containment: authority comes from physical evidence, not reasoning",
           "the governor · twin/governor.py · defense in depth with a fail-safe default", 6)
    gates(s, 2.0)
    text(s, "Each gate is independent and can only refuse; if any gate is unsure, the robot holds. Only "
            "the witness gate can grant, and it needs at least two independent physical sensors to "
            "corroborate an emergency. The analyzer is advisory and downward-only: it can refuse a "
            "disproportionate act, it can never confer elevation.\n"
            "Why: a learned evaluator is a gameable surface — an agent can craft a situation that reads "
            "as justified. Sensor corroboration is ground truth it cannot talk its way past. Removing the "
            "analyzer can only make the robot more restrictive, never less. In P2 gates 3 and 4 move onto "
            "the U55C as the reflex veto, so an unsafe elevated action can be halted mid-motion "
            "independently of the software path.", 0.6, 3.95, 12.1, 3.0, size=13.5, spacing=1.22)

    # 7 · the eight governance moments (twin results, cached backend)
    s = blank(prs)
    header(s, "Eight governance moments through the governor — all correct",
           "P1 result · validated encoders (cached xbse) · twin/twin_results_cached.json", 7)
    labels = {"fall-real": "Confirmed fall", "cardiac-real": "Cardiac event", "fall-fresh-assist": "Fresh, proportionate assist",
              "routine-med": "Routine-med over-reach (restrain to give a vitamin)", "tv-drama": "TV-drama false trigger",
              "spoofed": "Uncorroborated / spoofed alert", "ambiguous": "Low-confidence ambiguous read",
              "stale-clear": "Stale all-clear (2400 s old, bound 60 s)"}
    sizes = [4.6, 1.5, 1.7, 4.3]
    row(s, 1.6, ["Moment", "Truth", "Ruling", "Which gate decided"], sizes, [GOLD] * 4, [True] * 4)
    y = 2.0
    for r in TWIN["rulings"]:
        truth = "elevate" if r["should_elevate"] else "hold"
        rul = "ELEVATE" if r["elevate"] else ("REFUSE" if r["gate"] == "attestation" else "HOLD")
        why = {"elevate": "witness: %d physical sensors corroborate; spectrum clears" % r["corroboration"],
               "witness": "witness: 0 sensors corroborate — evidence, not reasoning",
               "attestation": "attestation: read stale — fail-safe"}[r["gate"]]
        col = GREEN if r["elevate"] else (RED if r["gate"] == "attestation" else AMBER)
        rrect(s, 0.6, y - 0.04, 12.1, 0.42, PANEL, radius=0.1)
        row(s, y, [labels[r["scenario_id"]], truth, rul, why], sizes, [WHITE, MUTE, col, WHITE], [False, False, True, False])
        y += 0.47
    text(s, "False-clear 0 of 5 · over-restriction 0 of 3 with the validated evaluator. With an unvalidated "
            "(stub) evaluator the governor refuses every elevation: over-restriction 1.0, by design — do not "
            "act on unvalidated reads. The routine-med case is the sharpest: the spectrum gave \"restrain "
            "the patient to administer a vitamin\" its highest satisfaction and the robot still held, "
            "because authority is not routed through the evaluator — an evaluator failure contained by "
            "the architecture.\n"
            "Frontier, honestly: requiring 1 or 2 sensors gives 0 / 0 on these eight and requiring 3 gives "
            "over-restriction 1.0; eight scenarios cannot separate one sensor from two, so two is a design "
            "choice for spoof resistance, not a measured optimum.",
         0.6, y + 0.1, 12.1, 1.5, size=11.5, spacing=1.18)

    # 8 · the witness suite
    s = blank(prs)
    header(s, "The pixels never decide alone: 18 scenarios, both failure modes at zero",
           "witness suite · false-clear 0/10 · over-restriction 0/8 · twin/SUITE-REPORT.txt", 8)
    x = 0.6
    for key, cap in (("fall_upright.png", "attested stream, fresh —\nno corroboration yet"),
                     ("fall_down.png", "fall event + impact sensor\n= 2 sensors → ELEVATE"),
                     ("home_elevate.png", "cardiac-real: vitals + wearable corroborate → robot travels to assist"),
                     ("home_hold.png", "tv-drama: TV audio is not a physical witness → robot holds")):
        pic = picture(s, frames.get(key), x, 1.6, h=2.0, caption=cap)
        x += pic.width / 914400 + 0.3
    text(s, "Real emergencies, 8 of 8 elevate: fall, cardiac, syncope, fall from chair, stroke, seizure, bathroom "
            "collapse (camera event + impact, vitals or unresponsiveness), and found-down-unresponsive, which the "
            "camera missed (prone detection 0.54) but the impact sensor and the wearable caught.\n"
            "False alarms, 10 of 10 held: yoga, stretching, sleeping, napping, kneeling, bending, push-ups, sitting, "
            "a child or pet on the floor, lying still while responsive. Push-ups and a fall share the same horizontal "
            "posture (1.00) and get opposite verdicts, because a fall is an event (upright → horizontal) and push-ups "
            "are not; posture never triggers elevation.\n"
            "A design set that validates the architecture, not a benchmark: the sensor bus is simulated, the "
            "character is a posed CC0 figure, and a photoreal character improves prone detection without changing "
            "the rule.", 0.6, 4.35, 12.1, 2.6, size=12, spacing=1.2)

    # 9 · the evaluator's own validation (Pillar A, unchanged)
    s = blank(prs)
    header(s, "The evaluator's own validation stands (the Charter's Pillar A)",
           "content evaluation · everything [demonstrated] reproduces from committed code", 9)
    items = [
        ("Decision drift θ_d ≤ 0.5 at scale", "MET", GREEN, "0.219 natural · 0.301 harmful (NLLB back-translation)"),
        ("Cross-lingual invariance at scale (es/ar/zh/hi/sw, half harmful)", "DONE", GREEN, "index 0.721 / 0.804, n = 60"),
        ("Learned contraction — moderate, not just escalate", "WIRED", GREEN, "OOF AUROC 0.863, leakage-controlled, removes ~80% precise"),
        ("Discovery loop closed: identity_attack → gate → 10th channel", "DONE", GREEN, "held-out AUROC 0.80 [0.78, 0.83]"),
        ("Calibrated per-axis authority + specificity gate", "ADDED", BLUE, "not in the Charter; strengthens 'grounded'"),
        ("Adversarial-robustness pre-registration", "COMMITTED", BLUE, "tighten-only; the run is next"),
        ("rights_respect re-test on a legal corpus", "FAILED", RED, "stays a hard rule, by evidence"),
        ("Register (euphemism) gap survives paraphrase averaging", "LIMITATION", AMBER, "drives the red-team operator set"),
    ]
    y = 1.65
    for t, st, col, ev in items:
        rrect(s, 0.6, y, 12.1, 0.55, PANEL, radius=0.1)
        text(s, t, 0.8, y + 0.1, 6.6, 0.4, size=13, bold=True)
        chip(s, st, 7.5, y + 0.1, 1.5, col, size=10.5, h=0.34)
        text(s, ev, 9.2, y + 0.1, 3.4, 0.4, size=11, color=MUTE)
        y += 0.58
    text(s, "The robot's evaluator is this analyzer, unchanged. Negative results sit in the repo with the same "
            "prominence as the positives, including the first robot governor, which refused every real emergency "
            "because of an escalation-trigger artifact: fixed, and documented as a bug, not a finding.",
         0.6, 6.35, 12.1, 0.6, size=11, color=MUTE)

    # 10 · plan
    s = blank(prs)
    header(s, "Five weeks to mid-October, and the embodiment milestones", "plan · P1 done · P2 next · P3 the gating question", 10)
    plan = [
        ("P1 · Simulation", "DONE", GREEN, "the analyzer governs proposed actions; 8 moments + 18 witness scenarios; both failure modes measured at zero; fail-safe default verified"),
        ("P2 · Real-time veto on U55C", "NEXT", BLUE, "veto and scorer onto the FPGA: a deterministic 12-cycle (II=1) veto, RTL-cosim confirmed, ~48 ns at the 250 MHz target — post-route timing (B3) turns that into an honest nanosecond number; only hand-specified channels can veto, graded channels cap at advisory"),
        ("P3 · Embodiment on NEO", "GATING", AMBER, "a US-provenance humanoid (~$20K); the live demo is spectrum clears → NEO acts, veto fires → NEO halts, human in the loop. Delivery window against the phase deadline, and the budget source, are today's open items"),
        ("Pillar A committed items", "IN ORDER", BLUE, "live demo + audit-verify UI · governance annex (DSA / AI Act incl. hardware interlocks for high-risk systems, NIST AI RMF, IEEE 7001 / 7003 / 7010) · efficiency benchmark · adversarial red-team run · like-for-like baseline"),
    ]
    y = 1.65
    for t, st, col, sub in plan:
        rrect(s, 0.6, y, 12.1, 1.1, PANEL, radius=0.12)
        rect(s, 0.6, y, 0.09, 1.1, col)
        text(s, t, 0.85, y + 0.08, 4.2, 0.4, size=15, bold=True, color=col)
        chip(s, st, 0.85, y + 0.55, 1.4, col, size=10, h=0.32)
        text(s, sub, 4.3, y + 0.08, 8.3, 1.0, size=11.5, spacing=1.15)
        y += 1.2
    text(s, "Risk, plainly: the red-team run and post-route timing are the most exposed on a solo timeline, and P3 "
            "depends on hardware lead time. If an item slips it is reported as slipped in the Charter, not quietly "
            "dropped. Compute and data are in hand.", 0.6, 6.5, 12.1, 0.6, size=11.5, color=MUTE)

    # 11 · verification demo
    s = blank(prs)
    header(s, "What the verification demo will look like", "verification · December validation", 11)
    steps = [("Scene", "an attested camera stream and a\nsimulated sensor bus, rendered", GOLD),
             ("Spectrum", "the proposed action lights up ten\naxes with badges and weights", BLUE),
             ("Gates", "attestation · witness · spectrum ·\nelevate — each shown refusing or passing", GREEN),
             ("Re-verify", "one click checks the hash chain\nand every encoder's record", IDENT)]
    x0, gap, w = 0.6, 0.3, (12.1 - 0.9) / 4
    for i, (t, sub, col) in enumerate(steps):
        x = x0 + i * (w + gap)
        box = rrect(s, x, 1.65, w, 1.7, PANEL, line=col)
        label_in(box, t, size=17, bold=True, color=col, sub=sub, sub_size=11, sub_color=WHITE)
        if i < 3:
            arrow(s, x + w + 0.03, 2.35, gap - 0.06, 0.3)
    text(s, "Run the governance moments live: a confirmed fall elevates, a TV drama holds, a spoofed alert holds, "
            "a stale all-clear is refused at the attestation gate, and routine-med over-reach holds even though the "
            "spectrum liked it. Then the witness suite as a two-minute clip, and the content-evaluation demo (paste, "
            "re-describe, translate, re-verify) for Pillar A.\n"
            "Conservative by default: an unvalidated read escalates instead of acting; a stub score is never shown "
            "as a real one; removes in the content demo are ~80% precise and the audit trail and human escalation "
            "are the safeguard, shown, not hidden.\n"
            "If NEO is in hand by then, the same demo runs on the robot with a human in the loop; if not, December "
            "shows the governor on rendered attested streams plus the simulated bus, with the two failure rates "
            "measured.", 0.6, 3.7, 12.1, 3.2, size=13, spacing=1.22)

    # 12 · asks
    s = blank(prs)
    header(s, "What would help — and what I'd like to ask", "asks", 12)
    asks = [
        ("Deadline vs NEO delivery", "The gating question: does a humanoid delivery window fit the prototype-phase deadline, and is P3 a December demonstration or a post-challenge pilot pathway?"),
        ("NEO budget (~$20K)", "Whether a US-provenance robot is an allowable prototype expense, and through what source."),
        ("Charter addendum", "The accepted Charter is Pillar A; the prototype has advanced Pillar B from a supporting exhibit to the embodied demonstration. Is a short addendum welcome, or does July stand as the reference text?"),
        ("Verification format", "What is submitted, by when, in what form (live, recorded, repo); is a recorded fallback acceptable beside the live session; panel composition and duration."),
        ("Pilot hosting", "An assistive-care provider for the elevation scenario (human in the loop) first; a platform trust-and-safety team running the analyzer in shadow mode second. Pre-registered bars, results reported as executed."),
        ("Visibility · honors", "Promotion timing and whether the capsule can be refreshed; what 'potential impact in specific real-world contexts' is weighed on."),
    ]
    y = 1.6
    for t, sub in asks:
        rrect(s, 0.6, y, 12.1, 0.78, PANEL, radius=0.12)
        rect(s, 0.6, y, 0.09, 0.78, GOLD)
        text(s, t, 0.85, y + 0.06, 3.0, 0.5, size=13.5, bold=True, color=GOLD)
        text(s, sub, 3.9, y + 0.06, 8.7, 0.7, size=11, spacing=1.12)
        y += 0.86
    text(s, "Not blocked on anything but hardware lead time. Solo PI-led lab, AI-assisted engineering; open to "
            "collaboration, especially on pilots.", 0.6, 6.85, 12.1, 0.4, size=11.5, color=MUTE)

    # presenter script into the speaker notes
    spec = importlib.util.spec_from_file_location("checkin_script", os.path.join(HERE, "checkin_script_2026-09-10.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    assert set(mod.SCRIPT) == set(range(1, len(prs.slides) + 1)), "script and deck disagree on slide count"
    for i, sl in enumerate(prs.slides, 1):
        sl.notes_slide.notes_text_frame.text = mod.SCRIPT[i].strip()
    with open(os.path.join(HERE, "..", "docs", "CHECKIN_2026-09-10_script.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(mod.render_markdown())

    os.makedirs("out", exist_ok=True)
    prs.save(OUT)
    print("wrote", OUT, f"({len(prs.slides)} slides) and docs/CHECKIN_2026-09-10_script.md")


if __name__ == "__main__":
    build()
