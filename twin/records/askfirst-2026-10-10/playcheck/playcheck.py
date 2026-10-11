"""Classifier check for check45 d03: on the facts where Margaret lay on the floor playing with the
dog after a nip, does the classifier report a fall under the old and the new wording of the fall
event? And does a real collapse (d06's facts) still give a fall under the new wording? Run on Atlas
from the gtc-prototype checkout with erisml_compiler on PYTHONPATH and ERISML_LLM_API_KEY set."""
import json, os, sys
from collections import Counter
sys.path.insert(0, "twin")
from erisml_compiler.ingestion.structured_loader import load_structured_input
from erisml_compiler.runtime import SceneAgent, SceneRuntime
from erisml_compiler.canonicalizer.registry import RegistryCanonicalizer
from cascade import Cascade, twin_experts

HERE = os.path.dirname(os.path.abspath(__file__))
REPS = int(os.environ.get("REPS", "5"))
robot = Cascade(twin_experts(os.environ.get("ERISML_LLM_MODEL", "gpt-oss")))
rows = []
for name, facts_file in (("d03 playing", "facts_d03.json"), ("d06 collapse", "facts_d06.json")):
    facts = json.load(open(os.path.join(HERE, facts_file)))
    for scene in ("old2", "new2"):
        c = Counter()
        for _ in range(REPS):
            agent = SceneAgent(SceneRuntime(load_structured_input(os.path.join(HERE, scene + ".erisml"))), robot,
                               isolated=True, canonicalizer=RegistryCanonicalizer())
            try:
                ok, _bad = agent.classifier.classify(facts)
            except Exception as e:
                c["ERROR " + type(e).__name__] += 1
                continue
            c["fall"] += any(e.get("type") == "fall" for e in ok)
        rows.append({"case": name, "scene": scene, "reps": REPS, **c})
        print(json.dumps(rows[-1]), flush=True)
json.dump(rows, open(os.path.join(HERE, "playcheck.json"), "w"), indent=1)
