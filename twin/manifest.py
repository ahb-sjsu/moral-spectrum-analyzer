#!/usr/bin/env python3
"""The robot's capability manifest: its actuation boundary, compiled from the ErisML scene.

Every action the robot can take is a typed entry derived from the scene and nothing else: its
declared effect, its tier (standing, or governed by the authority gate with its witness bar), the
norms that permit, oblige or prohibit it with their conditions, the refusals of Margaret's that
cover it, its DEME ethics profile and the reflexes that may take it, plus the scene's fallback.
The manifest is canonical JSON, identified by its SHA-256 and signed with Ed25519. The brain
refuses to start unless the signature verifies and the manifest compiled from the scene it loaded
is byte-identical; every decision and act-time check carries the manifest hash; the game executes
only the manifest's actions, against a hash pinned into its build.

  python twin/manifest.py keygen  --key KEY            # once, outside the repository
  python twin/manifest.py build   --scene SCENE --key KEY --out MANIFEST
  python twin/manifest.py verify  --scene SCENE --manifest MANIFEST
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

SCHEMA = "erisml-twin-manifest/1"
HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC_KEY = os.path.join(HERE, "manifest", "manifest_ed25519.pub")   # hex, committed


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compile_manifest(scene_path: str) -> dict:
    """The manifest body for one scene: deterministic, no timestamps."""
    import erisml_compiler
    from erisml_compiler.ingestion.structured_loader import load_structured_input

    ir = load_structured_input(scene_path)
    ex = ir.extra or {}
    agent = ex.get("agent") or "robot"
    refusals = ex.get("refusals") or {}
    ethics = ex.get("capability_ethics") or {}
    reflexes = ex.get("reflexes") or []

    def norms(action: str, modality: str) -> list[dict]:
        return sorted(({"id": n.id, "tier": n.priority_tier, "defeasible": bool(n.defeasible), "when": list(n.conditions or [])}
                       for n in ir.norms if n.action == action and n.modality == modality and n.actor == agent),
                      key=lambda e: e["id"])

    def refused_by(action: str) -> list[dict]:
        out = []
        for key, v in sorted(refusals.items()):
            covers, not_during = (v, []) if isinstance(v, list) else (v.get("covers", []), v.get("not_during", []))
            if action in covers:
                out.append({"refusal": key, "not_during": list(not_during)})
        return out

    actions = []
    for c in ex.get("capabilities", []):
        a = c["action"]
        governed = bool(c.get("elevated") or c.get("governed"))
        actions.append({
            "action": a,
            "effect": list(c.get("effect") or []),
            "tier": "governed" if governed else "standing",
            "elevated": bool(c.get("elevated")),
            "witness_bar": max(2, int(c.get("witness_bar", 2))) if governed else 0,
            "measure_required": governed and bool(ex.get("emergency_measures")),
            "permitted_when": norms(a, "permission"),
            "obliged_when": norms(a, "obligation"),
            "prohibited_when": norms(a, "prohibition"),
            "refused_by": refused_by(a),
            "ethics": ethics.get(a, {}),
            "reflexes": sorted(x["id"] for x in reflexes if a in x.get("act", [])),
        })
    with open(scene_path, "rb") as f:   # line endings normalized: a Windows checkout may hold CRLF
        scene_sha = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    return {
        "schema": SCHEMA,
        "scene": os.path.basename(scene_path),
        "scene_sha256": scene_sha,
        "compiler": getattr(erisml_compiler, "__version__", "unknown"),
        "agent": agent,
        "fallback": ex.get("default_action"),
        "emergency_kinds": sorted((ex.get("emergency_measures") or {}).keys()),
        "actions": sorted(actions, key=lambda e: e["action"]),
    }


def sign(body: dict, key_path: str) -> dict:
    from cryptography.hazmat.primitives import serialization

    with open(key_path, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    text = canonical(body)
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    return {"canonical": text, "sha256": sha256(text), "signature": key.sign(text.encode("utf-8")).hex(), "public_key": pub}


def verify_signature(signed: dict, public_key_hex: str | None = None) -> tuple[bool, str]:
    """(ok, why): the signature over the canonical text, by the committed public key."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if public_key_hex is None:
        if not os.path.exists(PUBLIC_KEY):
            return False, f"no committed public key at {PUBLIC_KEY}"
        public_key_hex = open(PUBLIC_KEY, encoding="utf-8").read().strip()
    text = signed.get("canonical", "")
    if sha256(text) != signed.get("sha256"):
        return False, "the canonical text does not match its hash"
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(bytes.fromhex(signed.get("signature", "")), text.encode("utf-8"))
    except (InvalidSignature, ValueError):
        return False, "the signature does not verify against the committed public key"
    return True, "signature verified"


def load_verified(manifest_path: str, scene_path: str, public_key_hex: str | None = None) -> dict:
    """The manifest the brain may run under, or a RuntimeError: the signature must verify and the
    manifest compiled now from the scene must be identical to the signed one."""
    with open(manifest_path, encoding="utf-8") as f:
        signed = json.load(f)
    ok, why = verify_signature(signed, public_key_hex)
    if not ok:
        raise RuntimeError(f"manifest {manifest_path}: {why}")
    if canonical(compile_manifest(scene_path)) != signed["canonical"]:
        raise RuntimeError(f"manifest {manifest_path} was not compiled from the scene loaded ({scene_path}); rebuild and re-sign it")
    body = json.loads(signed["canonical"])
    return {"sha256": signed["sha256"], "body": body, "signed": signed,
            "actions": {e["action"]: e for e in body["actions"]}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keygen")
    k.add_argument("--key", required=True)
    b = sub.add_parser("build")
    b.add_argument("--scene", required=True)
    b.add_argument("--key", required=True)
    b.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--scene", required=True)
    v.add_argument("--manifest", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "keygen":
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        if os.path.exists(a.key):
            print(f"{a.key} exists; not overwriting", file=sys.stderr)
            return 1
        key = Ed25519PrivateKey.generate()
        fd = os.open(a.key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        print(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex())
        return 0
    if a.cmd == "build":
        signed = sign(compile_manifest(a.scene), a.key)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(signed, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"{a.out}: {len(json.loads(signed['canonical'])['actions'])} actions, sha256 {signed['sha256']}")
        return 0
    m = load_verified(a.manifest, a.scene)
    print(f"verified: {len(m['actions'])} actions, sha256 {m['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
