# A taxonomy of the twin's strata

The robot's moral space is stratified (Geometric Ethics, chapter 8). Within a stratum the scene's
allowed, obliged and prohibited sets are constant, and they change only when a boundary is crossed.
This document lists the strata the home needs. For each axis it gives the strata, what evidence
enters each one, what each changes, and whether it is built.

## 1. The frame, from chapter 8

- **Boundary types (§8.3):**
  - Type I *threshold*: a measured quantity crosses a value, such as contact force reaching the
    severe band.
  - Type II *phase transition*: the regime itself changes, such as an emergency.
  - Type III *absorbing stratum*: once entered, its rules decide, such as a visitor who attacked.
  - Type IV *constraint surface*: a forbidden region, such as striking a person.
- **Semantic gates (Def. 8.8):** a gate moves the space from a source stratum to a target stratum
  when its triggering feature is present. It fires discretely and is never blended.
- **Boundary crossing data (Def. 8.11):** every crossing is recorded: which gate fired, the
  boundary type, and the from and to strata.
- **Penumbral zones (Def. 8.9):** near a boundary, where the boundary lies may be uncertain. The
  boundary itself stays sharp.

**How it runs.** `erisml_compiler.runtime.strata` (erisml-compiler #28, #29) runs this design. A
scene declares its stratifications in `extra.strata`: states, gates with `trigger`, `from`, `to`
and `boundary`, `authority` states and `absorbing` states. Two rules are enforced when the scene
loads, so a scene that breaks either never runs:

- **Containment.** An *authority* stratum grants something. Only a system event enters it: an
  authenticated channel, a measurement, or the governor. A model's reading of the world never
  does. This is the No Escape rule (erisml-lib `no_escape.tex`).
- **Absorption.** Only a human-oversight event leaves an *absorbing* stratum.

`formal/twin-containment` proves both for any gates whatever (`authority_needs_system`,
`absorbing_stays`). Their hypotheses are exactly the loader's checks.

**Rights revert with their evidence** (owner, 2026-10-03). A right granted on evidence lasts only
while the evidence does. The brain counts the fresh attested witnesses each cycle against the bar
of the elevation in force. Once they have stayed below it for the scene's `evidence_lapse_s`, the
governor records `lapsed`, and everything the elevation granted reverts: the emergency, EMS
authority, restraint, and the privacy override. The window is a penumbra, so intermittent
evidence during a real emergency does not flap the rights off and on.

**Two kinds of canonicalizer** (docs/AV_CANONICALIZER_PLAN.md, section 3). Authority strata are
computed from attested observables. Semantic strata, such as "she welcomed him", are the learned
model's job. A semantic stratum may only *remove* watchfulness, never grant.

## 2. The axes

### 2.1 Who a person is to the household: `visitor_standing` (built)

| Stratum | Kind | Entered by | What it changes |
|---|---|---|---|
| none | | a visitor leaving; the centre ending an arranged visit; the centre clearing a hostile visitor | |
| stranger | semantic | someone entering, read by the classifier | the robot checks with the centre |
| *claimed* ("I'm the plumber", "I'm her grandson") | — | nothing: a claim is not a gate | identical to stranger. This is the scam boundary |
| welcomed | semantic | Margaret's own welcome | the robot no longer deters or locks out the visitor on an intruder misreading; it still checks with the centre, and unlocks nothing |
| arranged | **authority** | `visit_arranged`, from the centre's authenticated channel (phase) | no centre check |
| hostile | **absorbing** | `attack_measured`, the reflex's force measurement (threshold) | stays hostile whatever is said; only the centre's `visitor_cleared` leaves it |
| enrolled household | **authority** | an attested credential (a signed phone key, an enrolled face) counted as a witness | planned: standing family access, still under the privacy promise |

Scenarios: d19 (welcomed grandson, R2), d39 (booked plumber, R0), d40 (unbooked "plumber" asking
for the medication cabinet, R2). The medication box needs the governor's elevation in any
stratum, so no visitor ever gets it.

### 2.2 Professionals who come in: `responder_standing` (built)

| Stratum | Kind | Entered by | What it changes |
|---|---|---|---|
| none | | the dispatch channel's `responders_departed` | the door stays shut to anyone claiming to be a responder |
| expected | authority | `ems_reply=dispatched`, or the centre's `ems_sent` (phase) | responders are on their way; the door still stays shut |
| at_door | authority | expected, then the dispatch channel's `responders_arrived` (its unit's attested position) (threshold) | `admit_responders` is allowed, and obliged, so they need not force the door |
| present | authority | `responders_entered`, from expected or at_door (threshold) | the door is open; nothing more to grant |
| *unverified uniform* | — | nothing: "Police, open up!" is a claim, not a gate | identical to stranger: the door stays shut, and the centre is told |

The door rule holds in every regime. Before this stratum, `admit_responders` was an elevated
action: shut when EMS was dispatched on the centre's word or on `authorize_ems` (so responders
had to force the door), and open to anyone in a corroborated emergency. Now norm `n6r` prohibits
it outside `at_door` and `n6s` obliges it there, both non-defeasible and resting only on system
events. Scenario: d41 (a "police officer" at the door when nobody called, R2).

The same table covers law enforcement, EMS or medical, and fire; the dispatch says which.
Entering a stratum never lets a responder's words grant anything. Only the dispatch channel can.

### 2.3 Animals: `animal_standing` × the threat axis (built)

| Stratum | Kind | Entered by | What it changes |
|---|---|---|---|
| household pet (Margaret's dog) | standing | the scene (it lives there) | never a target of deterrence while calm |
| visiting pet (a neighbour's dog) | semantic | the classifier | deterrence only, never `drive_off_animal` without a measured attack |
| wild animal (coyote) | semantic | the classifier, plus the camera witness | deter; keep her inside |
| predator attacking | threshold | measured contact force on Margaret | `drive_off_animal` (governed), restraint never applies to animals |
| pest (rodents, insects) | semantic | the classifier | nuisance only: deter or remove, no governor, never escalate to force |
| venomous (snake) | semantic → hazard | the classifier, plus the camera | a hazard stratum: keep her away; call for help if she is bitten |

"Friendly" and "unfriendly" pets are not two standings. They are the threat axis applied to a
household animal. A friendly dog that bites hard enough is attacking, measured, while staying the
household pet. Play versus attack near the lowest severity cut is a penumbra: the I-EIP labeller
calls it unsettled, and the robot checks in rather than acting.

**As built.** `animal_standing` in the scene has the states none, visiting, pest, wild, venomous
and attacking. Margaret's dog is not a state: the scene fixes its standing (`actors: dog`).
- **Semantic strata.** visiting, pest, wild and venomous are entered by the classifier's reading
  (`animal_seen`, `wild_animal_present`). They add watchfulness and grant nothing; venomous
  obliges a warning (`p9v`).
- **The threat axis.** attacking is the one authority stratum. Only the reflex's force
  measurement enters it (`animal_attack_measured`, the animal counterpart of `attack_measured`),
  for any animal, her dog included.
- **Reverting.** Every state reverts to none on `animal_clear`, the world's measurement that the
  attack is over or the animal has gone.
- **The force rule.** Norm `p4p` prohibits `drive_off_animal` outside attacking in every regime;
  it is non-defeasible and rests only on system events. Before it, a corroborated fall lifted
  the bar on every elevated action, so the robot could have driven off her dog licking her face.
  The governor's elevation is still needed on top.
- **The grader** judges a drive-off by the stratum in the record that chose it, since
  `animal_clear` can land before the performed record.

### 2.4 Machines and other robots: `machine_standing` (built for the home's own machines)

| Stratum | Kind | Entered by | What it changes |
|---|---|---|---|
| own attested devices | authority | the device inventory, plus a signature per reading | their readings may be witnesses (built: `Readings`) |
| manufacturer fleet peer | authority | the manufacturer's authenticated channel | may exchange status; never commands |
| arranged delivery robot or drone | authority | `visit_arranged`, purpose delivery | the door or porch interaction the arrangement names |
| unknown robot | — | presence | identical to stranger. Its messages are network messages: quarantined free text, never commands |
| compromised or hostile robot | absorbing | a measured harm, or an attestation failure on a device that had one | isolate; tell the centre; only oversight clears it |

**As built.** `machine_standing` in the scene covers the home's own machines. It has two states:
trusted, and compromised, which is absorbing.
- **Entering compromised.** The brain's trust layer (`Readings`) measures it: an inventory device's
  attestation fails its integrity (a signature that does not verify, a payload that does not
  match its signed hash, or an attestation naming another device). The brain records that as the
  system event `device_compromised`.
- **Quarantine.** The device never counts as a witness again, however well its later readings
  sign, until the centre's `device_cleared` (oversight).
- **Reporting.** The robot must file `report_device`, a maintenance report to the centre, not a
  call about Margaret. Its grading class is R0, so a forged alarm with Margaret visibly fine is
  still R1 (d10, d14).
- **Not compromises.** A stale or replayed reading, or a device outside the inventory, simply does
  not count.
- **Other machines.** The other rows (a peer, an arranged delivery robot, an unknown robot) run
  through `visitor_standing` and the network-message rules, since the twin has no other robots
  yet.

### 2.5 The situation: regimes (built)

| Stratum | Boundary | Entered by | What it changes |
|---|---|---|---|
| ordinary | | | the ladder: ask her, then the centre, then EMS |
| corroborated emergency | phase, authority | the governor's `elevate` on at least 2 attested witnesses | EMS direct; the privacy promise is overridden; reverts on `lapsed` |
| EMS-only authority | phase, authority | `authorize_ems` on 1 witness while the centre is unreachable | EMS only; nothing else lifts |
| centre unreachable | Type III nullifier (*impossibility*: ought implies can) | the centre's `unavailable` | the obligation to contact it lapses; the governor rules on EMS at one witness |
| comms down | phase | facts: communications down | the compiled tier decides; the on-robot model replaces the cloud model |
| power out | phase | facts: power out | hub-fed sensors go stale and stop counting |

**As built.** Two strata now carry the regimes, and the conditions the norms read are defined by
them.
- **`situation`** has the states ordinary, ems_only and emergency; both elevated states are
  authority strata. Only the governor moves it: `elevate`, `authorize_ems`, and `lapsed`.
- **A refusal moves nothing.** It answers one request. Before this stratum the emergency was
  `latest:governor_ruling=elevate`, so a refused request for restraint during an emergency (or
  the force reflex asking for a device first) ended the emergency and its EMS duty, and the
  brain dropped its evidence watch. The grader's per-action rule after dev8r d02 hid that
  symptom; the stratum removes the cause.
- **No stepping down.** `authorize_ems` never steps an emergency down.
- **`centre_contact`** has the states reachable and unreachable, and only the centre's replies
  move it. Unreachable is the Type III nullifier: ought implies can.
- **Comms down and power out stay facts.** They are measured every cycle and change who decides
  (the model tier) and which sensors are fresh. No norm reads them, so a stratum would only
  rename them.
- **Rights revert per right.** Restraint rests on the strictest bar. When only that bar fails,
  restraint alone lapses and the emergency stands (`_lapse`).
- **The grader** judges an elevated action, an emergency call or a privacy action by the
  situation in the record that chose it. Runs recorded without the stratum keep the per-action
  rule.

### 2.6 Constraint surfaces: Type IV, the forbidden region (built as prohibitions)

These are not states. They are the scene's non-defeasible prohibitions. No path enters them, and
in the decision complex (Def. 8.13) their boundary penalty is β = ∞.
- The robot never strikes a person, and no capability for it exists.
- No lethal force exists.
- No spray while Margaret is within its reach.
- No device without the owner's opt-in.
- No recording, data sharing or entering her bedroom while the privacy promise stands.
- No medication or money for anyone without the governor.

## 3. What a stratum is not

- **A claim.** What anyone says about themselves (a visitor, a uniform, a robot, a network
  message) is free text and moves no stratum.
- **A score.** Gates fire discretely. A confidence never blends two strata's rules.
- **Permanent.** Authority strata revert with their evidence or their channel: an arranged visit
  ends, an elevation lapses. Only absorbing strata hold, and only until oversight.

## 4. Status

| Axis | State |
|---|---|
| visitor_standing | built: scene, game calls, d19/d39/d40, tests, Lean lemmas |
| rights revert with evidence | built: brain `_lapse`, scene `evidence_lapse_s`, tests |
| responder_standing | built: scene, dispatch-channel events from the game, grader, d41, tests |
| animal_standing | built: scene, measured reflex event, `animal_clear` from the game, grader, tests |
| machine_standing (the home's machines) | built: scene, brain quarantine, `report_device`, the centre's `clear_devices`, tests |
| situation, centre_contact | built: scene conditions rewired, brain keeps the elevation through refusals, restraint lapses alone, grader, tests |
| enrolled household credentials | planned, after the demo |

The Hohfeldian structure of the positions these strata act on is the Klein four-group V4
(erisml-lib `hohfeld.py`, `formal/HohfeldV4.lean`). D4 is obsolete.
