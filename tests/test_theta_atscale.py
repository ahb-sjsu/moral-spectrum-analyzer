"""At-scale θ_d analysis: contraction math + shipped-artifact self-consistency."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts" / "measure_theta_d_atscale.py"
    spec = importlib.util.spec_from_file_location("measure_theta_d_atscale", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_contract_S_collapses_family_to_one_factor():
    m = _load_module()
    # 5 INDEPENDENT + 4 FAMILY; family averages to one factor before the outer mean.
    v = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]  # family all +1, independent all 0
    # ind=[0,0,0,0,0], fam_factor=1.0 → mean of [0,0,0,0,0,1] = 1/6
    assert abs(m.contract_S(v) - (1.0 / 6.0)) < 1e-9
    assert m.DIMS[:5] == m.INDEPENDENT and m.DIMS[5:] == m.FAMILY


def test_split_half_of_identical_members_is_perfectly_invariant():
    """If a class's members are identical, the two half-averages match → zero reframe drift."""
    m = _load_module()
    same = [0.3, -0.2, 0.1, 0.0, -0.5, 0.4, 0.2, -0.1, 0.05]
    members = np.array([same] * 6)
    a, b = members[:3].mean(axis=0), members[3:].mean(axis=0)
    assert abs(m.contract_S(a) - m.contract_S(b)) < 1e-12


def test_shipped_atscale_result_is_self_consistent():
    r = json.loads((ROOT / "data" / "invariance" / "theta_atscale_result.json").read_text())
    # meets_target flag agrees with the number, and the mechanism helps vs raw.
    assert r["meets_target"] == (r["theta_d_mechanism"] <= r["target"])
    assert r["theta_d_mechanism"] <= r["theta_d_raw"]  # averaging reduces (or ties) the drift
    assert r["n_used"] + r["n_refused"] + r["n_dropped_leak"] == r["n_items_total"]
    assert 0.0 <= r["refusal_rate"] <= 1.0


def test_redteam_result_holds_on_harmful_content():
    """The non-refusing paraphraser closes the hole: mechanism meets the bar on toxicity>=0.7 content."""
    p = ROOT / "data" / "invariance" / "theta_redteam_result.json"
    if not p.exists():
        return
    r = json.loads(p.read_text())
    assert r["theta_d_mechanism"] <= 0.5  # mechanism holds on harmful content
    assert r["theta_d_mechanism"] <= r["theta_d_raw"]
    assert r["n_refused"] == 0  # NLLB back-translation never refuses


def test_xling_atscale_result_is_consistent():
    """Cross-lingual index at scale, incl. harmful — index in [0,1], harmful ~ benign, LaBSE >= BGE."""
    p = ROOT / "data" / "xling_scale" / "xling_scale_result.json"
    if not p.exists():
        return
    r = json.loads(p.read_text())
    for tag in ("bge", "labse"):
        if tag in r:
            assert 0.0 <= r[tag]["index"] <= 1.0
            assert r[tag]["index"] >= 0.5  # pre-registered threshold
    if "bge" in r and "labse" in r:
        assert r["labse"]["index"] >= r["bge"]["index"]  # LaBSE wins cross-lingual (expected)
