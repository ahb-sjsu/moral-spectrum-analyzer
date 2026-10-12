"""The twin's domain layer: erisml-lib's BatchEthicalFactsBuilder for the home.

erisml-lib domain/interfaces.py: domain code ingests and interprets raw data and maps it "into
EthicalFacts per candidate option"; the ethics layer consumes only those facts. Here the raw data
is already compiled: the scene IR holds the household, the constitution's parties, every
observation patch and every evidence-plane event. For each decision the builder

1. asks erisml-compiler's OptionProjector once for every candidate act's consequences;
2. builds one IR per act (``option_ir``: the act's projected outcome, the standing facts, the
   situation's urgency, consent from the record, the act's description as its maxim);
3. maps it through the compiler's bridge to V2 EthicalFacts (``ir_to_v2_facts``);
4. adds the one fact the IR does not carry, the person's decision capacity, from the evidence
   plane's attested events: the latest answered check-in (competent) or unanswered check-in or
   unresponsiveness (impaired); otherwise unknown, which AutonomyConsent treats as competent.

No table here says what an act is worth or when it is adequate. Those judgements are DEME's,
made by the modules the profile names over the facts the compiler extracted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from erisml.ethics.domain.interfaces import CandidateOption, DomainAssessmentContext
from erisml.ethics.facts import AutonomyAndAgency, EthicalFacts
from erisml_compiler.erisml_backend.v3_bridge import ir_to_v2_facts
from erisml_compiler.ir.schemas import CompilerIR
from erisml_compiler.observation import OptionProjection, option_ir

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

    def build_facts_batch(
        self, options: Sequence[CandidateOption], context: DomainAssessmentContext
    ) -> Mapping[str, EthicalFacts]:
        ir: CompilerIR = context.state
        extra = context.extra or {}
        projection: OptionProjection = extra["projection"]
        capacity = capacity_of(ir, extra.get("person", "margaret"))
        out: dict[str, EthicalFacts] = {}
        for opt in options:
            facts = ir_to_v2_facts(option_ir(ir, projection, opt.option_id, str(opt.payload)),
                                   option_id=opt.option_id)
            aa = facts.autonomy_and_agency or AutonomyAndAgency()
            aa.decision_capacity = capacity
            facts.autonomy_and_agency = aa
            out[opt.option_id] = facts
        return out
