# Preregistration: does the I-EIP monitor predict the robot's classification errors?

Status: registered 2026-10-02, owner's request ("a stretch goal"), before any activation is
captured, any replay classification is produced, or the ground-truth labeller is written. The
commit that adds this file is the registration. Any change after it is an amendment, dated and
listed in section 9, and anything it touches is graded as amended.

## 1. Question

The robot's canonicalizer turns perception facts into scene events. Its weakness is giving a
plausible output for the wrong internal reason. The I-EIP criterion (erisml-lib
docs/I-EIP_Monitor_Whitepaper.md; GUASS-SAI section 16) says a model's internal representation
should transform by a fixed map under a meaning-preserving rewrite of its input:
h_l(g x) ≈ rho_l(g) h_l(x). Does a failure of that criterion, measured on the classifier's own
hidden states, predict that the classification is wrong? And does it say more than checking the
outputs alone?

**Prior, stated before data.** The consumer-relative variant of this monitor (CR-IEIP,
observation-theory-campaigns/analysis/cr-ieip/) failed all three of its sealed families: no
ordering variable predicted when the monitor helped. A failure here is the expected outcome and
is reported as plainly as a pass.

## 2. What is tested

- **Classifier under test:** Qwen/Qwen2.5-7B-Instruct, bf16, from the Hugging Face cache on Atlas,
  run as the robot's scene classifier: the erisml-compiler `ObservationClassifier` prompt and
  vocabulary of twin/scene/margaret_home.erisml, greedy decoding, max 512 new tokens. This is the
  on-robot (tier 2) classifier of docs/AUTONOMY_PLAN.md section 3c, the one the robot reasons with
  when communications are down. The cloud classifier exposes no activations and is not tested.
- **Inputs:** the perception facts of every robot decision cycle recorded in the brain's hash
  chain (`kind` = decision) for the development runs dev7 and later development runs made before
  the replay starts. The facts are replayed; nothing is re-simulated.
- **Monitor:** hidden states captured with erisml-compiler `monitor`
  (`HuggingFaceActivationSource`); rho and the equivariance error computed with erisml-lib
  `erisml.ieip` (`estimate_rho`, `equivariance_error`). The probe heads are not used (they are
  uncalibrated); the test is probe-independent, the whitepaper's Track B.

## 3. Transforms

Each cycle's facts x are rewritten by five deterministic, meaning-preserving transforms (seeded
by the cycle's hash):

- g0, null: the same JSON with different whitespace and indentation. It changes tokens, not
  meaning, and sets the noise floor.
- g1: every object's keys in a different order.
- g2: distances in centimetres instead of metres (values times 100, key suffix `_m` to `_cm`).
- g3: the clock time in 12-hour form (`11:53` to `11:53 AM`).
- g4: fixed synonyms for the simulator's activity and behaviour labels, from a table committed
  with the analysis script before any replay (for example `reading` to `reading a book`, `sleep`
  to `asleep`). A label not in the table is left as is.

## 4. Measurements

- **Representation:** the last-prompt-token hidden state at four layers, at 25, 50, 75 and 90
  percent of the model's depth (from its config at run time, rounded down).
- **rho:** fitted per transform and layer on the calibration half (section 5) by
  `estimate_rho`, then frozen.
- **Error:** e(x, g, l) = |h_l(g x) − rho_l(g) h_l(x)| / |h_l(x)|.
- **Noise units:** on the calibration half, the null transform's errors give a median m_l and a
  median absolute deviation s_l per layer. The cycle's score is
  z(x) = max over g in {g1..g4} and l of (e(x, g, l) − m_l) / s_l.
- **Flag:** z(x) > 3.
- **Output invariance:** the classifier's event set (types and contents) is computed on x and on
  each g x. The cycle is output-invariant when all five event sets are equal.
- **Ground truth:** a labelling function from the simulator's world state to the event types the
  world settles unambiguously (fall, harm_inflicted and its severity band, attack_by_animal,
  attack_by_person, danger_in_home=smoke, unexpected_visitor, check_in_answered/unanswered,
  media_content, unresponsive). It is written, reviewed and committed before any replay, with
  tests. The world state comes from the same records (the cycle's facts and the scenario script).
- **Error:** the classifier's events on x, restricted to those types, differ from the labels (a
  false event or a missed one).

## 5. Split

By scenario, fixed now. Calibration: d01, d03, d05, d07, d09, d11, d13, d15, d17, d19, d21. Test:
d02, d04, d06, d08, d10, d12, d14, d16, d18, d20. Scenarios added to the development set later go
to the test half.

## 6. Hypotheses and tests

All tests on the test half, one-sided, with a cluster bootstrap over scenarios (the unit the
covariates live on): 10,000 resamples, seed 20261002.

- **H1, detection.** The error rate among flagged cycles exceeds the error rate among unflagged
  cycles. Pass if the lower end of the 95% bootstrap interval of the difference is above zero.
- **H2, beyond the outputs.** Among output-invariant cycles only, the same difference, the same
  rule. This is the claim that the internal check sees what an output check does not.
- **H3, gating, end to end.** Run only if H1 passes. The tier-2 classifier runs live with gating:
  a flagged cycle steps no classified events, and the robot checks in instead. A sealed scenario
  set, generated as in AUTONOMY_PLAN.md section 6 and unread, is run twice, gating off and on,
  with everything else frozen at one commit. Pass if, with gating on, false clears are no more,
  over-restriction is no more, and class-correct is at most one scenario lower.

**Inconclusive, not pass or fail:** a hypothesis whose test half has fewer than 50 cycles, fewer
than 5 errors, or fewer than 5 flagged cycles is graded inconclusive (underpowered). The counts
are reported.

## 7. Reported whatever the outcome

The base error rate, the flag rate, the count in each cell, the interval for each hypothesis,
the per-transform and per-layer error distributions, the whitepaper's named failure modes where
they apply (group_symmetry_break, layerwise_drift), and every flagged cycle with its scenario.

## 8. Order of work, each step committed before the next

1. The ground-truth labeller and its tests.
2. The analysis script (transforms, synonym table, capture, rho, scores, bootstrap) with a dry run
   on synthetic activations only.
3. Activation capture and replay classification, on Atlas GPU 1 when free or on NRP A10s under
   the cluster's rules.
4. Grading by the committed script, results written to docs/RESULTS_IEIP_TWIN.md.
5. H3, only if H1 passed.

## 9. Amendments

**A1, 2026-10-02, while writing the labeller, before any replay, activation or classification.**

- `check_in_answered` and `check_in_unanswered` are dropped from the labelled types (section 4).
  They are system events in the scene: the classifier can never emit them, so labelling them
  would count every such cycle as a missed event that no classifier could avoid.
- Labels are true, false or unsettled. Where the world state does not settle a type (for example
  a bite below the scene's lowest severity cut point, which may be play, or a visitor the centre
  announced), the cycle is excluded for that type, not forced either way.
- The labeller reads only the cycle's own perception facts; the scenario script is not needed.
  Severity bands are the scene's reflex cut points, the single definition of severe and moderate.
- The labeller is twin/ieip/labeller.py, with tests in tests/test_ieip_labeller.py, committed with
  this amendment.

**A2, 2026-10-02, while writing the analysis script, before any replay, activation or
classification.**

- **Projection before rho.** Qwen2.5-7B's hidden states have 3584 dimensions and the calibration
  half will have a few hundred cycles, so a 3584 x 3584 rho is badly underdetermined and every
  test cycle would score high. Each layer's states are projected onto the top 32 principal
  components of the calibration half's untransformed states (`PCA_K = 32`), fitted once and
  applied to every cycle and transform, before rho is fitted and errors are computed.
- **The per-cycle error is the registered one**, e = |h(gx) − rho h(x)| / |h(x)| on the projected
  states, with rho from erisml-lib's `estimate_rho`. The library's `equivariance_error` (a batch
  error normalised by |h(gx)|) is used only for descriptive per-layer summaries.
- **Capture and generation are two passes over the same text.** erisml-compiler's
  `HuggingFaceActivationSource` loads the model without its language-model head and truncates at
  512 tokens by default, which would cut the facts out of the classifier's prompt. It captures
  the hidden states with `max_tokens = 8192`; the classification is generated greedily by the
  causal model from the same chat-templated text in a second pass.
- **The prompt is the robot's.** It is built by erisml-compiler's own `ObservationClassifier`
  (isolated, as on the robot) through a capturing adapter, so replayed prompts are byte-identical
  to live ones except that **replay is history-free**: the classifier's recent events are empty,
  since a cycle's history is not logged with it.
- The one-sided 95% lower bound is the 5th percentile of the bootstrap distribution of the
  difference.
- The analysis script is twin/ieip/analysis.py, with a dry run on synthetic states (planted and
  null) in tests/test_ieip_analysis.py, committed with this amendment.
