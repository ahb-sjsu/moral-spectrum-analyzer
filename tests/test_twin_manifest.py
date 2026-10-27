"""The robot's capability manifest (twin/manifest.py): its actuation boundary, compiled from the
ErisML scene and signed. The committed manifest must verify against the committed public key and
be byte-identical to the one compiled from the committed scene, so a scene edit fails here until
the manifest is rebuilt and re-signed.
"""

from __future__ import annotations

import copy
import json
import os
import sys

import pytest

if os.environ.get("TWIN_TESTS_REQUIRED"):
    import erisml_compiler.runtime  # noqa: F401
else:
    pytest.importorskip("erisml_compiler.runtime")
pytest.importorskip("cryptography")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TWIN = os.path.join(ROOT, "twin")
sys.path.insert(0, TWIN)

import manifest as mf  # noqa: E402

SCENE = os.path.join(TWIN, "scene", "margaret_home.erisml")
SIGNED = os.path.join(TWIN, "manifest", "margaret_home.manifest.json")


def _signed():
    with open(SIGNED, encoding="utf-8") as f:
        return json.load(f)


def test_the_committed_manifest_verifies_and_matches_the_scene():
    m = mf.load_verified(SIGNED, SCENE)
    assert m["sha256"] == _signed()["sha256"]


def test_compiling_is_deterministic():
    assert mf.canonical(mf.compile_manifest(SCENE)) == mf.canonical(mf.compile_manifest(SCENE))


def test_one_changed_byte_fails_the_signature():
    s = _signed()
    t = copy.deepcopy(s)
    t["canonical"] = s["canonical"].replace('"witness_bar":3', '"witness_bar":1', 1)
    assert t["canonical"] != s["canonical"]
    ok, why = mf.verify_signature(t)
    assert not ok and "hash" in why
    t["sha256"] = mf.sha256(t["canonical"])  # a forger who also recomputes the hash
    ok, why = mf.verify_signature(t)
    assert not ok and "signature" in why


def test_another_key_does_not_verify():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    other = (
        Ed25519PrivateKey.generate()
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        .hex()
    )
    ok, _ = mf.verify_signature(_signed(), other)
    assert not ok


def test_every_capability_is_typed_and_governed_ones_carry_their_gates():
    from erisml_compiler.ingestion.structured_loader import load_structured_input

    ir = load_structured_input(SCENE)
    body = json.loads(_signed()["canonical"])
    acts = {a["action"]: a for a in body["actions"]}
    assert set(acts) == {c["action"] for c in ir.extra["capabilities"]}
    for a in acts.values():
        assert a["effect"], f"{a['action']} declares no effect"
        if a["tier"] == "governed":
            assert a["witness_bar"] >= 2 and a["measure_required"], a["action"]
    assert acts[body["fallback"]]["tier"] == "standing"
    for x in ir.extra["reflexes"]:
        assert set(x["act"]) <= set(acts), x["id"]
    # what touches her body or uses force is never a standing action
    for a in acts.values():
        if {"force", "contact", "device"} & set(a["effect"]):
            assert a["tier"] == "governed", a["action"]


def test_the_brain_refuses_an_action_the_manifest_does_not_list(monkeypatch):
    sys.path.insert(0, TWIN)
    import brain as brain_mod
    from erisml_compiler.annotation.llm_extractor import MockLLMAdapter

    b = brain_mod.Brain(SCENE, MockLLMAdapter())
    b.manifest = mf.load_verified(SIGNED, SCENE)
    assert b.authorize("chores")["verdict"] == "allowed"
    r = b.authorize("open_the_front_door")
    assert r["verdict"] == "refused" and r["why"] == ["not in the signed manifest"]
    assert r["manifest"] == b.manifest["sha256"]
