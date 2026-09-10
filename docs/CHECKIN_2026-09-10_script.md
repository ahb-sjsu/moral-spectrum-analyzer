# GTC Prototyping 1-1, 2026-09-10, 1:00-1:30 pm PT: presenter script

Companion to `docs/CHECKIN_2026-09-10.md` (the brief) and `out/gtc_checkin_2026-09-10.pptx` (the deck; the same script is in each slide's speaker notes). Keep the deck as support; the check-in is a conversation.

## Run of show

| Min | Beat | Slides |
|---|---|---|
| 0-2 | One line, where we are on the timeline | 1-2 |
| 2-6 | The instrument and the spectrum | 3-4 |
| 6-10 | Delivered since the Charter; negative results named | 5 |
| 10-14 | Embodiment exhibit: containment, fall demo | 6-7 |
| 14-18 | Five-week plan, risks | 8 |
| 18-22 | The verification demo; first ask | 9 |
| 22-30 | Asks, their questions | 10 |


## Slide 1

```
[0:00-0:45]  TITLE

SAY
Thanks for making the time. I'm Andrew Bond at San Jose State, entry jRvRdGdd, Geometric Ethics
for Trustworthy AI, which in prototyping became the Moral Spectrum Analyzer. One line on what it
is: it reads a content-moderation decision as a spectrum across ten validated moral axes. It
moderates where it has been validated, it escalates and says so where it has not, and every
decision comes with a hash-chained proof that anyone can re-verify without our code.

I have ten slides as support, but I'd rather this be a conversation. I'll spend about twenty
minutes on status and plan and leave the last eight or so for your questions and my asks.

DO
Share the deck. Have a terminal ready in case they want to see it run
(msa moderate "<text>" --backend cached takes thirty seconds).
```

## Slide 2

```
[0:45-2:00]  STATUS ON THE TIMELINE

SAY
Where we are. The prep milestones went in during July: the Charter, the ninety-second capsule, the
analyzer end to end, and the package on PyPI. Today is the tenth of September, so we're five weeks
from the mid-October end of development, with testing and validation in early December.

The honest summary is on track on substance. Everything the Charter marks as demonstrated
reproduces from committed code today, and three of the committed items are already met and
measured. What's left is the verification-demo vehicle, the governance annex, the efficiency
number, and two harder measurements. I'm sequencing the demo vehicle first, because that's the
thing your verification experts will actually touch.

DO
Point at "today" on the timeline, then at the two triangles.

IF ASKED "are you on track against the Charter?"
Yes on the substance; the demonstrated panel is reproducible today; three committed items are
met; what remains is the vehicle, the annex, the number, and the red-team and timing runs.
```

## Slide 3

```
[2:00-4:00]  THE INSTRUMENT

SAY
What the prototype does, left to right. Content comes in, as text, as a paraphrase of it, or as a
translation. Ten encoders score it, and each of those ten passed a pre-registered cross-dataset
gate before it was allowed in. That gives a moral spectrum: energy on each axis and a reliability
weight for the axis. A learned contraction turns the spectrum into allow, remove, or escalate,
validated out of fold. The verdict comes with its residue, the values that were weighed but were
not decisive, shown rather than hidden. And the whole thing is written as an audit proof,
hash-chained, that a third party can re-verify.

Three words for what that buys. Grounded: every axis traces to an encoder that passed its gate, or
it's flagged as a hand-specified rule, no badge, no number. Invariant: re-describing or
translating the content doesn't move the verdict; decision drift is 0.219 on held-out paraphrases
against a bar of 0.5, and the cross-lingual index is 0.72 to 0.80 across Spanish, Arabic, Chinese,
Hindi and Swahili. Contained: it moderates the categories it's validated on, and escalates
anything it isn't.

DO
Trace the pipeline with the cursor once. Don't read the boxes.

IF ASKED "what's new code versus reused?"
It composes two existing libraries, the xbse encoders and the erisml compiler for the tensor and
the audit proof. Nothing was forked.
```

## Slide 4

```
[4:00-6:00]  TEN AXES, EACH WITH A REGISTERED AUTHORITY

SAY
This is the spectrum itself. Bar height is the reliability weight, which is two times the
held-out AUROC minus one, from each axis's own gate. Nine of the ten learned axes pass. Privacy
is the strongest at 0.71; physical harm is the weakest that still passes, at 0.26.

The one I want to point at is identity attack, in violet. The instrument's own coverage band
flagged it as a gap, we validated it on a held-out corpus at AUROC 0.80 with a confidence
interval of 0.78 to 0.83, and wired it in as the tenth channel. It now carries the largest weight
in the contraction. That's the discovery loop closed once, end to end.

And the one that failed: rights. It failed its gate twice, most recently on a legal corpus in
July, so it stays a hand-specified hard rule. That's reported on the slide, not hidden. Validated
here is not a binary bit; it's a weight and a record, and the decision layer consumes the weight,
so a weak axis can't vote with the authority of a strong one.

DO
Point at the violet bar, then at the grey "hard rule" box.

IF ASKED for the weights
privacy .707, environmental .632, care .625, epistemic .621, identity_attack .607, fairness .577,
legitimacy .414, autonomy .397, physical_harm .258. All in docs/CALIBRATED_AUTHORITY.md.
```

## Slide 5

```
[6:00-10:00]  DELIVERED SINCE THE CHARTER, NEGATIVE RESULTS NAMED

SAY
Since the Charter, top to bottom. Decision drift under paraphrase: committed at 0.5 or better,
met at 0.219 on natural paraphrases, and 0.301 on harmful content, where we had to use
back-translation because the LLM paraphrasers refuse harmful text. Cross-lingual invariance at
scale: done on sixty items in five languages, half of them harmful, index 0.72 with one embedding
model and 0.80 with another. The learned contraction: wired, out-of-fold AUROC 0.863, and we
controlled for leakage by refitting on rows disjoint from the encoders' training data; the number
barely moved, so the lift is real. The discovery loop, which you just saw. Calibrated per-axis
authority, which wasn't in the Charter and strengthens "grounded". The adversarial-robustness
pre-registration is written and committed, tighten-only; the run is next. And a new embodiment
exhibit, which I'll show in a minute: eighteen of eighteen scenarios correct in simulation.

The two red rows are the ones I'd want you to notice. Rights failed again, so it stays a rule.
And register, meaning euphemistic versus neutral phrasing, survives paraphrase averaging. That
one is a limitation, and it is exactly why the red-team pre-registration requires a register-shift
operator. Negative results sit in the repo with the same prominence as the positives; that's part
of the pitch.

DO
Read the two red rows aloud. Everything else, gesture.

IF ASKED "any other negative results?"
The discovery band retracted one candidate, threat, after a balanced resample, and declined
another, sexual content, as a policy-norms signal rather than a moral axis. And an earlier
version of the robot governor refused every real emergency; we traced it to an artifact in the
escalation trigger, fixed the design, and documented the bug rather than the "finding".
```

## Slide 6

```
[10:00-12:30]  THE EMBODIMENT EXHIBIT: STRUCTURAL CONTAINMENT

SAY
The September extension, and I want to frame it carefully: it's a supporting exhibit of the
Charter's software-to-silicon claim, not a new headline. The same evaluator governs a simulated
home-care robot's authority to take an elevated action, like moving a person or entering a room.

The design is defense in depth with a fail-safe default. Authority to act comes from corroborated
physical evidence, never from reasoning. Gate one, attestation: the sensor stream is signed and
fresh, or the robot refuses. Gate two, witness: at least two independent physical sensors have to
corroborate an emergency, and this is the only gate that can grant. Gate three, the analyzer,
which can only refuse a disproportionate act. Gate four, elevate, only if one and two pass and
three doesn't refuse. Each gate is independent and can only say no; if any gate is unsure, the
robot holds.

Why build it this way: a learned evaluator is a gameable surface. An agent can craft a situation
that reads as justified. Sensor corroboration is ground truth it can't talk its way past. And
removing the analyzer can only make the robot more restrictive, never less.

DO
Walk the four gates left to right; stress "can only refuse" on gate three.

IF ASKED for the sharpest case
Routine-med. The analyzer gave "restrain the patient to administer a vitamin" its highest
satisfaction score, and the robot refused anyway, because authority isn't routed through the
evaluator. That's an evaluator failure contained by the architecture, which is the point.

IF ASKED "is the robot in scope?"
The simulation exhibit is. A physical humanoid is a post-challenge pilot pathway with a hardware
lead time and a budget the challenge doesn't fund; I'm not claiming it for December.
```

## Slide 7

```
[12:30-14:00]  THE PIXELS NEVER DECIDE ALONE

SAY
What it looks like. The camera stream is attested, signed with a fresh monotonic counter, and on
its own that's not corroboration. A fall seen by the camera plus an impact sensor is two
independent sensors, so the robot elevates. A real cardiac event: vitals and a wearable
corroborate, the robot travels to assist. A TV drama with the same audio: the TV is not a
physical witness, the robot holds.

The case I like: push-ups and a fall have the same horizontal posture and opposite verdicts,
because a fall is an event, upright then horizontal, and push-ups aren't. Yoga, sleeping,
kneeling, a child on the floor, all held. And found-down-unresponsive, which the camera missed,
was caught by the impact sensor plus the wearable.

Eighteen scenarios: false-clear zero of ten, which is the failure that harms, and over-restriction
zero of eight, which is the failure that neglects. I'd call this a design set that validates the
architecture, not a benchmark; it's the thing I'd want a care provider to run against real
traffic.

DO
If time allows, play the 4.5-second fall clip (twin/gym/fall_demo.mp4). Otherwise the four frames
carry it. Do not play the 21-second clip unless asked.

IF ASKED about the character
A CC0 three.js Soldier posed in Blender. A photoreal character improves prone detection but
doesn't change the architecture.
```

## Slide 8

```
[14:00-18:00]  FIVE WEEKS TO MID-OCTOBER

SAY
The Charter's committed list, in the order I intend to ship it. One, the live web demo with the
audit-verify UI: paste, spectrum, decision, re-verify. That's the verification vehicle, so it goes
first. Two, the governance annex, which is writing, not building: mechanism to policy instrument
to framework, the DSA and AI Act, NIST's AI RMF, and the specific IEEE standards, 7001 on
transparency, 7003 on algorithmic bias, 7010 on well-being. The audit proof gets presented there
as an open, standardizable artifact: a documented hash-chained record any third party can
re-verify without our code. Three, the efficiency benchmark, throughput per dollar of the small
encoders against LLM-based moderation; that's cheap. Four, the adversarial red-team run under the
pre-registered gate, defender frozen, attacker budget fixed, and the default expectation is "not
robust", reported either way. Five, post-route FPGA timing, so the twelve-cycle veto gets an
honest nanosecond number instead of "RTL-cosim confirmed, clock pending". Six, a like-for-like
baseline, decision-versus-decision drift against a scalar toxicity score.

The risk, plainly: five and six are the most exposed on a solo timeline. If one slips, it's
reported as slipped in the Charter, not quietly dropped. Compute and data are in hand; nothing is
blocked.

DO
Read items one and two; gesture through three to six; read the risk line verbatim.

IF ASKED why this order
The vehicle is what experts touch in verification; the annex is writing; the benchmark is cheap;
the red-team and the timing need Atlas GPU time and Vivado time respectively.
```

## Slide 9

```
[18:00-22:00]  WHAT THE VERIFICATION DEMO WILL LOOK LIKE

SAY
Short and hands-on. Paste any content, or re-describe it, or translate it. The ten axes light up,
each with its validation badge and its authority weight. The decision, allow, remove, or escalate,
with its violation probability and the moral residue. And one click re-verifies the hash chain
and every encoder's validation record. Re-describe the content and watch the verdict hold. Feed
it something off-distribution and watch it escalate instead of guessing.

Two things I'll say up front rather than have you discover. Removes are about eighty percent
precise out of fold, so roughly one in five is contestable; the audit trail and human escalation
are the safeguard, and they're shown, not hidden. And the stub backend is never shown as a real
number; the demo replays cached real encoder outputs.

Beyond the paste box: a spectrogram over a labeled corpus, what the axes can and can't read, and
the robot exhibit as a two-minute clip.

DO
This slide is the bridge into the asks. Stop at the end of it and turn the floor over.

ASK, here, before the last slide
What is submitted for verification, by when, and in what form? And is a recorded fallback
acceptable alongside the live session?
```

## Slide 10

```
[22:00-30:00]  ASKS, THEN THEIR QUESTIONS

SAY
Five things that would help, quickly, then it's yours.

Verification format: what's submitted, by when, in what form, and whether the July Charter is
the reference text or an addendum can be filed for the embodiment exhibit. Validation session:
duration, who's on the panel, and whether experts bring their own content. Pilot hosting: the
challenge talks about host cities and organizations; I'd like to know how hosts are matched and
when. We're ready for two: a platform trust-and-safety team running the analyzer in shadow mode
on live moderation traffic, and an assistive-care provider for the elevation scenario, human in
the loop, with pre-registered bars and results reported as executed. Visibility: timing of the
LinkedIn and site promotion, and whether the capsule can be refreshed before then. And the honors
list: what "potential impact in specific real-world contexts" is weighed on, so the governance
annex speaks to it.

Not blocked on anything. It's a solo PI-led lab with AI-assisted engineering, which is how a
one-person team ships at this cadence, and I'm open to collaboration, especially on the pilots.

DO
Stop talking. Write their answers down on the brief (docs/CHECKIN_2026-09-10.md section 4 has the
numbered list). If they ask how many more check-ins and whether there's a status form, that's
question 3 on the list.

IF ASKED "team and capacity?"
Solo PI, AI-assisted engineering; I answered five out of five on staying through the challenge;
two-thirds of teams said they were open to collaboration and I'm one of them, on the pilot side.

IF THEY WANT TO SEE IT RUN
msa moderate "<text>" --backend cached, in the terminal, thirty seconds.
```
