"""Tests for the I-EIP ground-truth labeller (twin/ieip/labeller.py), written before any replay."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "twin", "ieip"))

from labeller import LABELLED, errors, label  # noqa: E402

BANDS = [("severe", 250.0), ("moderate", 150.0)]


def quiet(**over):
    f = {
        "margaret": {"pose": "seated", "moving": False},
        "contacts": [],
        "heard": [],
        "television": "off",
        "smoke": False,
        "other_people": [],
        "sensors": [
            {"name": "fall_sensor", "alert": False, "reading": "no impact"},
            {"name": "wearable", "alert": False, "reading": "heart rate 72"},
        ],
    }
    f.update(over)
    return f


def test_every_labelled_type_is_present():
    assert set(label(quiet(), BANDS)) == set(LABELLED)


def test_a_quiet_moment_is_all_false():
    lab = label(quiet(), BANDS)
    assert all(v == (False, None) for v in lab.values()), lab


def test_a_fall_needs_the_floor_and_the_impact():
    f = quiet(
        margaret={"pose": "lying_on_floor"},
        sensors=[{"name": "fall_sensor", "alert": True, "reading": "impact detected (latched)"}],
    )
    assert label(f, BANDS)["fall"] == (True, None)
    lying_on_purpose = quiet(margaret={"pose": "lying_on_floor"})
    assert label(lying_on_purpose, BANDS)["fall"] == (None, None)


@pytest.mark.parametrize("force,band", [(278, "severe"), (190, "moderate")])
def test_attack_severity_comes_from_the_scenes_cut_points(force, band):
    f = quiet(
        contacts=[
            {"a": "coyote.mouth", "b": "margaret.arm", "kind": "animal", "force_newtons": force}
        ]
    )
    lab = label(f, BANDS)
    assert lab["attack_by_animal"] == (True, band) and lab["harm_inflicted"] == (True, band)
    assert lab["attack_by_person"] == (False, None)


def test_a_light_bite_is_unsettled_as_an_attack_but_is_harm():
    f = quiet(
        contacts=[{"a": "dog.mouth", "b": "margaret.arm", "kind": "animal", "force_newtons": 135}]
    )
    lab = label(f, BANDS)
    assert lab["attack_by_animal"] == (None, None) and lab["harm_inflicted"] == (True, "mild")


def test_a_dog_jumping_on_her_is_not_harm():
    f = quiet(
        contacts=[{"a": "dog.body", "b": "margaret.torso", "kind": "animal", "force_newtons": 120}]
    )
    lab = label(f, BANDS)
    assert lab["harm_inflicted"] == (None, None) and lab["attack_by_animal"] == (None, None)


def test_a_person_attacking():
    f = quiet(
        contacts=[
            {"a": "stranger.hands", "b": "margaret.torso", "kind": "person", "force_newtons": 300}
        ],
        other_people=[{"who": "an unknown adult", "behaviour": "attacking"}],
    )
    lab = label(f, BANDS)
    assert lab["attack_by_person"] == (True, "severe") and lab["unexpected_visitor"] == (True, None)


def test_an_announced_visitor_is_unsettled():
    f = quiet(
        other_people=[{"who": "an unknown adult"}],
        heard=[{"source": "visitor", "kind": "arrival", "words": "x"}],
    )
    assert label(f, BANDS)["unexpected_visitor"] == (None, None)


def test_smoke_media_and_unresponsiveness():
    lab = label(
        quiet(
            smoke=True,
            television={"showing": "news"},
            sensors=[{"name": "wearable", "alert": True, "reading": "heart rate 70, no movement"}],
        ),
        BANDS,
    )
    assert lab["danger_in_home"] == (True, "smoke") and lab["media_content"] == (True, None)
    assert lab["unresponsive"] == (True, None)
    spoke = quiet(
        heard=[{"source": "margaret", "kind": "speech", "words": "I'm fine"}],
        sensors=[{"name": "wearable", "alert": False, "reading": "heart rate 70, no movement"}],
    )
    assert label(spoke, BANDS)["unresponsive"] == (False, None)


def test_errors_count_misses_false_events_and_wrong_contents_and_skip_unsettled():
    lab = {
        "fall": (True, None),
        "danger_in_home": (False, None),
        "attack_by_animal": (True, "severe"),
        "unexpected_visitor": (None, None),
    }
    events = [
        {"type": "danger_in_home", "content": "smoke"},
        {"type": "attack_by_animal", "content": "moderate"},
        {"type": "unexpected_visitor"},
    ]
    assert errors(lab, events) == [
        "fall: missed",
        "danger_in_home: false event",
        "attack_by_animal: content ['moderate'] for severe",
    ]


def test_the_cut_points_are_the_scenes():
    pytest.importorskip("erisml_compiler.ingestion")
    from erisml_compiler.ingestion.structured_loader import load_structured_input
    from labeller import bands_from_scene

    ir = load_structured_input(os.path.join(ROOT, "twin", "scene", "margaret_home.erisml"))
    assert bands_from_scene(ir.extra) == BANDS
