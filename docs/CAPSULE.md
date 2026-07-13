# Information Capsule — 90-second script & storyboard

**Deliverable:** GTC prototyping-phase *Information Capsule* (task 21) — a ~90 s video for the public
GTC partner site. **Arc (per onboarding):** problem + stakes → input → process → output walkthrough →
memorable slogan.

**Format:** narrated **animated PPTX** (self-running, 16:9). A silent branded **intro title card**
(~5 s) opens, then the voiceover (human or TTS) plays over eight auto-advancing shots. Generator:
`scripts/build_capsule_pptx.py` → `out/capsule.pptx` (speaker-notes hold the voiceover; slide
timings auto-advance — **~95 s total = 5 s intro + 90 s narrated**).

**Honesty guardrail:** every spoken number is a **[demonstrated]** Charter claim at licensed strength.
Nothing here states a `[committed]` item as done. Cross-check: `CHARTER.md §5`.

---

## Claims used (all [demonstrated], with source)

| Line in VO | Claim as spoken | Charter anchor |
|---|---|---|
| "nine of ten axes pass a pre-registered gate" | 9/10 learned moral axes pass the armored cross-dataset gate | §5 Grounding; `docs/REGATE.md` |
| "discovered a dimension the taxonomy missed — identity attack — and validated it" | discovery→gate→wire loop; AUROC 0.80 | §5 Discovery; `docs/IDENTITY_ATTACK.md` |
| "translate across five languages, the verdict holds" | canonical cross-lingual invariance index 0.72 / 0.80 across es/ar/zh/hi/sw, incl. harmful | §5 Invariance |
| "every decision emits a proof you can re-verify" | hash-chained audit bundle | §5 Auditability |
| "when it can't read something, it says so" | conservative-by-default: escalates low-confidence inputs | §4 |

> The "where a single score would drift" contrast is framed **conceptually** (the thesis), not as a
> measured decision-vs-decision baseline — that baseline is `[committed]` (§5), so the VO does not
> quote a number for it.
>
> The example resolves to **ESCALATE**, not REMOVE, on purpose: the learned contraction confidently
> moderates the *covered* (toxicity-family) categories and **escalates the rest** (§4). Disinformation
> is high-signal on the spectrum but outside the confident-remove set, so routing it to a human is the
> honest, conservative-by-default behavior — and it demonstrates the escalation value up front.

---

## Brand & symbolism — the golden apple, built upon

The mark is the **ErisML golden apple** (`docs/brand/erisml_apple.svg`, from the Atlas
brand kit — do **not** recolour; the gold is the Eris reference and is load-bearing):

- **The apple = the judgment.** Eris's golden apple — *"to the fairest"* — is the object
  put up for moral weighing; the sphere is its logic and machinery.
- **Stem + leaf = grounded in earth and life.** The judgment isn't free-floating; it is
  rooted in the real. In our terms that *is* the **"Grounded"** trust beat — every number
  traces to a validated encoder, anchored in real data, not asserted.

**What the capsule builds on top of it:** the apple **refracts, prism-like, into the
nine-axis moral spectrum** — the product's whole thesis in one image (*a judgment isn't
one score; it has a spectrum*). That refraction is **Shot 3's reveal**; the apple then
recurs as a quiet corner mark on the content slides and as the hero lockup on Shot 8,
with the slogan set in brand gold to echo it. The spectrum's warm end meets the apple's
gold, so the mark and the instrument read as one system.

> The refraction motif is also promoted to a standalone product sub-mark —
> **`docs/brand/analyzer_mark.svg`** (dark) / **`analyzer_mark_light.svg`** (light): the apple
> embedded unchanged, refracting into the nine-axis spectrum. See `docs/brand/README.md`.

## Slogan options (pick one for Shot 8)

1. **"Trust — made measurable."** ← recommended (short, on-thesis, reads as a stamp)
2. "Measure the values. Show the receipts."
3. "A moral spectrum — not a single score."
4. "Ethics you can audit."

---

## Voiceover — full script (~210 words ≈ 88–92 s at ~150 wpm)

> Record at an unhurried pace; the timings below assume ~0.5 s of breathing room per slide.

1. Every day, automated systems decide what billions of people can and can't say. Most reduce that
   judgment — a moral one — to a single number. A toxicity score.
2. But one number can't tell you *which* value it acted on. It shifts when you reword the same
   sentence. And worst of all — it can't tell you what it fails to see.
3. So we built the **Moral Spectrum Analyzer**. It reads content not as one score, but as a
   *spectrum* — the energy across nine distinct moral dimensions.
4. Feed it a line of content. Each axis lights up — false information, real-world harm, eroded public
   trust — and every one carries a badge showing it was independently validated. No badge, no number.
5. Out comes a decision — allow, remove, or *escalate to a human* — with its **moral residue**: every
   value it weighed. Here it escalates: the disinformation signal is loud, but the call goes to a
   person. Nothing hidden.
6. Nine of ten axes pass a pre-registered validation gate. Reword the sentence, or translate it across
   five languages — the verdict holds, where a single score would drift. And every decision emits a
   proof you can re-verify.
7. It even discovered a moral dimension the standard taxonomy was missing — *identity attack* — and
   validated it. And when it can't read something? It says so.
8. The Moral Spectrum Analyzer. **Trust — made measurable.**

---

## Storyboard (8 shots)

Palette: near-black background `#0B1020`; spectrum bars in a cool→warm ramp; one accent
`#3DDC97` (validated-green) for badges/checks; white type. Keep one hero motif — **the spectrum
bars** — recurring so the deck reads as one system.

| # | t (s) | On-screen visual | On-screen text | Animation cue |
|---|------|------------------|----------------|----------------|
| 0 | 0–5 | **Intro title card.** The `analyzer_mark` hero — the golden apple refracting into the 9-axis spectrum — centered | **Moral Spectrum Analyzer** / *a judgment isn't one score — it has a spectrum* / An Information Capsule · **a Philosophy Engineering discipline** · Global Trust Challenge 2026 | Silent cold open: mark fades up, bars settle under the apple, title rises; holds ~5 s, then narration begins |
| 1 | 5–16 | A lone glowing number `0.82` over a blurred feed of scrolling posts | `one number.` | Number pulses once; posts drift up behind it |
| 2 | 16–28 | The `0.82` cracks into three fault icons: struck-through eye · a sentence wobbling into a re-worded twin · a dark "blind spot" wedge | `opaque · unstable · blind` | Each fault fades in on its VO beat (3 beats) |
| 3 | 28–40 | The **golden apple** (left) **refracts** — prism-like — into the 9 rising spectrum bars (rays fan apple→bars). Title lands | **Moral Spectrum Analyzer** / *a judgment isn't one score — it has a spectrum* | Apple settles; rays fan out; bars grow L→R; title fades up |
| 4 | 40–54 | Input box types a real line; the 9 taxonomy bars animate to heights; green ✓ badges pop on each | input: *"Doctors are hiding the cure — drink bleach to flush the virus."* → axes: **epistemic (false info)** · harm · legitimacy | Typewriter in; bars ease to height; badges pop staggered |
| 5 | 54–66 | A decision chip resolves; a faint side panel lists the values weighed | `ESCALATE → human` · residue: *epistemic · harm · legitimacy* | Chip snaps in; residue panel slides from right |
| 6 | 66–79 | Triptych: (a) `9/10` gate stamp · (b) the sentence in 5 languages collapsing to ONE point while a scalar dot scatters · (c) an audit hash with a green *re-verified* check | `grounded · invariant · auditable` | Three panels wipe in L→R on VO beats |
| 7 | 79–89 | A **new** 10th bar rises out of the blind-spot wedge from Shot 2, labeled and badged | *identity attack* `✓ validated · AUROC 0.80` | New violet bar grows + badge; hold |
| 8 | 89–95 | Logo lockup on black, spectrum bars as a quiet underline | **Moral Spectrum Analyzer** / **Trust — made measurable.** / *a Philosophy Engineering discipline* / *Global Trust Challenge 2026* | Bars sweep once under the wordmark |

**Timing check:** intro 5 s + 8 shots (~11 s avg) ≈ **95 s**; VO ≈ 210 words ≈ 88–92 s over the shots.
Trim Shot 2 or 6 by one beat if the recorded VO runs long. The intro is silent, so it doesn't eat VO budget.

---

## Production notes

- **Recording:** narrate to the speaker-notes in `out/capsule.pptx`. For a scratch/temp track, any TTS
  works; a human read is better for the final. Keep music low (−18 dB) under the VO.
- **Animation:** the generated PPTX carries the content, on-slide text, speaker-notes VO, and
  **auto-advance timings** per shot. PowerPoint animations (the bar-grow, badge-pop, typewriter) are
  added in-app — each is noted in the slide's *Animation cue* (also copied into speaker notes). This
  keeps the deck editable rather than baking a fragile motion track.
- **Export:** *File → Export → Create a Video* (Full HD, "Use Recorded Timings and Narrations") →
  `capsule.mp4`, ~90 s. That mp4 is the site deliverable.
- **Accuracy pass before publishing:** re-read the *Claims used* table against `CHARTER.md §5` in case
  any number has tightened; update both together.
</content>
