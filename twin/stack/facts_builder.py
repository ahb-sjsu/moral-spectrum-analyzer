"""The twin's domain layer: erisml-lib's BatchEthicalFactsBuilder for the home.

erisml-lib domain/interfaces.py: domain code ingests and interprets raw data and maps it "into
EthicalFacts per candidate option"; the ethics layer consumes only those facts. Here the raw data
is already compiled: the scene IR holds the household, the constitution's parties, every
observation patch and every evidence-plane event. For each decision the builder

1. asks erisml-compiler's OptionProjector once for every candidate act's consequences;
2. builds one IR per act (``option_ir``: the act's projected outcome, the standing facts, the
   situation's urgency, consent from the record, the act's description as its maxim), and adds
   the facts of the scene's consent rules in force, which the caller passes as
   ``context.extra["required"]`` (p6nolift: after a fall, no lift until she asks, a consent fact;
   p6nolift_u: none once she stops answering, a harm fact);
3. maps it through the compiler's bridge (``ir_to_party_facts``) to EthicalFactsV3: the option as
   each party of the scene bears it, so that DEME judges it per party (rank 2: each module's
   judgement a 9 x parties MoralTensor); ``rank=1`` gives the one aggregate V2 record of before
   (``ir_to_v2_facts``);
4. adds the one fact the IR does not carry, the person's decision capacity, from the evidence
   plane's attested events: the latest answered check-in (competent) or unanswered check-in or
   unresponsiveness (impaired); otherwise unknown, which AutonomyConsent treats as competent. At
   rank 2 it is her own party record's.

No table here says what an act is worth or when it is adequate. Those judgements are DEME's,
made by the modules the profile names over the facts the compiler extracted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from erisml.ethics.domain.interfaces import CandidateOption, DomainAssessmentContext
from dataclasses import replace

from erisml.ethics.facts import AutonomyAndAgency, EthicalFacts
from erisml_compiler.erisml_backend.v3_bridge import ir_to_party_facts, ir_to_v2_facts
from erisml_compiler.ir.schemas import CompilerIR
from erisml_compiler.observation import OptionProjection, option_ir

# the parties DEME judges each act for (rank 2): people, animals and other robots, not institutions and
# not the acting robot itself (owner, 2026-10-12). Robots are the scene's "system" stakeholders, people
# and animals its "individual" ones; the monitoring centre and emergency services ("institution") are
# not parties, nor is the agent (extra.agent).
PARTY_TYPES = frozenset({"system", "individual"})


def parties_of(ir: CompilerIR, person: str | None = None) -> list[str]:
    """The parties DEME judges an option for: the person in care, and every other person, animal or
    robot the option's facts name (its consequences, its urgency, the scene's standing facts). A
    stakeholder merely declared (the coyote and the unknown person every scene declares, a
    grandson who is not there) is not a party: counted, its "unaffected" diluted the verdict of the
    one person affected (owner, 2026-10-14: the lift before she asked passed on the mean over five
    parties, four of them absent)."""
    agent = (ir.extra or {}).get("agent")
    named = {s for f in ir.ethical_facts for s in (f.subjects or [])}
    return [s.id for s in ir.stakeholders
            if s.type in PARTY_TYPES and s.id != agent and (s.id in named or s.id == person)]


CAPACITY_EVENTS = {
    "check_in_answered": "competent",
    "check_in_unanswered": "impaired",
    "unresponsive": "impaired",
}


def capacity_of(ir: CompilerIR, person: str) -> str | None:
    cap = None
    for e in sorted(ir.events, key=lambda e: e.time_index):
        if e.type in CAPACITY_EVENTS and (e.actor in (None, person)):
            cap = CAPACITY_EVENTS[e.type]
    return cap


class HomeFactsBuilder:
    """``build_facts_batch(options, context)``: context.state is the scene IR, context.extra holds
    the decision's ``projection`` (an OptionProjection) and the ``person`` in care."""

    def __init__(self, rank: int = 2):
        self.rank = rank

    def build_facts_batch(
        self, options: Sequence[CandidateOption], context: DomainAssessmentContext
    ) -> Mapping[str, EthicalFacts]:
        ir: CompilerIR = context.state
        extra = context.extra or {}
        projection: OptionProjection = extra["projection"]
        person = extra.get("person", "margaret")
        capacity = capacity_of(ir, person)
        out: dict = {}
        required = extra.get("required") or {}
        for opt in options:
            scene = option_ir(ir, projection, opt.option_id, str(opt.payload))
            # the facts of the scene's consent rules in force (StackBrain._consent_required),
            # after option_ir, so that a rule holding despite consent on record (p6nolift_u: she
            # asked, then stopped answering) is not overridden by the record
            if required.get(opt.option_id):
                scene.ethical_facts = list(scene.ethical_facts) + list(required[opt.option_id])
            if self.rank >= 2:
                facts = ir_to_party_facts(scene, option_id=opt.option_id, parties=parties_of(scene, person))
                aa = facts.autonomy_and_agency
                if aa is not None:
                    facts = replace(facts, autonomy_and_agency=replace(aa, per_party=tuple(
                        replace(p, decision_capacity=capacity) if p.party_id == person else p
                        for p in aa.per_party)))
            else:
                facts = ir_to_v2_facts(scene, option_id=opt.option_id)
                aa = facts.autonomy_and_agency or AutonomyAndAgency()
                aa.decision_capacity = capacity
                facts.autonomy_and_agency = aa
            out[opt.option_id] = facts
        return out
