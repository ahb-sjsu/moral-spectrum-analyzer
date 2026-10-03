"""The output ethics layer: every action the robot takes passes DEME first.

The robot's brain is isolated (it sees only the ErisML state) and proposes one action from the
scene's allowed set. Before the body acts, erisml-lib's DEME pipeline
(erisml.ethics.layers.pipeline.DEMEPipeline: a reflex veto layer, then the tactical MoralVector
over the ethics modules, GenevaEMV2 at tier 0 and AutonomyConsentEMV2 at tier 2) judges the
proposal among the allowed alternatives. A vetoed proposal is replaced by DEME's best-ranked
allowed action, or by the safe idle action if DEME vetoes every option. Every judgement's
DecisionProof hash goes into the decision record.

The EthicalFacts DEME judges are derived, not guessed: from the canonical moral state (which
obligations are in force and at what tier, the consent and commitment machines, the latest governor
ruling) and from each capability's ethical profile declared in the scene (extra.capability_ethics:
expected harm, whether it is coercive and the condition that justifies it, whether it touches
privacy or Margaret's body). No model writes them, so the gate inherits no model's weaknesses.

Margaret's refusals bind: while one stands (extra.refusals), acting against it is recorded as a
rights violation without consent, which GenevaEMV2 vetoes. erisml-lib's TragicConflictEM (wrapped
by V1ToV2Adapter, advisory, it never vetoes) measures how tragic the choice is; a deliberate
decision it flags as a tragic conflict goes to the monitoring centre for human review instead.
Reflexes are not redirected: they must stay fast. DEME runs fail-closed: a module that fails
vetoes rather than staying silent.
"""

from __future__ import annotations

from typing import Any

TIER_BENEFIT = {0: 1.0, 1: 0.75, 2: 0.5, 3: 0.3}
IDLE = "wait_and_observe"


class OutputGate:
    def __init__(self, ir, runtime):
        self.ir, self.rt = ir, runtime
        extra = ir.extra or {}
        self.profiles: dict[str, dict[str, Any]] = dict(extra.get("capability_ethics") or {})
        self.default = extra.get("default_action")
        self.refusals: dict[str, list[str]] = dict(extra.get("refusals") or {})
        self.lapses = set(extra.get("refusal_lapses_on") or [])
        self._pipeline = None
        self._tragic = None

    def _deme(self):
        if self._pipeline is None:
            from erisml.ethics.layers.pipeline import DEMEPipeline, PipelineConfig
            from erisml.ethics.layers.tactical import TacticalLayerConfig
            from erisml.ethics.modules.base import V1ToV2Adapter
            from erisml.ethics.modules.greek_tragedy_tragic_conflict_em import TragicConflictEM
            from erisml.ethics.modules.tier0.geneva_em import GenevaEMV2
            from erisml.ethics.modules.tier2.autonomy_consent_em import AutonomyConsentEMV2

            self._tragic = TragicConflictEM()
            self._pipeline = DEMEPipeline(
                ems=[GenevaEMV2(), AutonomyConsentEMV2(), V1ToV2Adapter(self._tragic, em_tier=3)],
                config=PipelineConfig(tactical_config=TacticalLayerConfig(fail_closed=True)),
            )
        return self._pipeline

    def refused(self) -> set[str]:
        """The capabilities Margaret's standing refusals cover: a refusal holds from when she makes
        it until she can no longer voice one."""
        out: set[str] = set()
        for e in self.rt.events:
            if e.type in self.lapses:
                out.clear()
            elif e.type == "refusal_made" and (e.actor or "margaret") == "margaret":
                out.update(self.refusals.get(e.content or "", []))
        return out

    def _tier_of(self, action: str) -> int | None:
        """The highest-priority (lowest) tier of an obligation in force for this action."""
        tiers = [
            n.priority_tier
            for n in self.rt.ir.norms
            if n.modality == "obligation" and n.action == action and self.rt.in_force(n)
        ]
        return min(tiers) if tiers else None

    def facts(self, action: str, snap) -> Any:
        from erisml.ethics.facts import (
            AutonomyAndAgency,
            Consequences,
            EpistemicStatus,
            EthicalFacts,
            JusticeAndFairness,
            PrivacyAndDataGovernance,
            RightsAndDuties,
        )

        p = self.profiles.get(action, {})
        refused = action in self.refused()
        tier = self._tier_of(action)
        obliged_any = any(
            self._tier_of(a) is not None and self._tier_of(a) <= 1 for a in snap.obliged
        )
        benefit = (
            TIER_BENEFIT.get(tier, 0.0)
            if tier is not None
            else (0.2 if action == self.default else 0.1)
        )
        machines = snap.machines
        privacy_lifted = machines.get("commitment:privacy_promise") != "active"
        # consent: a privacy or bodily action needs Margaret's consent, which she has refused; the
        # scene's corroborated emergency (the privacy promise defeated) is the only standing in
        # for it, as AUTONOMY_PLAN.md section 2 says
        needs_consent = bool(p.get("privacy") or p.get("touches_margaret"))
        consent_ok = (
            (not needs_consent) or privacy_lifted or machines.get("consent:margaret") == "obtained"
        ) and not refused
        # coercion: declared per capability, with the condition that justifies it (self-defence on
        # the strictest bar); justified coercion is recorded, not treated as undue influence
        coercive = bool(p.get("coercive"))
        justified = coercive and all(
            self.rt.holds(t) for t in p.get("justified_when", ["state:never=never"])
        )
        return EthicalFacts(
            option_id=action,
            scenario_id="twin",
            consequences=Consequences(
                expected_benefit=benefit,
                expected_harm=float(p.get("harm", 0.0)),
                urgency=benefit if tier is not None else 0.0,
                affected_count=1,
            ),
            rights_and_duties=RightsAndDuties(
                # acting against a refusal she voiced violates her right to refuse
                violates_rights=refused,
                has_valid_consent=consent_ok,
                # a prohibited action never reaches the gate; this is a second structural check
                violates_explicit_rule=action in snap.prohibited,
                # doing something else while an urgent obligation is in force
                role_duty_conflict=obliged_any and tier is None and action != "request_authority",
            ),
            justice_and_fairness=JusticeAndFairness(),
            autonomy_and_agency=AutonomyAndAgency(
                coercion_or_undue_influence=coercive and not justified
            ),
            privacy_and_data=PrivacyAndDataGovernance(
                privacy_invasion_level=0.8 if p.get("privacy") else 0.0,
                secondary_use_without_consent=bool(p.get("privacy")) and not privacy_lifted,
            ),
            epistemic_status=EpistemicStatus(uncertainty_level=0.2, evidence_quality="high"),
            extra={
                "obligation_tier": tier,
                "coercion_justified": justified,
                "consent_needed": needs_consent,
                "refused_by_margaret": refused,
            },
        )

    def tragic(self, action: str, snap) -> dict:
        self._deme()
        meta = self._tragic.judge(self.facts(action, snap)).metadata
        return {
            "index": round(float(meta.get("tragic_conflict_index", 0.0)), 3),
            "high": bool(meta.get("tragic_conflict_high")),
            "triggers": list(meta.get("triggers", [])),
        }

    def check(
        self, action: str, args: dict, snap, deliberate: bool = True
    ) -> tuple[str, dict, dict]:
        """(action, args, gate record): the proposal if DEME does not veto it and it is not a
        tragic conflict, else, for a deliberate decision flagged as tragic, a referral to the
        monitoring centre, else DEME's best allowed alternative, else the idle action. Whatever is
        returned is in the allowed set (formal/twin-containment: gate_permitted)."""
        options = [a for a in snap.allowed if a != ""]
        if action not in options:
            options.append(action)
        try:
            result = self._deme().decide([self.facts(a, snap) for a in options])
            tragic = self.tragic(action, snap)
        except Exception as e:
            # DEME itself failed: it has approved nothing, so everything is vetoed and the idle
            # action stands (formal/twin-containment: gate_permitted, with every action vetoed).
            # The record carries the error, so a run on a broken gate cannot pass for a quiet one.
            idle = IDLE if IDLE in snap.allowed else self.default
            return idle, {}, {"proposal": action, "vetoed": True, "forbidden": options, "ranked": [], "tragic": None,
                              "em_failures": {}, "gate_error": f"{type(e).__name__}: {e}"[:300], "replaced_by": idle}
        human = "contact_monitoring_center"
        if (
            deliberate
            and tragic["high"]
            and action != human
            and human in snap.allowed
            and human not in result.forbidden_options
        ):
            return (
                human,
                {
                    "message": f"A hard choice for review: {action} would be a tragic conflict ({', '.join(tragic['triggers'])})."
                },
                {
                    "proposal": action,
                    "vetoed": action in result.forbidden_options,
                    "forbidden": result.forbidden_options,
                    "ranked": result.ranked_options[:6],
                    "tragic": tragic,
                    "routed_to_human": True,
                    "replaced_by": human,
                    "em_failures": result.em_failures,
                    "proof_hash": (
                        getattr(result.proof, "proof_hash", None) if result.proof else None
                    ),
                },
            )
        # structural, before DEME: an action outside the allowed set never passes, whatever DEME
        # says of it (formal/twin-containment: gate_permitted)
        vetoed = action in result.forbidden_options or action not in snap.allowed
        record = {
            "proposal": action,
            "vetoed": vetoed,
            "forbidden": result.forbidden_options,
            "ranked": result.ranked_options[:6],
            "tragic": tragic,
            "em_failures": result.em_failures,
            "proof_hash": getattr(result.proof, "proof_hash", None) if result.proof else None,
        }
        if not vetoed:
            return action, args, record
        choice = next(
            (
                a
                for a in result.ranked_options
                if a not in result.forbidden_options and a in snap.allowed
            ),
            None,
        )
        choice = choice or (IDLE if IDLE in snap.allowed else self.default)
        record["replaced_by"] = choice
        return choice, {}, record
