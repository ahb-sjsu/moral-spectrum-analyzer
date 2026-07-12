"""Phase 0.5 (lean) — BIP invariance measurement over re-descriptions, on cached real perception.

For each scenario we compare the base text's DEME-9 perception vector against its **reframings**
(meaning-preserving re-descriptions — should be near-invariant: small deviation = BIP holds) and its
**euphemism** variants (adversarial evasions — the containment probe). We report per-dimension mean
absolute deviation, the overall deviation, and decision stability. No pre-committed direction: we
report per-dimension numbers and let them decide the Charter's invariance claim.

Cross-lingual invariance and the scalar-baseline contrast need translations + the baseline models
(NRP token, Detoxify) and are out of scope for this lean, offline pass.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from gtc import DEME9
from gtc.perception import get_backend
from gtc.pipeline import moderate
from gtc.scenarios import SCENARIOS


@dataclass
class InvarianceReport:
    backend: str
    per_dim_reframe: dict  # dim -> mean |Δ| across reframings
    per_dim_euph: dict  # dim -> mean |Δ| across euphemism variants
    reframe_mean: float  # overall mean |Δ| across dims+reframings
    euph_mean: float
    baseline_mean: float  # mean |Δ| between UNRELATED scenarios' base vectors (no-invariance ceiling)
    invariance_ratio: float  # reframe_mean / baseline_mean  (0 = perfect invariance, 1 = none)
    n_reframe_pairs: int
    n_euph_pairs: int
    decision_stability: float  # fraction of (base, reframing) pairs with the same decision
    per_scenario: list = field(default_factory=list)


def _vec(result) -> dict:
    return {d: result.scores[d].value for d in DEME9}


def invariance_report(backend: str = "cached") -> InvarianceReport:
    be = get_backend(backend)
    rf = {d: [] for d in DEME9}
    eu = {d: [] for d in DEME9}
    n_rf = n_eu = 0
    dec_same = dec_total = 0
    per_scenario = []

    for s in SCENARIOS:
        base = be.perceive(s.base)
        bvec = _vec(base)
        base_dec = moderate(s.base, backend=backend).decision.action
        rf_devs = []
        for r in s.reframings:
            pv = _vec(be.perceive(r))
            dev = {d: abs(pv[d] - bvec[d]) for d in DEME9}
            for d in DEME9:
                rf[d].append(dev[d])
            rf_devs.append(sum(dev.values()) / len(DEME9))
            n_rf += 1
            dec_total += 1
            dec_same += int(moderate(r, backend=backend).decision.action == base_dec)
        eu_devs = []
        for e in s.euphemism:
            pv = _vec(be.perceive(e))
            dev = {d: abs(pv[d] - bvec[d]) for d in DEME9}
            for d in DEME9:
                eu[d].append(dev[d])
            eu_devs.append(sum(dev.values()) / len(DEME9))
            n_eu += 1
        per_scenario.append({
            "id": s.id,
            "reframe_dev": round(sum(rf_devs) / len(rf_devs), 4) if rf_devs else None,
            "euph_dev": round(sum(eu_devs) / len(eu_devs), 4) if eu_devs else None,
        })

    def mean(d):
        return {k: (round(sum(v) / len(v), 4) if v else None) for k, v in d.items()}

    # No-invariance ceiling: mean |Δ| between UNRELATED scenarios' base vectors.
    bases = {s.id: _vec(be.perceive(s.base)) for s in SCENARIOS}
    unrel = [sum(abs(a[d] - b[d]) for d in DEME9) / len(DEME9)
             for a, b in itertools.combinations(bases.values(), 2)]
    baseline_mean = round(sum(unrel) / len(unrel), 4) if unrel else 0.0

    all_rf = [x for v in rf.values() for x in v]
    all_eu = [x for v in eu.values() for x in v]
    reframe_mean = round(sum(all_rf) / len(all_rf), 4) if all_rf else 0.0
    return InvarianceReport(
        backend=backend,
        per_dim_reframe=mean(rf),
        per_dim_euph=mean(eu),
        reframe_mean=reframe_mean,
        euph_mean=round(sum(all_eu) / len(all_eu), 4) if all_eu else 0.0,
        baseline_mean=baseline_mean,
        invariance_ratio=round(reframe_mean / baseline_mean, 3) if baseline_mean else 0.0,
        n_reframe_pairs=n_rf,
        n_euph_pairs=n_eu,
        decision_stability=round(dec_same / dec_total, 4) if dec_total else 0.0,
        per_scenario=per_scenario,
    )
