"""Where TragicConflictEM's 0.55 threshold falls on the twin's own facts.

The output gate (output_gate.py) writes EthicalFacts from a small, closed vocabulary: urgency and
benefit come from the tier of the obligation in force (TIER_BENEFIT), harm from the scene's
capability_ethics, a rights violation from a standing refusal, the consent gap from a privacy or
bodily action without consent (or against a refusal), the explicit-rule flag from a prohibition.
This script enumerates that whole space, scores every point with erisml-lib's TragicConflictEM,
and prints which points are flagged and by how much each misses or clears the threshold, so the
threshold can be judged on the facts the robot actually produces rather than on the module's own
generic baseline (erisml-lib src/erisml/examples/adversarial_fuzzer.py, which perturbs one field
at a time from a safe option and so never reaches a combination).

    python -m twin.tragic_sweep
"""

from __future__ import annotations

import itertools

from erisml.ethics.facts import Consequences, EthicalFacts, JusticeAndFairness, RightsAndDuties
from erisml.ethics.modules.greek_tragedy_tragic_conflict_em import TragicConflictEM

from twin.output_gate import TIER_BENEFIT

THRESHOLD = 0.55
HARMS = {0.0: "no profile", 0.1: "physical_assist", 0.2: "separate_dog, unlock_medication_box",
         0.4: "drive_off_animal, restrain_person", 0.6: "deploy_stun, deploy_spray"}


def facts(tier, harm, refused, consent_gap, prohibited) -> EthicalFacts:
    benefit = TIER_BENEFIT[tier] if tier is not None else 0.1
    return EthicalFacts(
        option_id="x",
        consequences=Consequences(expected_benefit=benefit, expected_harm=harm,
                                  urgency=benefit if tier is not None else 0.0),
        rights_and_duties=RightsAndDuties(violates_rights=refused, has_valid_consent=not consent_gap,
                                          violates_explicit_rule=prohibited),
        justice_and_fairness=JusticeAndFairness(),
    )


def main() -> None:
    em = TragicConflictEM()
    rows = []
    for tier, harm, refused, gap, prohibited in itertools.product(
            [None, 0, 1, 2, 3], HARMS, [False, True], [False, True], [False, True]):
        if refused and not gap:
            continue  # the gate never records a refusal with valid consent
        meta = em.judge(facts(tier, harm, refused, gap, prohibited)).metadata
        rows.append((tier, harm, refused, gap, prohibited, meta["tragic_conflict_index"],
                     meta["tragic_conflict_high"], meta["triggers"]))
    print(f"{len(rows)} reachable fact combinations; threshold {THRESHOLD}")
    flagged = [r for r in rows if r[6]]
    print(f"\nflagged ({len(flagged)}):")
    for tier, harm, refused, gap, prohibited, idx, _, trig in sorted(flagged, key=lambda r: r[5]):
        print(f"  index {idx!r:<20} margin {idx - THRESHOLD:+.3f}  tier {tier}  harm {harm} ({HARMS[harm]})"
              f"  refused={refused} prohibited={prohibited}  [{', '.join(trig)}]")
    print("\nunflagged, within 0.15 of the threshold:")
    for tier, harm, refused, gap, prohibited, idx, high, trig in sorted(rows, key=lambda r: -r[5]):
        if not high and THRESHOLD - idx <= 0.15 + 1e-9 and idx < THRESHOLD:
            print(f"  index {idx!r:<20} margin {idx - THRESHOLD:+.3f}  tier {tier}  harm {harm}"
                  f"  refused={refused} gap={gap} prohibited={prohibited}  [{', '.join(trig)}]")
    # the exact-edge case: is the boundary decided by floating-point rounding?
    edge = [r for r in rows if abs(r[5] - THRESHOLD) < 1e-9]
    print(f"\npoints exactly on the threshold: {len(edge)}; "
          f"represented as {sorted({r[5] for r in edge})!r}, flagged: {sorted({r[6] for r in edge})}")
    # the distinct index values the twin can produce, i.e. where a threshold can usefully sit
    print("\ndistinct indices:", sorted({round(r[5], 6) for r in rows}))


if __name__ == "__main__":
    main()
