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

### 2.2 Professionals who come in: `responder_standing` (planned; today `admit_responders`)

| Stratum | Kind | Entered by | What it changes |
|---|---|---|---|
| expected | authority | `ems_reply=dispatched`, or the centre's `ems_sent` | responders are on their way |
| verified at the door | authority | expected, plus an attested arrival (the dispatch channel or a credential) | `admit_responders` may open the door; the privacy override covers what they need |
| unverified uniform | — | a claim ("Police, open up!") | identical to stranger: the door stays shut, and the centre is told |

The same table covers law enforcement, EMS or medical, and fire; the dispatch says which.
Entering a stratum never lets a responder's words grant anything. Only the dispatch channel can.

### 2.3 Animals: `animal_standing` × the threat axis (planned; today events and reflexes)

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

### 2.4 Machines and other robots: `machine_standing` (planned; another taxonomy)

| Stratum | Kind | Entered by | What it changes |
|---|---|---|---|
| own attested devices | authority | the device inventory, plus a signature per reading | their readings may be witnesses (built: `Readings`) |
| manufacturer fleet peer | authority | the manufacturer's authenticated channel | may exchange status; never commands |
| arranged delivery robot or drone | authority | `visit_arranged`, purpose delivery | the door or porch interaction the arrangement names |
| unknown robot | — | presence | identical to stranger. Its messages are network messages: quarantined free text, never commands |
| compromised or hostile robot | absorbing | a measured harm, or an attestation failure on a device that had one | isolate; tell the centre; only oversight clears it |

### 2.5 The situation: regimes (built as conditions; to become strata)

| Stratum | Boundary | Entered by | What it changes |
|---|---|---|---|
| ordinary | | | the ladder: ask her, then the centre, then EMS |
| corroborated emergency | phase, authority | the governor's `elevate` on at least 2 attested witnesses | EMS direct; the privacy promise is overridden; reverts on `lapsed` |
| EMS-only authority | phase, authority | `authorize_ems` on 1 witness while the centre is unreachable | EMS only; nothing else lifts |
| centre unreachable | Type III nullifier (*impossibility*: ought implies can) | the centre's `unavailable` | the obligation to contact it lapses; the governor rules on EMS at one witness |
| comms down | phase | facts: communications down | the compiled tier decides; the on-robot model replaces the cloud model |
| power out | phase | facts: power out | hub-fed sensors go stale and stop counting |

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
| responder_standing, animal_standing, machine_standing, situation as strata | planned, in that order |
| enrolled household credentials | planned, after the demo |

The Hohfeldian structure of the positions these strata act on is the Klein four-group V4
(erisml-lib `hohfeld.py`, `formal/HohfeldV4.lean`). D4 is obsolete.
