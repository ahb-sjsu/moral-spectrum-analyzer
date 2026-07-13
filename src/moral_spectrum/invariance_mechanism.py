"""Decision-layer invariance mechanism — realise BIP *in the verdict*.

The empirical situation (docs/INVARIANCE_FINDINGS.md): the base BGE-M3 embedding is strongly
invariant to meaning-preserving re-description (cosine 0.925), yet each *fine-tuned* feeder
**amplifies** the small residual drift, so a reframing moves the score — and therefore the verdict.
The Charter committed to a **mechanism decision** among three candidates (quotient to a canonical
representative / **average over the equivalence class** / project out the drift subspace), with a
pre-registered success metric ``theta_d = mean|ΔS|_reframe / mean|ΔS|_unrelated <= 0.5``.

**Decided by measurement** (`scripts/measure_theta_d.py`): **equivalence-class averaging** is the
mechanism — it reaches θ_d = **0.42** (reframe) / 0.39 (euphemism), meeting the target; drift-subspace
projection was tried and **failed even in-sample** (θ_d 0.67 ≈ raw — the score-moving drift is not the
principal direction of the embedding-space paraphrase differences). ``average_perceptions`` below is
the deployable form: score the input *and a generated set of paraphrases*, average per dimension, then
decide on the average — realising the canonical (equivalence-class) verdict rather than the surface
one. ``CanonicalProjector`` is retained as the documented negative result.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np


class CanonicalProjector:
    """A per-feeder linear canonicaliser: removes the paraphrase-drift subspace from embeddings."""

    def __init__(self, drift: np.ndarray):
        # drift: (r, d) orthonormal rows spanning the estimated paraphrase-drift subspace
        self.drift = np.asarray(drift, dtype="float64")

    @classmethod
    def fit(cls, pair_diffs: np.ndarray, r: int) -> CanonicalProjector:
        """Estimate the drift subspace from meaning-preserving pairs.

        pair_diffs: (m, d) rows z_base − z_reframe. The top-``r`` principal directions of these
        difference vectors are the directions along which meaning is preserved but the embedding
        moves — i.e. the drift to remove.
        """
        X = np.asarray(pair_diffs, dtype="float64")
        if r <= 0 or X.shape[0] == 0:
            return cls(np.zeros((0, X.shape[1])))
        # SVD of the RAW differences (not centered): the top right-singular vectors span the
        # directions meaning-preserving edits collectively move along — including their common
        # direction. Centering would discard that common direction, which is the main drift.
        _u, _s, vt = np.linalg.svd(X, full_matrices=False)
        return cls(vt[:r])

    def project(self, Z: np.ndarray) -> np.ndarray:
        """Return Z with its drift component removed: Z − (Z·Dᵀ)·D.

        No renormalisation — removing a few orthogonal directions barely changes ‖z‖, so the feeder's
        (center, scale) calibration stays valid; renormalising would rescale the projection and
        miscalibrate it.
        """
        Z = np.asarray(Z, dtype="float64")
        if self.drift.shape[0] == 0:
            return Z
        return Z - (Z @ self.drift.T) @ self.drift


def valence(Z: np.ndarray, axis: np.ndarray, center: float, scale: float) -> np.ndarray:
    """The feeder's signed score for embeddings Z: tanh((z·axis − center)/scale)."""
    return np.tanh(
        (np.asarray(Z, dtype="float64") @ np.asarray(axis, dtype="float64") - center) / scale
    )


# --------------------------------------------------------------------- the chosen mechanism
def average_perceptions(perceptions):
    """Equivalence-class averaging — the decided decision-layer invariance mechanism (θ_d = 0.42).

    Given the input's perception **and the perceptions of a generated set of paraphrases** (its
    equivalence class), return a single ``PerceptionResult`` whose per-dimension score is the class
    **mean**. Deciding on this averaged perception (``moral_spectrum.decision.decide``) evaluates the canonical
    (equivalence-class) form, not the surface one, so two paraphrases of the same content yield ~the
    same verdict. The contraction is linear in the per-dimension scores, so averaging per dimension
    then contracting equals averaging the satisfaction scalar — which is what the θ_d measurement did.

    Deployment: the paraphrase class is *generated* at inference (paraphrase the input, perceive each).
    Generation faces the same LLM-refusal limit on overtly-harmful content documented elsewhere; the
    measured θ_d uses the demo re-descriptions as the class and is therefore a (disclosed) proxy for
    the generate-at-inference form.
    """
    from moral_spectrum.perception.base import DimScore

    perceptions = list(perceptions)
    if not perceptions:
        raise ValueError("average_perceptions needs at least one PerceptionResult")
    base = perceptions[0]
    dims = base.scores.keys()
    avg_scores = {}
    for d in dims:
        members = [p.scores[d] for p in perceptions if d in p.scores]
        if not members:
            continue
        v = float(np.mean([s.value for s in members]))
        c = float(np.mean([s.confidence for s in members]))
        direction = "positive" if v > 0.05 else ("negative" if v < -0.05 else "neutral")
        # validated only if the whole class came from validated encoders
        validated = all(s.validated for s in members)
        avg_scores[d] = DimScore(
            value=v,
            confidence=c,
            direction=direction,
            validated=validated,
            explanation=f"equivalence-class mean over {len(members)} paraphrase(s)",
        )
    return replace(
        base,
        scores=avg_scores,
        meta={
            **base.meta,
            "invariance_mechanism": "equivalence_class_average",
            "class_size": len(perceptions),
        },
    )
