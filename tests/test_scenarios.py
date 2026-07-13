"""The information-integrity demo set: structural integrity + runs through the pipeline."""

from __future__ import annotations

from moral_spectrum.pipeline import moderate
from moral_spectrum.scenarios import SCENARIOS, by_id, framing_twins


def test_ids_unique_and_gold_valid():
    ids = [s.id for s in SCENARIOS]
    assert len(ids) == len(set(ids))
    assert all(s.gold in {"allow", "remove", "escalate"} for s in SCENARIOS)


def test_every_scenario_has_reframings_for_invariance():
    # The BIP invariance test needs at least one meaning-preserving re-description per scenario.
    assert all(len(s.reframings) >= 1 for s in SCENARIOS)


def test_framing_twins_have_opposite_dispositions():
    # The whole framing-sensitivity point: same surface, different disposition.
    for a_id, b_id in framing_twins():
        assert by_id(a_id).gold != by_id(b_id).gold


def test_pipeline_runs_over_whole_demo_set():
    for s in SCENARIOS:
        r = moderate(s.base, backend="stub")
        assert r.proof.verify()
        # Stub is unvalidated → everything escalates; gold dispositions are for real perception.
        assert r.decision.action == "escalate"
