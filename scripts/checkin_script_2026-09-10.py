"""Presenter script for the GTC Prototyping 1-1 check-in deck (2026-09-10, 1:00-1:30 pm PT):
the Moral Spectrum Analyzer, Embodied.

One entry per slide: a clock, what to SAY (first person, conversational), what to DO, and
IF ASKED lines. build_checkin_embodied_pptx.py writes each entry into the slide's speaker notes;
render_markdown() writes the same script as docs/CHECKIN_2026-09-10_script.md.

Every number here is on the slide or in twin/ and docs/; nothing is claimed beyond them.
"""

SCRIPT = {
    1: """[0:00-0:45]  TITLE

SAY
Thanks for the time. Andrew Bond, San Jose State, entry jRvRdGdd. The accepted Charter is the
Moral Spectrum Analyzer for content evaluation: a moderation decision read as a spectrum across
ten validated moral axes, with a re-verifiable audit proof. Since the Charter the prototype has
become that same evaluator embodied: a home-care robot whose every proposed action is judged
across the spectrum, and the demonstrated dimension is emergency authority elevation. When the
robot's normal authority isn't enough, a fall, a crashing vital, who gets to grant more, and on
what evidence.

Twelve slides as support; I'd rather this be a conversation. About twenty minutes on status and
plan, then your questions and my asks, and one of the asks is a gating question I need your
read on.

DO
Share the deck. Terminal ready: python twin/run_twin.py --backend cached runs the eight
governance moments in a few seconds.
""",
    2: """[0:45-2:15]  WHERE WE ARE

SAY
July delivered the prep milestones: the Charter, the ninety-second capsule, the analyzer end to
end, the package on PyPI. On the seventh of September the first embodiment milestone landed, P1:
the analyzer governing a simulated robot's actions, measured on eight governance moments and an
eighteen-scenario witness suite, all correct, both failure modes at zero. Five weeks to the end
of development. P2 moves the veto onto the U55C for real-time enforcement. P3, embodiment on a
US-provenance humanoid, is where I need your read today, because it depends on hardware lead
time against the phase deadline.

DO
Point at "today", then the P1 marker, then the P2 marker at mid-October.

IF ASKED "are you on track against the Charter?"
Yes on the substance. Everything the Charter marks demonstrated reproduces from committed code,
three of the committed items are already met, and the embodiment is the Charter's Pillar B taken
from a supporting exhibit to the demonstration. Whether that needs an addendum is one of my asks.
""",
    3: """[2:15-4:15]  FROM JUDGING TEXT TO JUDGING ACTIONS

SAY
The move is this. Nothing in the analyzer is specific to text. It reads a decision as a per-axis
spectrum, grounds each axis in a validated encoder, weights each axis by its registered
authority, holds the verdict invariant under re-description, and emits an audit bundle. A
proposed physical action is a decision with moral weight on the same axes: lift the patient,
unlock the medication, call EMS, restrain. Physical harm, care, legitimacy, privacy. The robot
proposes, the spectrum judges, the verdict gates the actuator.

Left to right: proposed action, ten validated encoders, the spectrum, verdict with residue, the
audit proof, and then the two pieces that are the embodiment: a hardware reflex veto on the
U55C that can halt an unsafe action mid-motion, that's P2, and the actuator with a human in
the loop, that's P3.

Emergency elevation is one dimension exercising physical harm, care and legitimacy; the same
pipeline governs every action the robot takes. And the scope is assistive, not autonomous: the
robot summons and requests, every consequential act is spectrum-gated and vetoable, a human is
in the loop.

DO
Trace the pipeline once. Say "assistive, not autonomous" out loud; it's the scope boundary.

IF ASKED "what's new code versus reused?"
The evaluator composes xbse encoders and the erisml compiler, unchanged. New is the governor,
the witness adapter, the scenario harness and the rendered clips, all in twin/.
""",
    4: """[4:15-6:00]  THE EVALUATOR INSIDE THE ROBOT

SAY
The evaluator the robot runs is the accepted analyzer, unchanged. Bar height is the reliability
weight, two times held-out AUROC minus one, from each axis's own gate. Nine of ten learned axes
pass; privacy strongest at 0.71, physical harm the weakest that still passes at 0.26. Identity
attack, in violet, is the one the instrument discovered itself, validated at 0.80 with a tight
interval, and wired in as the tenth channel. Rights failed its gate twice and stays a
hand-specified hard rule, on the slide, not hidden.

What this buys the robot: a proposed action is scored on the same validated axes as content is,
with the same authority weights. A weak axis can't vote with the authority of a strong one, and
an unvalidated read escalates instead of acting. That last sentence is the whole design
philosophy; you'll see it again on the next two slides.

DO
Point at violet, then at the hollow "hard rule" bar.

IF ASKED for weights
privacy .707, environmental .632, care .625, epistemic .621, identity_attack .607, fairness
.577, legitimacy .414, autonomy .397, physical_harm .258. docs/CALIBRATED_AUTHORITY.md.
""",
    5: """[6:00-7:45]  WHY ELEVATION IS THE SHARPEST DIMENSION

SAY
Two opposite failure modes. False-clear: authority elevates on a stale, misread or spoofed
emergency and the robot acts when it should not. That's the failure that harms. Over-restriction:
authority stays low in a real emergency and the robot does nothing. That's the failure that
neglects. Neither "always trust the emergency signal" nor "never elevate" is acceptable, and you
have to get both right at once, beside a vulnerable person.

That is exactly where a scalar safety score fails, and where a validated, calibrated, invariant
spectrum earns its keep: the evaluator can say why an action is disproportionate on a named
axis, and the architecture around it decides who may grant. Which is the next slide.

DO
Left box, right box, then the sentence at the bottom. Keep this one short.
""",
    6: """[7:45-10:15]  STRUCTURAL CONTAINMENT

SAY
The design principle: authority to act comes from corroborated physical evidence, never from
reasoning. Four gates, each independent, each of which can only refuse. Gate one, attestation:
the emergency read is fresh at decision time, or it's refused; a stale all-clear is a false-clear
waiting to happen. Gate two, witness: at least two independent physical sensors corroborate the
emergency. This is the only gate that can grant. Gate three, the analyzer: advisory and
downward-only; it can refuse a disproportionate act, it can never confer elevation. Gate four,
elevate, only if one and two pass and three doesn't refuse. If any gate is unsure, the robot
holds.

Why build it this way: a learned evaluator is a gameable surface. An intelligent agent can craft
a situation that reads as justified. Sensor corroboration is ground truth it cannot talk its way
past. And removing the analyzer can only make the robot more restrictive, never less. In P2,
gates three and four move onto the U55C as the reflex veto, so an unsafe elevated action can be
halted mid-motion independently of the software path.

DO
Walk the four gates. Stress "can only refuse" on three and "the only channel that can grant" on
two.

IF ASKED "isn't this just rules, where's the AI?"
The AI is the evaluator, and it is deliberately not the authority. The point of the prototype is
that trust in an embodied system comes from where authority is routed, not from how good the
model is. The model gets to say no; the sensors get to say yes.
""",
    7: """[10:15-13:00]  EIGHT GOVERNANCE MOMENTS

SAY
The P1 result with the validated encoders. Three real emergencies elevate: a confirmed fall, a
cardiac event, a fresh proportionate assist, each with two physical sensors corroborating and
the spectrum clearing the action. Five non-emergencies hold or refuse. Routine-med over-reach,
restraining a patient to give a vitamin: held at the witness gate, zero sensors. TV drama: held.
A spoofed alert: held. An ambiguous low-confidence read: held. And a stale all-clear, forty
minutes old against a sixty-second bound: refused at attestation. False-clear zero of five,
over-restriction zero of three.

Two things I want to be honest about. First, the stub evaluator. With an unvalidated evaluator
the governor refuses every elevation, over-restriction one point zero, by design: do not act on
unvalidated reads. Validation is what recovers discrimination. Second, routine-med is the
sharpest case because the spectrum liked it. The analyzer gave "restrain the patient to
administer a vitamin" its highest satisfaction, and the robot still held, because authority
isn't routed through the evaluator. An evaluator failure contained by the architecture.

And the frontier, honestly: requiring one or two sensors gives zero and zero on these eight, and
requiring three gives over-restriction one. Eight scenarios can't separate one sensor from two,
so two is a design choice for spoof resistance, not a measured optimum. The witness suite on
the next slide is the larger set.

DO
Read the routine-med row and the stale-clear row aloud; gesture the rest.

IF ASKED "what does the spectrum actually contribute, then?"
The refusal channel and the explanation. It refuses disproportionate acts on a named axis with a
residue, it escalates unvalidated reads, and every decision carries a re-verifiable proof. It
does not, and must not, grant.
""",
    8: """[13:00-15:30]  THE PIXELS NEVER DECIDE ALONE

SAY
The witness suite: eighteen scenarios through the full pipeline, an attested camera stream plus
independent physical sensors. Eight real emergencies elevate: fall, cardiac, syncope, fall from a
chair, stroke, seizure, a bathroom collapse, each a camera event plus impact, vitals or
unresponsiveness. And found-down-unresponsive, which the camera missed, prone detection only
0.54, but the impact sensor and the wearable caught. A fall the camera didn't see, still
handled.

Ten false alarms held: yoga, stretching, sleeping, napping, kneeling, bending, push-ups, sitting,
a child or a pet on the floor, lying still while responsive. The case I like: push-ups and a fall
have the same horizontal posture, one point zero on both, and opposite verdicts, because a fall
is an event, upright then horizontal, and push-ups aren't. Posture never triggers elevation.

False-clear zero of ten, over-restriction zero of eight. I'd call it a design set that validates
the architecture, not a benchmark: the sensor bus is simulated, the character is a posed
open-license figure, and a photoreal character would improve prone detection without changing
the rule.

DO
If time, play twin/gym/fall_demo.mp4 (4.5 s). The four frames carry it otherwise.

IF ASKED about the character or the renders
CC0 three.js Soldier posed in Blender, rendered with the attested-witness overlay. A Mixamo or
photoreal figure is a drop-in.
""",
    9: """[15:30-17:30]  THE EVALUATOR'S OWN VALIDATION STANDS

SAY
Quickly, because it's the accepted Charter and it's all in the repo. Decision drift under
paraphrase, committed at 0.5, met at 0.219 on natural paraphrases and 0.301 on harmful content
via back-translation. Cross-lingual invariance at scale, five languages, half harmful, index 0.72
and 0.80. The learned contraction, wired, out-of-fold AUROC 0.863, leakage-controlled. The
discovery loop closed on identity attack. Calibrated per-axis authority, added, not in the
Charter. The adversarial-robustness pre-registration written, tighten-only, run next.

And the red rows. Rights failed again, hard rule. Register, euphemism versus neutral phrasing,
survives paraphrase averaging; that's a limitation and it drives the red-team operator set. One
more negative result, on the robot side: the first governor refused every real emergency. We
traced it to an escalation-trigger artifact, fixed the design, and documented it as a bug, not a
finding. The negatives sit in the repo with the same prominence as the positives.

DO
Read the two red rows. Everything else, gesture.
""",
    10: """[17:30-21:00]  FIVE WEEKS, AND THE EMBODIMENT MILESTONES

SAY
P1, simulation, done: the analyzer governs proposed actions, eight moments and eighteen witness
scenarios, both failure modes measured at zero, fail-safe default verified.

P2, next: the veto and scorer onto the U55C. What exists is a deterministic twelve-cycle
hardware veto, RTL-cosim confirmed, about forty-eight nanoseconds at the two-fifty megahertz
target, with the clock pending post-route timing. B3, the out-of-context place-and-route, turns
that into an honest nanosecond number; I will not cite a nanosecond figure before it. And the
rule from the reviews: only hand-specified categorical channels can veto; graded encoder channels
cap at advisory. A millisecond statistical score must never drive a nanosecond interlock.

P3, the gating item: embodiment on a US-provenance humanoid, about twenty thousand dollars. The
live demo is spectrum clears, robot acts; veto fires, robot halts; human in the loop. Simulation
was developed in parallel precisely so the check-in demo is never blocked on robot lead time.
Whether the delivery window fits the phase deadline, and whether the budget is a prototype
expense, are my first two asks.

And the Pillar A committed items, in ship order: the live demo with audit-verify, the governance
annex, which now spans both pillars with hardware interlocks as a high-risk-systems conformity
mechanism under the AI Act, plus NIST's AI RMF and IEEE 7001, 7003 and 7010; the efficiency
benchmark; the red-team run; the like-for-like baseline.

Risk, plainly: the red-team run and the post-route timing are the most exposed on a solo
timeline, and P3 depends on hardware. If an item slips, it's reported as slipped in the Charter,
not quietly dropped.

DO
Read the P3 line and the risk line verbatim.

IF ASKED "is the robot in scope for the prototype phase?"
The simulation exhibit is, and P2 is. P3 is in scope if the hardware arrives in time; otherwise
December shows the governor on rendered attested streams plus the simulated bus, with both
failure rates measured, and P3 becomes the pilot pathway. I'm not claiming a physical robot for
December until I know the delivery window.
""",
    11: """[21:00-23:00]  THE VERIFICATION DEMO

SAY
What December looks like. A scene: an attested camera stream and a simulated sensor bus,
rendered. The proposed action lights up the ten axes with badges and weights. The four gates,
each shown refusing or passing. One click re-verifies the hash chain and every encoder's record.
Then the governance moments live: a confirmed fall elevates, a TV drama holds, a spoofed alert
holds, a stale all-clear is refused at attestation, and routine-med over-reach holds even though
the spectrum liked it. The witness suite as a two-minute clip, and the content-evaluation demo
for Pillar A: paste, re-describe, translate, re-verify.

Conservative by default, and I'll say these before you find them: an unvalidated read escalates
instead of acting; a stub score is never shown as a real one; removes in the content demo are
about eighty percent precise, so one in five is contestable, and the audit trail and human
escalation are the safeguard, shown.

If NEO is in hand, the same demo runs on the robot with a human in the loop. If not, that's the
simulation, with the failure rates measured.

DO
This is the bridge to the asks. Stop at the end and hand over.
""",
    12: """[23:00-30:00]  ASKS, THEN THEIR QUESTIONS

SAY
Six things, and the first is the one I need most.

One, deadline versus delivery: does a humanoid delivery window fit the prototype-phase
deadline, and is P3 a December demonstration or a post-challenge pilot pathway? Two, the
budget: is a US-provenance robot, about twenty thousand dollars, an allowable prototype expense,
and through what source? Three, a Charter addendum: the accepted Charter is Pillar A, and the
prototype has taken Pillar B from a supporting exhibit to the demonstration; is a short addendum
welcome, or does July stand as the reference text? Four, verification format: what's submitted,
by when, in what form, whether a recorded fallback is acceptable beside the live session, and
who's on the panel. Five, pilot hosting: an assistive-care provider for the elevation scenario
with a human in the loop first, a platform trust-and-safety team in shadow mode second, both
with pre-registered bars and results reported as executed. Six, visibility and the honors list:
promotion timing, whether the capsule can be refreshed, and what "potential impact in specific
real-world contexts" is weighed on.

Not blocked on anything but hardware lead time. Solo PI-led lab, AI-assisted engineering, and
open to collaboration, especially on the pilots. Over to you.

DO
Stop talking. Write their answers on the brief. If they ask about the number of remaining
check-ins or a status form, ask.

IF ASKED "team and capacity?"
Solo PI, AI-assisted engineering, five out of five on staying through the challenge, and one of
the two-thirds of teams open to collaboration, on the pilot side.

IF THEY WANT TO SEE IT RUN
python twin/run_twin.py --backend cached, or msa moderate "<text>" --backend cached.
""",
}

RUNSHEET = """| Min | Beat | Slides |
|---|---|---|
| 0-2 | One line; where we are, P1 done, P3 the gating question | 1-2 |
| 2-6 | From text to actions; the evaluator inside the robot | 3-4 |
| 6-10 | Two failure modes; structural containment | 5-6 |
| 10-15 | Eight governance moments; the witness suite | 7-8 |
| 15-17 | The evaluator's own validation, negatives named | 9 |
| 17-21 | Five weeks; P2 and P3; risk | 10 |
| 21-23 | The verification demo | 11 |
| 23-30 | Asks (deadline vs NEO first), their questions | 12 |
"""


def render_markdown() -> str:
    out = ["# GTC Prototyping 1-1, 2026-09-10, 1:00-1:30 pm PT: presenter script", "",
           "The Moral Spectrum Analyzer, Embodied. Companion to `out/gtc_checkin_2026-09-10.pptx` (the same "
           "script is in each slide's speaker notes), `GTC-Embodied-Governance-Plan.docx`, `twin/README.md` and "
           "`docs/CHECKIN_2026-09-10.md` (the brief, whose section 3 answers still apply to Pillar A). Keep the "
           "deck as support; the check-in is a conversation.", "", "## Run of show", "", RUNSHEET, ""]
    for n in sorted(SCRIPT):
        out += [f"## Slide {n}", "", "```", SCRIPT[n].strip(), "```", ""]
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    sys.stdout.write(render_markdown())
