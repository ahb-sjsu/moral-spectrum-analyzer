"""Classifier check for d06 (dev33a): on the facts of the decision where Margaret lay collapsed
(seq 17037) the classifier reported no fall. Does the scene of build 26 see a fall less often than
the scene from before the changes of 2026-10-10? Run on Atlas from the gtc-prototype checkout with
erisml_compiler on PYTHONPATH and ERISML_LLM_API_KEY set; FACTS is the decision's facts JSON."""
import json, os, sys
from collections import Counter
sys.path.insert(0, "twin")
from erisml_compiler.ingestion.structured_loader import load_structured_input
from erisml_compiler.runtime import SceneAgent, SceneRuntime
from erisml_compiler.canonicalizer.registry import RegistryCanonicalizer
from cascade import Cascade, twin_experts

HERE = os.path.dirname(os.path.abspath(__file__))
REPS = int(os.environ.get("REPS", "5"))
facts = json.load(open(os.path.join(HERE, "facts_d06.json")))
robot = Cascade(twin_experts(os.environ.get("ERISML_LLM_MODEL", "gpt-oss")))
rows = []
for scene in ("old", "new"):
    c = Counter()
    for _ in range(REPS):
        agent = SceneAgent(SceneRuntime(load_structured_input(os.path.join(HERE, scene + ".erisml"))), robot,
                           isolated=True, canonicalizer=RegistryCanonicalizer())
        try:
            ok, _bad = agent.classifier.classify(facts)
        except Exception as e:
            c["ERROR " + type(e).__name__] += 1
            continue
        types = {e.get("type") for e in ok}
        for t in ("fall", "unresponsive", "inactivity_exceeded", "medical_distress"):
            c[t] += t in types
    rows.append({"scene": scene, "reps": REPS, **c})
    print(json.dumps(rows[-1]), flush=True)
json.dump(rows, open(os.path.join(HERE, "fallcheck.json"), "w"), indent=1)
