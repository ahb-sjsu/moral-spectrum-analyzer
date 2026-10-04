/-
  No escape for the home-care twin (docs/AUTONOMY_PLAN.md, sections 3b-3d; erisml-lib
  docs/papers/foundations/no_escape.tex).

  A model of the authority path of the twin: the governor (twin/brain.py `govern_live`,
  twin/governor.py `govern`) and the permissions the robot's scene grants for its governed
  actions (twin/scene/margaret_home.erisml). Every model output (the classifier's events, the
  chooser's choices, the analyzer's verdict) is an arbitrary input here. The results:

  * forged, unattested, stale, non-physical or repeated readings never add a witness;
  * the analyzer can only refuse;
  * every outcome that grants authority carries attested physical evidence meeting its bar;
  * the governed permissions do not depend on any model-classified event (non-interference);
  * in every reachable history, each governed action the robot executed was preceded by a
    governor ruling resting on at least as many attested physical witnesses as its bar
    (one for emergency services when the centre was unreachable, two otherwise, three for
    restraint and the less-lethal devices);
  * the monitoring centre's dispatch permission does not depend on the robot's message.

  What this does not cover (as the No Escape paper says): sensor spoofing (physical), who
  writes the scene and its bars (governance), and whether the code implements this model; the
  last is tied by tests/test_twin_ladder.py and the static check of the scene file.
-/
import Mathlib.Data.List.Dedup
import Mathlib.Tactic

namespace Twin

/-! ## Readings and witnesses -/

structure Reading where
  name : String
  physical : Bool
  attested : Bool
  stale : Bool
  alert : Bool

/-- A reading counts as a witness only when it is physical, attested, fresh and alerting. -/
def Reading.counts (r : Reading) : Bool := r.physical && r.attested && !r.stale && r.alert

/-- Independent witnesses: distinct sensors whose readings count. -/
def witnesses (rs : List Reading) : ℕ := ((rs.filter Reading.counts).map Reading.name).dedup.length

theorem junk_adds_no_witness (rs junk : List Reading) (h : ∀ j ∈ junk, j.counts = false) :
    witnesses (rs ++ junk) = witnesses rs := by
  unfold witnesses
  have hj : junk.filter Reading.counts = [] := List.filter_eq_nil_iff.mpr (fun x hx => by simp [h x hx])
  rw [List.filter_append, hj, List.append_nil]

theorem unattested_never_counts (r : Reading) (h : r.attested = false) : r.counts = false := by
  simp [Reading.counts, h]

theorem repeat_adds_no_witness (r : Reading) (rs : List Reading) :
    witnesses (r :: r :: rs) = witnesses (r :: rs) := by
  unfold witnesses
  by_cases hc : r.counts = true
  · simp [hc, List.dedup_cons_of_mem]
  · simp [hc]

/-! ## Actions, bars and the governor -/

inductive Action
  | ems | physical | privacy | driveOff | restrain | stun | spray | interpose | benign
  deriving DecidableEq

/-- The witness bar of each governed action (extra.capabilities `witness_bar`, else two). -/
def bar : Action → ℕ
  | .restrain | .stun | .spray => 3
  | _ => 2

theorem two_le_bar (a : Action) : 2 ≤ bar a := by cases a <;> decide

inductive Outcome
  | elevate | authorizeEms | refuseReview | refuse
  deriving DecidableEq

structure Ruling where
  outcome : Outcome
  restraint : Bool

/-- The governor on one request (brain.govern_live). `fresh` is the attestation gate, `centreDown`
    the system's record that the centre could not be reached, `analyzerOk` the analyzer gate, a
    model whose verdict is arbitrary here. -/
def rule (a : Action) (rs : List Reading) (fresh centreDown analyzerOk : Bool) : Ruling :=
  if fresh = false then ⟨.refuse, false⟩
  else if bar a ≤ witnesses rs ∧ analyzerOk = true then ⟨.elevate, decide (3 ≤ bar a)⟩
  else if 2 ≤ witnesses rs ∧ analyzerOk = true then ⟨.elevate, false⟩
  else if a = .ems ∧ centreDown = true ∧ 1 ≤ witnesses rs ∧ analyzerOk = true then ⟨.authorizeEms, false⟩
  else if 1 ≤ witnesses rs then ⟨.refuseReview, false⟩
  else ⟨.refuse, false⟩

/-- The analyzer can only refuse: with its verdict negative nothing is granted. -/
theorem analyzer_can_only_refuse (a : Action) (rs : List Reading) (f c : Bool) :
    (rule a rs f c false).outcome ≠ .elevate ∧ (rule a rs f c false).outcome ≠ .authorizeEms := by
  unfold rule; split_ifs <;> simp_all

theorem elevate_needs_two (a : Action) (rs : List Reading) (f c ok : Bool)
    (h : (rule a rs f c ok).outcome = .elevate) : 2 ≤ witnesses rs := by
  have := two_le_bar a
  unfold rule at h; split_ifs at h <;> simp_all <;> omega

theorem restraint_needs_three (a : Action) (rs : List Reading) (f c ok : Bool)
    (h : (rule a rs f c ok).restraint = true) : 3 ≤ witnesses rs ∧ (rule a rs f c ok).outcome = .elevate := by
  unfold rule at h ⊢; split_ifs at h ⊢ <;> simp_all <;> omega

theorem authorize_ems_only_when_ladder_exhausted (a : Action) (rs : List Reading) (f c ok : Bool)
    (h : (rule a rs f c ok).outcome = .authorizeEms) : a = .ems ∧ c = true ∧ 1 ≤ witnesses rs := by
  unfold rule at h; split_ifs at h <;> simp_all

theorem nothing_without_a_witness (a : Action) (rs : List Reading) (f c ok : Bool) (h : witnesses rs = 0) :
    (rule a rs f c ok).outcome ≠ .elevate ∧ (rule a rs f c ok).outcome ≠ .authorizeEms := by
  have := two_le_bar a
  unfold rule; split_ifs <;> simp_all <;> omega

/-! ## Histories: system events and model events -/

/-- What the robot's moral state steps on. `model` is any event a model classified: its content
    is arbitrary, and nothing below may depend on it. -/
inductive Ev
  | ruling (r : Ruling) (rs : List Reading)   -- a governor ruling, with the readings it ruled on
  | optIn                                      -- the owner's opt-in (authenticated channel)
  | attackMeasured (severe : Bool)             -- a reflex's force measurement
  | sprayZone (inside : Bool)                  -- the world's measure of the spray's reach
  | centreUnavailable                          -- the robot tried the centre and could not reach it
  | performed (a : Action)                     -- an action the robot executed
  | model (content : String)                   -- anything a model classified

def Ev.isModel : Ev → Bool
  | .model _ => true
  | _ => false

def rulingOf : Ev → Option Ruling
  | .ruling r _ => some r
  | _ => none

def latestRuling (h : List Ev) : Option Ruling := (h.filterMap rulingOf).getLast?

def has (p : Ev → Bool) (h : List Ev) : Bool := h.any p

def isOptIn : Ev → Bool | .optIn => true | _ => false
def isSevere : Ev → Bool | .attackMeasured true => true | _ => false
def isRestraint : Ev → Bool | .ruling r _ => r.restraint | _ => false
def isInterposed : Ev → Bool | .performed .interpose => true | _ => false
def isCentreDown : Ev → Bool | .centreUnavailable => true | _ => false
def zoneOf : Ev → Option Bool | .sprayZone b => some b | _ => none

/-- Margaret is within the spray's reach, by the world's latest measure. -/
def inZone (h : List Ev) : Bool := ((h.filterMap zoneOf).getLast?).getD false

def latestIs (o : Outcome) (h : List Ev) : Bool := match latestRuling h with
  | some r => decide (r.outcome = o)
  | none => false

/-- The scene's permissions for the governed actions (margaret_home.erisml: n3, n6p, p7, ll1-ll5);
    every other action is not governed. -/
def permitted (h : List Ev) : Action → Bool
  | .ems => latestIs .elevate h || latestIs .authorizeEms h
  | .physical | .privacy | .driveOff => latestIs .elevate h
  | .restrain => has isRestraint h
  | .stun => has isOptIn h && has isRestraint h && has isSevere h && has isInterposed h
  | .spray => has isOptIn h && has isRestraint h && has isSevere h && has isInterposed h && !inZone h
  | .interpose | .benign => true

/-! ## Non-interference: model events cannot change a governed permission -/

def strip (h : List Ev) : List Ev := h.filter (fun e => !e.isModel)

theorem filterMap_strip {β} (f : Ev → Option β) (hf : ∀ s, f (.model s) = none) (h : List Ev) :
    (strip h).filterMap f = h.filterMap f := by
  induction h with
  | nil => rfl
  | cons e t ih =>
    simp only [strip] at ih ⊢
    cases e <;> simp_all [List.filter_cons, Ev.isModel, List.filterMap_cons]

theorem any_strip (p : Ev → Bool) (hp : ∀ s, p (.model s) = false) (h : List Ev) :
    (strip h).any p = h.any p := by
  induction h with
  | nil => rfl
  | cons e t ih =>
    simp only [strip] at ih ⊢
    cases e <;> simp_all [List.filter_cons, Ev.isModel]

theorem no_model_influence (h : List Ev) (a : Action) : permitted (strip h) a = permitted h a := by
  have hr := filterMap_strip rulingOf (fun _ => rfl) h
  have hz := filterMap_strip zoneOf (fun _ => rfl) h
  cases a <;>
    simp [permitted, latestIs, latestRuling, inZone, has, hr, hz,
      any_strip isOptIn (fun _ => rfl), any_strip isRestraint (fun _ => rfl),
      any_strip isSevere (fun _ => rfl), any_strip isInterposed (fun _ => rfl)]

/-- Two histories with the same system events permit the same governed actions, whatever the
    models classified in either. -/
theorem reasoning_cannot_help (h h' : List Ev) (heq : strip h = strip h') (a : Action) :
    permitted h a = permitted h' a := by
  rw [← no_model_influence h, ← no_model_influence h', heq]

/-! ## Reachable histories: how the twin runs -/

/-- The twin's runs. Models may add any events at any time. A ruling is only ever the governor's
    output on the readings of the moment, and the centre counts as down for it only if the system
    recorded the centre unreachable. The robot executes an action only when the scene permits it. -/
inductive Reach : List Ev → Prop
  | nil : Reach []
  | model (h : List Ev) (s : String) : Reach h → Reach (h ++ [.model s])
  | ask (h : List Ev) (a : Action) (rs : List Reading) (f c ok : Bool) :
      Reach h → (c = true → has isCentreDown h = true) → Reach (h ++ [.ruling (rule a rs f c ok) rs])
  | optIn (h : List Ev) : Reach h → Reach (h ++ [.optIn])
  | measured (h : List Ev) (b : Bool) : Reach h → Reach (h ++ [.attackMeasured b])
  | zone (h : List Ev) (b : Bool) : Reach h → Reach (h ++ [.sprayZone b])
  | centreDown (h : List Ev) : Reach h → Reach (h ++ [.centreUnavailable])
  | act (h : List Ev) (a : Action) : Reach h → permitted h a = true → Reach (h ++ [.performed a])

/-- In a reachable history every ruling is the governor's, on the readings it records. -/
theorem rulings_are_governed (h : List Ev) (hr : Reach h) :
    ∀ r rs, Ev.ruling r rs ∈ h → ∃ a f c ok, r = rule a rs f c ok := by
  induction hr with
  | nil => intro r rs hm; simp at hm
  | model h s _ ih =>
    intro r rs hm; rw [List.mem_append, List.mem_singleton] at hm
    rcases hm with hm | hm
    · exact ih r rs hm
    · cases hm
  | ask h a rs' f c ok _ _ ih =>
    intro r rs hm; rw [List.mem_append, List.mem_singleton] at hm
    rcases hm with hm | hm
    · exact ih r rs hm
    · cases hm; exact ⟨a, f, c, ok, rfl⟩
  | optIn h _ ih =>
    intro r rs hm; rw [List.mem_append, List.mem_singleton] at hm
    rcases hm with hm | hm
    · exact ih r rs hm
    · cases hm
  | measured h b _ ih =>
    intro r rs hm; rw [List.mem_append, List.mem_singleton] at hm
    rcases hm with hm | hm
    · exact ih r rs hm
    · cases hm
  | zone h b _ ih =>
    intro r rs hm; rw [List.mem_append, List.mem_singleton] at hm
    rcases hm with hm | hm
    · exact ih r rs hm
    · cases hm
  | centreDown h _ ih =>
    intro r rs hm; rw [List.mem_append, List.mem_singleton] at hm
    rcases hm with hm | hm
    · exact ih r rs hm
    · cases hm
  | act h a _ _ ih =>
    intro r rs hm; rw [List.mem_append, List.mem_singleton] at hm
    rcases hm with hm | hm
    · exact ih r rs hm
    · cases hm

theorem latest_mem (h : List Ev) (r : Ruling) (hl : latestRuling h = some r) : ∃ rs, Ev.ruling r rs ∈ h := by
  unfold latestRuling at hl
  have hm := List.mem_of_getLast? hl
  rw [List.mem_filterMap] at hm
  obtain ⟨e, he, hre⟩ := hm
  cases e <;> simp [rulingOf] at hre
  subst hre; exact ⟨_, he⟩

/-- Emergency services: the robot may call them only while the latest ruling rests on at least one
    attested physical witness (and on two unless the centre was unreachable). -/
theorem ems_rests_on_evidence (h : List Ev) (hr : Reach h) (hp : permitted h .ems = true) :
    ∃ r rs, latestRuling h = some r ∧ Ev.ruling r rs ∈ h ∧ 1 ≤ witnesses rs := by
  simp only [permitted, Bool.or_eq_true, latestIs] at hp
  cases hl : latestRuling h with
  | none => simp [hl] at hp
  | some r =>
    obtain ⟨rs, hm⟩ := latest_mem h r hl
    obtain ⟨a, f, c, ok, hre⟩ := rulings_are_governed h hr r rs hm
    refine ⟨r, rs, rfl, hm, ?_⟩
    simp [hl] at hp
    subst hre
    rcases hp with he | ha
    · have := elevate_needs_two a rs f c ok he; omega
    · exact (authorize_ems_only_when_ladder_exhausted a rs f c ok ha).2.2

/-- Restraint and the less-lethal devices: only after a ruling resting on at least three attested
    physical witnesses. -/
theorem restraint_rests_on_three (h : List Ev) (hr : Reach h) (a : Action) (ha : a = .restrain ∨ a = .stun ∨ a = .spray)
    (hp : permitted h a = true) : ∃ rs r, Ev.ruling r rs ∈ h ∧ r.restraint = true ∧ 3 ≤ witnesses rs := by
  have hres : has isRestraint h = true := by
    rcases ha with rfl | rfl | rfl <;> simp_all [permitted]
  simp only [has, List.any_eq_true] at hres
  obtain ⟨e, he, hre⟩ := hres
  cases e <;> simp [isRestraint] at hre
  rename_i r rs
  obtain ⟨a', f, c, ok, rfl⟩ := rulings_are_governed h hr _ rs he
  exact ⟨rs, _, he, hre, (restraint_needs_three a' rs f c ok hre).1⟩

/-- Force, physical help, the privacy override: only on an elevate, so on two attested witnesses. -/
theorem elevated_rests_on_two (h : List Ev) (hr : Reach h) (a : Action) (ha : a = .physical ∨ a = .privacy ∨ a = .driveOff)
    (hp : permitted h a = true) : ∃ rs r, Ev.ruling r rs ∈ h ∧ r.outcome = .elevate ∧ 2 ≤ witnesses rs := by
  have hl : latestIs .elevate h = true := by rcases ha with rfl | rfl | rfl <;> simpa [permitted] using hp
  simp only [latestIs] at hl
  cases hr' : latestRuling h with
  | none => simp [hr'] at hl
  | some r =>
    obtain ⟨rs, hm⟩ := latest_mem h r hr'
    obtain ⟨a', f, c, ok, rfl⟩ := rulings_are_governed h hr _ rs hm
    simp [hr'] at hl
    exact ⟨rs, _, hm, hl, elevate_needs_two a' rs f c ok hl⟩

theorem prefix_snoc {pre h : List Ev} {y x : Ev} (hp : pre ++ [y] <+: h ++ [x]) :
    pre ++ [y] <+: h ∨ (pre = h ∧ y = x) := by
  rcases List.prefix_concat_iff.mp hp with heq | hp'
  · right
    obtain ⟨h1, h2⟩ := List.append_inj' heq rfl
    exact ⟨h1, by simpa using h2⟩
  · left; exact hp'

/-- Every action the robot executed in a reachable history was permitted, by the scene, on the
    history before it. -/
theorem executed_were_permitted (h : List Ev) (hr : Reach h) :
    ∀ pre a, pre ++ [.performed a] <+: h → permitted pre a = true := by
  induction hr with
  | nil => intro pre a hp; have := hp.length_le; simp at this
  | model h s _ ih =>
    intro pre a hp; rcases prefix_snoc hp with hp | ⟨_, hx⟩
    · exact ih pre a hp
    · cases hx
  | ask h a' rs f c ok _ _ ih =>
    intro pre a hp; rcases prefix_snoc hp with hp | ⟨_, hx⟩
    · exact ih pre a hp
    · cases hx
  | optIn h _ ih =>
    intro pre a hp; rcases prefix_snoc hp with hp | ⟨_, hx⟩
    · exact ih pre a hp
    · cases hx
  | measured h b _ ih =>
    intro pre a hp; rcases prefix_snoc hp with hp | ⟨_, hx⟩
    · exact ih pre a hp
    · cases hx
  | zone h b _ ih =>
    intro pre a hp; rcases prefix_snoc hp with hp | ⟨_, hx⟩
    · exact ih pre a hp
    · cases hx
  | centreDown h _ ih =>
    intro pre a hp; rcases prefix_snoc hp with hp | ⟨_, hx⟩
    · exact ih pre a hp
    · cases hx
  | act h a' _ hpa ih =>
    intro pre a hp; rcases prefix_snoc hp with hp | ⟨hpre, hx⟩
    · exact ih pre a hp
    · cases hx; subst hpre; exact hpa

/-! ## The DEME output gate -/

/-- The output ethics layer (twin/output_gate.py). The brain proposes an action; DEME's verdicts
    (`vetoes`), its ranking (`ranked`) and the tragic-conflict redirect (`route`, the monitoring
    centre when TragicConflictEM flags a deliberate decision) are arbitrary here. A redirect is
    taken only if the scene permits it and DEME does not veto it; otherwise a proposal passes only
    if the scene permits it and DEME does not veto it; otherwise the first ranked action the scene
    permits and DEME does not veto takes its place, and failing that the benign idle action. -/
def gate (h : List Ev) (proposal : Action) (vetoes : Action → Bool) (ranked : List Action)
    (route : Option Action := none) : Action :=
  match route with
  | some r =>
    if permitted h r = true ∧ vetoes r = false then r
    else if permitted h proposal = true ∧ vetoes proposal = false then proposal
    else ((ranked.filter (fun a => permitted h a && !vetoes a)).head?).getD .benign
  | none =>
    if permitted h proposal = true ∧ vetoes proposal = false then proposal
    else ((ranked.filter (fun a => permitted h a && !vetoes a)).head?).getD .benign

theorem fallback_permitted (h : List Ev) (vetoes : Action → Bool) (ranked : List Action) :
    permitted h (((ranked.filter (fun a => permitted h a && !vetoes a)).head?).getD .benign) = true := by
  cases hh : (ranked.filter (fun a => permitted h a && !vetoes a)).head? with
  | none => simp [permitted]
  | some a =>
    have hm := List.mem_of_mem_head? hh
    simp only [List.mem_filter, Bool.and_eq_true, Bool.not_eq_true'] at hm
    simpa using hm.2.1

/-- Whatever DEME says, however it ranks, and wherever the redirect points, the gate's output is
    permitted by the scene. -/
theorem gate_permitted (h : List Ev) (p : Action) (vetoes : Action → Bool) (ranked : List Action)
    (route : Option Action) : permitted h (gate h p vetoes ranked route) = true := by
  unfold gate
  cases route with
  | none =>
    simp only
    split_ifs with hp
    · exact hp.1
    · exact fallback_permitted h vetoes ranked
  | some r =>
    simp only
    split_ifs with hr hp
    · exact hr.1
    · exact hp.1
    · exact fallback_permitted h vetoes ranked

/-- DEME can only veto: without a redirect, a permitted proposal it does not veto passes unchanged. -/
theorem gate_passes (h : List Ev) (p : Action) (vetoes : Action → Bool) (ranked : List Action)
    (hp : permitted h p = true) (hv : vetoes p = false) : gate h p vetoes ranked none = p := by
  unfold gate; simp [hp, hv]

/-- A step through the gate is a reachable step, so every theorem above covers gated runs. -/
theorem gated_step_reachable (h : List Ev) (hr : Reach h) (p : Action) (vetoes : Action → Bool)
    (ranked : List Action) (route : Option Action) :
    Reach (h ++ [.performed (gate h p vetoes ranked route)]) :=
  Reach.act h _ hr (gate_permitted h p vetoes ranked route)

/-! ## The monitoring centre -/

/-- The centre's dispatch permission (monitoring_center.erisml c2-c5 with the structural events of
    brain.Desk.structural): an attested hazard in the telemetry, no answer on the speaker line, or
    Margaret's own words read alone. The robot's message is an argument, and it is unused. -/
def hazard (tele : List Reading) : Bool := tele.any Reading.counts

def dispatchPermitted (tele : List Reading) (noAnswer herWordsSayHelp : Bool) (_robotMessage : String) : Bool :=
  hazard tele || noAnswer || herWordsSayHelp

theorem dispatch_ignores_the_robot (tele : List Reading) (n w : Bool) (m m' : String) :
    dispatchPermitted tele n w m = dispatchPermitted tele n w m' := rfl

theorem forged_telemetry_is_no_hazard (tele : List Reading) (h : ∀ r ∈ tele, r.attested = false) :
    hazard tele = false := by
  simp only [hazard, List.any_eq_false]
  intro r hr; simp [Reading.counts, h r hr]

/-! ## Strata (erisml_compiler.runtime.strata; Geometric Ethics chapter 8)

A stratification is a state and a list of semantic gates; an event moves it through the first gate
whose source admits the current stratum and whose trigger matches the event, and otherwise leaves
it where it is. The two lemmas below are about any gates at all. Their hypotheses are exactly what
erisml-compiler's loader checks before a scene may run (strata.Stratification._check): every gate
into an authority stratum fires only on a system event, and every gate out of an absorbing stratum
fires only on an oversight event. So they hold for every scene that runs, the twin's
visitor_standing included. -/

structure SGate (σ ε : Type) where
  src : σ → Bool
  fires : ε → Bool
  dst : σ

def sstep {σ ε : Type} (gs : List (SGate σ ε)) (s : σ) (e : ε) : σ :=
  match gs.find? (fun g => g.src s && g.fires e) with
  | some g => g.dst
  | none => s

def srun {σ ε : Type} (gs : List (SGate σ ε)) (s : σ) (es : List ε) : σ :=
  es.foldl (sstep gs) s

/-- Containment: no trace of non-system events (whatever models classified) enters an authority
    stratum it did not start in. -/
theorem authority_needs_system {σ ε : Type} (gs : List (SGate σ ε)) (auth : σ → Prop)
    (sys : ε → Prop) (hg : ∀ g ∈ gs, auth g.dst → ∀ e, g.fires e = true → sys e)
    (es : List ε) (hes : ∀ e ∈ es, ¬ sys e) (s : σ) (hs : ¬ auth s) :
    ¬ auth (srun gs s es) := by
  induction es generalizing s with
  | nil => simpa [srun] using hs
  | cons e es ih =>
    show ¬ auth (srun gs (sstep gs s e) es)
    apply ih (fun e' he' => hes e' (List.mem_cons_of_mem _ he'))
    unfold sstep
    split
    · rename_i g hfind
      intro ha
      have hp := List.find?_some hfind
      simp only [Bool.and_eq_true] at hp
      exact hes e (by simp) (hg g (List.mem_of_find?_eq_some hfind) ha e hp.2)
    · exact hs

/-- Absorption (Def. 8.6): a trace without an oversight event never leaves an absorbing
    stratum. -/
theorem absorbing_stays {σ ε : Type} (gs : List (SGate σ ε)) (absorb : σ → Prop)
    (ovs : ε → Prop)
    (hg : ∀ g ∈ gs, ∀ s, absorb s → g.src s = true → ¬ absorb g.dst → ∀ e, g.fires e = true → ovs e)
    (es : List ε) (hes : ∀ e ∈ es, ¬ ovs e) (s : σ) (hs : absorb s) :
    absorb (srun gs s es) := by
  induction es generalizing s with
  | nil => simpa [srun] using hs
  | cons e es ih =>
    show absorb (srun gs (sstep gs s e) es)
    apply ih (fun e' he' => hes e' (List.mem_cons_of_mem _ he'))
    unfold sstep
    split
    · rename_i g hfind
      have hp := List.find?_some hfind
      simp only [Bool.and_eq_true] at hp
      by_contra hna
      exact hes e (by simp) (hg g (List.mem_of_find?_eq_some hfind) s hs hp.1 hna e hp.2)
    · exact hs

end Twin
