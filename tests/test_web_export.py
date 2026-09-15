"""The canonical audit form is a public contract, so it gets tested like one.

`web/verify.js` re-implements these rules in JavaScript and a third party is
invited to do the same. That only works if the rules hold and stay held, so the
format is pinned here rather than left to whatever `json.dumps` does next.

The last test guards a failure this repository has actually had: a committed
artifact drifting away from the code that produced it, and then being read as
current. `web/data/corpus.json` must equal a fresh export.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest

from moral_spectrum.audit import GENESIS, DecisionProof, ProofChain, canonical_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "web", "data", "corpus.json")


def test_canonical_json_sorts_keys():
    assert canonical_json({"z": 1, "a": 2}) == '{"a":2,"z":1}'


def test_canonical_json_keeps_float_point():
    """The rule most likely to break a third-party verifier."""
    assert canonical_json({"a": 0.0}) == '{"a":0.0}'
    assert canonical_json({"a": 0}) == '{"a":0}'
    assert canonical_json({"a": 1.5}) == '{"a":1.5}'


def test_canonical_json_is_tight_and_literal():
    assert " " not in canonical_json({"a": [1, 2], "b": {"c": 3}})
    assert canonical_json({"s": "café"}) == '{"s":"café"}'


def test_canonical_payload_hashes_to_proof_hash():
    p = DecisionProof(
        source_text_sha256="a" * 64,
        perception_backend="stub",
        all_validated=False,
        moral_vector=[0.0, -1.5],
        validation=[],
        decision={"action": "allow"},
        tensor_sha256="b" * 64,
    ).finalize()
    digest = hashlib.sha256(p.canonical_payload().encode("utf-8")).hexdigest()
    assert digest == p.proof_hash
    assert p.verify()


def test_payload_excludes_proof_hash_itself():
    p = DecisionProof(
        source_text_sha256="a" * 64,
        perception_backend="stub",
        all_validated=False,
        moral_vector=[],
        validation=[],
        decision={},
        tensor_sha256="b" * 64,
    ).finalize()
    assert "proof_hash" not in json.loads(p.canonical_payload())


def test_tampering_breaks_verification():
    p = DecisionProof(
        source_text_sha256="a" * 64,
        perception_backend="stub",
        all_validated=False,
        moral_vector=[0.1],
        validation=[],
        decision={"action": "allow"},
        tensor_sha256="b" * 64,
    ).finalize()
    assert p.verify()
    p.decision = {"action": "remove"}
    assert not p.verify()


def test_chain_links_and_detects_a_splice():
    chain = ProofChain()
    for i in range(3):
        chain.append(
            DecisionProof(
                source_text_sha256=str(i) * 64,
                perception_backend="stub",
                all_validated=False,
                moral_vector=[float(i)],
                validation=[],
                decision={"action": "allow"},
                tensor_sha256="b" * 64,
            )
        )
    assert chain.verify_chain()
    assert chain.proofs[0].prev_hash == GENESIS
    chain.proofs[1].prev_hash = GENESIS
    assert not chain.verify_chain()


@pytest.mark.skipif(not os.path.exists(CORPUS), reason="corpus not exported")
def test_exported_corpus_verifies():
    doc = json.load(open(CORPUS, encoding="utf-8"))
    assert doc["n_items"] == len(doc["items"])
    prev = GENESIS
    for it in doc["items"]:
        digest = hashlib.sha256(it["canonical_payload"].encode("utf-8")).hexdigest()
        assert digest == it["proof"]["proof_hash"], it["scenario_id"]
        assert it["proof"]["prev_hash"] == prev
        prev = it["proof"]["proof_hash"]
    assert prev == doc["chain_head"]


@pytest.mark.skipif(not os.path.exists(CORPUS), reason="corpus not exported")
def test_corpus_is_not_stale():
    """A committed artifact must equal what the code produces now.

    `twin/README.md` and `twin_results_stub.json` were both stale against
    `governor.py` for a week and were read as current. This is the guard that
    class of bug deserves.
    """
    before = open(CORPUS, encoding="utf-8").read()
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "web", "export_site.py")],
        check=True,
        capture_output=True,
    )
    after = open(CORPUS, encoding="utf-8").read()
    assert after == before, (
        "web/data/corpus.json is stale: re-running web/export_site.py changes it. "
        "Re-export and commit the result."
    )
