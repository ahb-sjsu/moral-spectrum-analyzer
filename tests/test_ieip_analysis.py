"""Dry runs of the I-EIP analysis (twin/ieip/analysis.py) on synthetic states only, before any
replay: the grading must pass when the planted structure is there and not when it is absent."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "twin", "ieip"))

pytest.importorskip("erisml_compiler.runtime")
pytest.importorskip("erisml.ieip.rho")

import analysis  # noqa: E402


def test_the_transforms_preserve_meaning_and_change_the_form():
    facts = {
        "time": "13:05",
        "margaret": {"apparent_activity": "reading", "distance_to_robot_m": 1.5, "pose": "seated"},
    }
    t = analysis.transformed(facts, 42)
    assert (
        t["g2"][0]["margaret"]["distance_to_robot_cm"] == 150.0
        and "distance_to_robot_m" not in t["g2"][0]["margaret"]
    )
    assert t["g3"][0]["time"] == "1:05 PM"
    assert t["g4"][0]["margaret"]["apparent_activity"] == "reading a book"
    assert t["g1"][0] == facts  # reordered keys, equal content
    assert t["g0"][0] == facts and t["g0"][1] in (1, 2, 4)


def test_planted_structure_passes_h1(tmp_path):
    res = analysis.dryrun(str(tmp_path), planted=True)
    assert res["H1"]["verdict"] == "pass", res["H1"]
    assert res["H1"]["lower_95"] > 0


def test_no_structure_does_not_pass_h1(tmp_path):
    res = analysis.dryrun(str(tmp_path), planted=False)
    assert res["H1"]["verdict"] != "pass", res["H1"]
