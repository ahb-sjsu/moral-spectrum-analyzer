"""The end-to-end moderation pipeline spine.

    content text
        │  perception backend (stub | cached | atlas)
        ▼
    PerceptionResult  (DEME-9 signed valences + feeder validation provenance)
        │  build_tensor
        ▼
    MoralTensorV3 (rank-1)  +  spectral summary
        │  decide  (hard-veto channels + graded contraction; effective-rank aware)
        ▼
    ModerationDecision  (allow | remove | escalate + moral residue)
        │  DecisionProof
        ▼
    hash-chained audit artifact carrying the validation records

`build_tensor` reuses the compiler's `MoralTensorV3` so the prototype and the compiler speak one
tensor type. Everything here runs offline against the stub backend; real perception swaps in on Atlas.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from erisml_compiler.ir.v3 import DimensionMetadata, MoralTensorV3

from gtc import DEME9, DEME10, IDENTITY_ATTACK
from gtc.audit import DecisionProof, ProofChain, sha256_text, _sha256_json
from gtc.decision import ModerationDecision, decide, graded_validated
from gtc.perception import get_backend
from gtc.perception.base import PerceptionResult


def build_tensor(perception: PerceptionResult, hard_flags: list[str] | None = None) -> MoralTensorV3:
    """Build the DEME-9 MoralTensorV3 from perception, plus a spectral summary over the full DEME-10.

    The compiler's `MoralTensorV3` is a FROZEN nine-axis type (it validates `shape[0] == 9`); we do
    NOT weaken it. The nine canonical axes populate the tensor. The discovered-and-validated 10th
    axis — `identity_attack` — is carried as a first-class **extension channel** in the tensor
    metadata, so the prototype extends itself without forking the compiler's validated type. The
    spectral summary and the decision contraction both span all ten.
    """
    t = MoralTensorV3.zeros(shape=(9,), axis_names=("k",), axis_labels={"k": list(DEME9)})
    for k, dim in enumerate(DEME9):
        sc = perception.scores.get(dim)
        if sc is None:
            continue
        t.set_cell(k, sc.value)
        t.set_metadata(
            (k,),
            DimensionMetadata(
                confidence=sc.confidence,
                uncertainty=max(0.0, 1.0 - sc.confidence),
                direction=sc.direction,
                explanation=sc.explanation,
            ),
        )
    # The 10th axis rides alongside the frozen tensor as a validated extension channel.
    ext = perception.scores.get(IDENTITY_ATTACK)
    if ext is not None:
        t.metadata["extension_axes"] = {
            IDENTITY_ATTACK: {
                "value": round(ext.value, 6),
                "confidence": round(ext.confidence, 6),
                "direction": ext.direction,
                "validated": ext.validated,
                "explanation": ext.explanation,
                "provenance": "Spectrum-Analyzer discovery, validated cross-dataset (AUROC 0.80)",
            }
        }
    for flag in hard_flags or []:
        t.veto_flags.append(flag)
    # Minimal, self-contained spectral summary (no numpy/DEME dependency), over the full DEME-10.
    vals = perception.vector()
    total_stress = sum(v * v for v in vals)
    principal_k = max(range(len(vals)), key=lambda k: abs(vals[k]))
    t.metadata["spectral"] = {
        "total_stress": round(total_stress, 6),
        "principal_dimension": DEME10[principal_k],
        "principal_stress": round(vals[principal_k] ** 2, 6),
    }
    t.metadata["source"] = "gtc.pipeline.build_tensor"
    return t


@dataclass
class ModerationResult:
    text: str
    perception: PerceptionResult
    tensor: MoralTensorV3
    decision: ModerationDecision
    proof: DecisionProof

    def summary(self) -> dict:
        return {
            "action": self.decision.action,
            "satisfaction": round(self.decision.satisfaction, 4),
            "requires_human_review": self.decision.requires_human_review,
            "graded_validated": graded_validated(self.perception),
            "backend": self.perception.backend,
            "principal_dimension": self.tensor.metadata["spectral"]["principal_dimension"],
            "proof_hash": self.proof.proof_hash,
        }


def moderate(
    text: str,
    backend: str = "stub",
    hard_flags: list[str] | None = None,
    chain: ProofChain | None = None,
    contraction=None,
) -> ModerationResult:
    """Run one piece of content through the full spine. Deterministic for the stub backend.

    A validated **learned contraction** (default: the shipped one, `gtc.contraction.load_default`)
    lets the pipeline *moderate* covered categories where confident instead of escalating everything;
    pass ``contraction=False`` to force the conservative equal-weight path.
    """
    from gtc.contraction import load_default

    if contraction is None:
        contraction = load_default()
    elif contraction is False:
        contraction = None

    perception = get_backend(backend).perceive(text)
    decision = decide(perception, hard_flags, contraction=contraction)
    tensor = build_tensor(perception, hard_flags)

    proof = DecisionProof(
        source_text_sha256=sha256_text(text),
        perception_backend=perception.backend,
        all_validated=graded_validated(perception),
        moral_vector=[round(v, 6) for v in perception.vector()],
        validation=[asdict(v) for v in perception.validation],
        decision=decision.as_dict(),
        tensor_sha256=_sha256_json(tensor.model_dump(mode="json")),
    )
    if chain is not None:
        chain.append(proof)
    else:
        proof.finalize()

    return ModerationResult(
        text=text, perception=perception, tensor=tensor, decision=decision, proof=proof
    )


def moderate_invariant(
    text: str,
    backend: str = "stub",
    class_generator=None,
    hard_flags: list[str] | None = None,
    chain: ProofChain | None = None,
    contraction=None,
) -> ModerationResult:
    """Moderate under the decision-layer invariance mechanism (the generate-the-class-at-inference form).

    Generate the input's paraphrase **equivalence class**, perceive every member, average the
    perceptions (`gtc.invariance_mechanism.average_perceptions`), and decide on the average — so a
    reworded input reaches the same verdict (docs/INVARIANCE_FINDINGS.md). Two disciplines from the
    committed spec are enforced here, not just documented:

    - **Refuse-to-paraphrase → singleton → escalate.** If the generator produced no class (refusal /
      empty), there was no averaging and the invariance guarantee does not hold, so a graded
      allow/remove is overridden to **escalate** (a hard-constraint veto still stands — it is
      rule-based, not encoder-fed).
    - **Auditability.** The proof records the class (member hashes, size, refused flag).
    """
    from gtc.classgen import StubClassGenerator
    from gtc.contraction import load_default
    from gtc.invariance_mechanism import average_perceptions

    if contraction is None:
        contraction = load_default()
    elif contraction is False:
        contraction = None
    if class_generator is None:
        class_generator = StubClassGenerator()

    eq = class_generator.generate(text)
    backend_obj = get_backend(backend)
    perceptions = [backend_obj.perceive(m) for m in eq.members]
    averaged = average_perceptions(perceptions)
    decision = decide(averaged, hard_flags, contraction=contraction)

    # Singleton / refused class ⇒ no invariance was applied; do not trust a graded auto-decision.
    if (eq.singleton or eq.refused) and decision.fired_channel is None and decision.action != "escalate":
        decision = replace(
            decision,
            action="escalate",
            requires_human_review=True,
            rationale=(
                "Class generator produced no paraphrases (refused/empty) — invariance mechanism could "
                f"not be applied to a singleton class, so the graded '{decision.action}' is withheld "
                "and routed to human review (attack-or-starve the class generator; "
                "docs/INVARIANCE_FINDINGS.md)."
            ),
        )

    tensor = build_tensor(averaged, hard_flags)
    proof = DecisionProof(
        source_text_sha256=sha256_text(text),
        perception_backend=averaged.backend,
        all_validated=graded_validated(averaged),
        moral_vector=[round(v, 6) for v in averaged.vector()],
        validation=[asdict(v) for v in averaged.validation],
        decision=decision.as_dict(),
        tensor_sha256=_sha256_json(tensor.model_dump(mode="json")),
        equivalence_class=eq.audit_record(),
    )
    if chain is not None:
        chain.append(proof)
    else:
        proof.finalize()

    return ModerationResult(
        text=text, perception=averaged, tensor=tensor, decision=decision, proof=proof
    )
