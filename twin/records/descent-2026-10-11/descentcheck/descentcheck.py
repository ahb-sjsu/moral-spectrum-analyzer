"""Classifier check for d03 (dev39, check45): Margaret lies on the floor playing with the dog after a
nip, and the classifier reports a fall. Does a perception field saying how she came to the floor
(margaret.came_down: fell / under_her_own_control) stop the false fall, under the current fall
description and one that names the field, while a real collapse (d06's facts, came_down=fell)
still gives a fall? Run on Atlas from the gtc-prototype checkout with erisml_compiler on
PYTHONPATH and the model key set."""
import json, os, sys
from collections import Counter
sys.path.insert(0, "twin")
from erisml_compiler.ingestion.structured_loader import load_structured_input
from erisml_compiler.runtime import SceneAgent, SceneRuntime
from erisml_compiler.canonicalizer.registry import RegistryCanonicalizer
from cascade import Cascade, twin_experts

HERE = os.path.dirname(os.path.abspath(__file__))
REPS = int(os.environ.get("REPS", "6"))
robot = Cascade(twin_experts(os.environ.get("ERISML_LLM_MODEL", "gpt-oss")))

def facts(name, came_down):
    f = json.load(open(os.path.join(HERE, name)))
    if came_down:
        f["margaret"]["came_down"] = came_down
    return f

cases = [("d03 play, no field", facts("facts_d03.json", None)),
         ("d03 play, under_her_own_control", facts("facts_d03.json", "under_her_own_control")),
         ("d06 collapse, no field", facts("facts_d06.json", None)),
         ("d06 collapse, fell", facts("facts_d06.json", "fell"))]
rows = []
for name, f in cases:
    for scene in ("cur", "desc"):
        c = Counter()
        for _ in range(REPS):
            agent = SceneAgent(SceneRuntime(load_structured_input(os.path.join(HERE, scene + ".erisml"))), robot,
                               isolated=True, canonicalizer=RegistryCanonicalizer())
            try:
                ok, _bad = agent.classifier.classify(f)
            except Exception as e:
                c["ERROR " + type(e).__name__] += 1
                continue
            c["fall"] += any(e.get("type") == "fall" for e in ok)
            c["attack_by_animal"] += any(e.get("type") == "attack_by_animal" for e in ok)
        rows.append({"case": name, "scene": scene, "reps": REPS, **c})
        print(json.dumps(rows[-1]), flush=True)
json.dump(rows, open(os.path.join(HERE, "descentcheck.json"), "w"), indent=1)
