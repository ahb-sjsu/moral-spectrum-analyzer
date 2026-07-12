"""Hash-chained DecisionProof — the audit artifact carrying validation provenance.

Every moderation decision emits a `DecisionProof`: a SHA-256 over the exact inputs that produced
it (source text, the DEME-9 moral vector, the per-dimension feeder validation records, the decision,
and the tensor hash), chained to the previous proof. This is what makes a decision *auditable* —
anyone can re-verify the chain and see which validated (or unvalidated) encoder produced each
number. It is the self-contained seed of the Phase-4.5 audit-verification UI.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

GENESIS = "0" * 64


def _sha256_json(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class DecisionProof:
    """A tamper-evident record binding a decision to the exact inputs that produced it."""

    source_text_sha256: str
    perception_backend: str
    all_validated: bool
    moral_vector: list[float]  # DEME-9 signed values, canonical k-axis order
    validation: list[dict]  # per-dimension feeder validation records
    decision: dict  # ModerationDecision.as_dict()
    tensor_sha256: str
    prev_hash: str = GENESIS
    proof_hash: str = ""
    # Present only for decisions made under the invariance mechanism: the generated equivalence class
    # (hashes + size + refused flag) that the perception was averaged over. Records the
    # canonicalisation step so it is not a silent, unauditable transform (docs/INVARIANCE_FINDINGS.md).
    equivalence_class: dict | None = None

    # Fields that are part of the signed payload (everything except proof_hash itself).
    _PAYLOAD = (
        "source_text_sha256",
        "perception_backend",
        "all_validated",
        "moral_vector",
        "validation",
        "decision",
        "tensor_sha256",
        "prev_hash",
    )

    def _payload(self) -> dict:
        payload = {k: getattr(self, k) for k in self._PAYLOAD}
        # Included only when set, so non-invariance proofs keep their exact prior hash.
        if self.equivalence_class is not None:
            payload["equivalence_class"] = self.equivalence_class
        return payload

    def compute_hash(self) -> str:
        return _sha256_json(self._payload())

    def finalize(self) -> "DecisionProof":
        self.proof_hash = self.compute_hash()
        return self

    def verify(self) -> bool:
        """True iff the recomputed hash matches — i.e. nothing in the payload was tampered with."""
        return bool(self.proof_hash) and self.proof_hash == self.compute_hash()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProofChain:
    """An append-only chain of DecisionProofs. Each proof's prev_hash = the prior proof_hash."""

    proofs: list[DecisionProof] = field(default_factory=list)

    @property
    def head(self) -> str:
        return self.proofs[-1].proof_hash if self.proofs else GENESIS

    def append(self, proof: DecisionProof) -> DecisionProof:
        proof.prev_hash = self.head
        proof.finalize()
        self.proofs.append(proof)
        return proof

    def verify_chain(self) -> bool:
        """True iff every proof verifies AND the prev_hash links are intact and ordered."""
        prev = GENESIS
        for p in self.proofs:
            if p.prev_hash != prev or not p.verify():
                return False
            prev = p.proof_hash
        return True
