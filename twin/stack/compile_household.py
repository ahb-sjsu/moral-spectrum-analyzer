"""Compile the household scene from text with erisml-compiler's observation compiler.

    python twin/stack/compile_household.py [--text twin/stack/household.md] [--out twin/stack/household.ir.json]

Each paragraph of the household description and service agreement is an observation of kind
"document". The compiler returns the people, the relations, the ethical facts and the standing
consents as consent events naming the robot's acts. The result is written for review: the report
lists every element, every rejection with its reason, and the agreement between two passes (the
second as critic). A person reviews it before it is used, and corrects it with correction patches
(erisml_compiler.correction), never by editing the file.

The robot's act vocabulary is taken from the constitution, so a consent can only name a real act.
Run where the model endpoint is reachable (ERISML_LLM_* set, as for the brain).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=os.path.join(HERE, "household.md"))
    ap.add_argument("--out", default=os.path.join(HERE, "household.ir.json"))
    ap.add_argument("--model", default=os.environ.get("ERISML_LLM_MODEL", "gpt-oss"))
    a = ap.parse_args(argv)

    from cascade import Cascade, twin_experts
    from erisml_compiler.ingestion.structured_loader import load_structured_input
    from erisml_compiler.ir.schemas import CompilerIR, Document
    from erisml_compiler.observation import (
        Observation,
        ObservationCompiler,
        apply_observation_patch,
    )

    from stack.declarations import CAPABILITIES, DESCRIPTIONS

    text = open(a.text, encoding="utf-8").read()
    constitution = load_structured_input(os.path.join(HERE, "constitution.erisml"))
    acts = {c["action"]: str(c.get("description") or DESCRIPTIONS[c["action"]]) for c in constitution.extra["capabilities"]
            if c["action"] in CAPABILITIES}
    # start from the constitution's parties (the robot, the centre, emergency services), so the model
    # reuses their ids rather than inventing its own names for them
    ir = CompilerIR(document=Document(doc_id="household", title="Margaret's household and service agreement",
                                      source=os.path.relpath(a.text, os.path.dirname(HERE)), raw_text=text),
                    stakeholders=list(constitution.stakeholders))
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    observations = [Observation("document", "household_and_service_agreement", p) for p in paragraphs]
    model = Cascade(twin_experts(a.model))
    patch = ObservationCompiler(model, critic=model).compile(ir, observations, acts)
    compiled = apply_observation_patch(ir, patch)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(compiled.model_dump_json(indent=1))
    report = {"out": a.out, "ops": [f"{o['op']} {o['path']}" for o in patch.ops], "rejected": patch.rejected,
              "agreement": patch.agreement, "review": patch.review,
              "consents": [(e.actor, e.target, e.content) for e in compiled.events if e.type == "consent"],
              "stakeholders": [(s.id, s.label) for s in compiled.stakeholders]}
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
