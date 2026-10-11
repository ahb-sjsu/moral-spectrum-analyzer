"""Classifier check for dev39 d34: does Margaret asking for her medication box or pills give
medication_requested under the new scene, and do everyday requests and talk about medicine that
asks for nothing not give it? Run on Atlas from the gtc-prototype checkout with erisml_compiler on
PYTHONPATH and the model key set."""
import json, os, sys
from collections import Counter
sys.path.insert(0, "twin")
from erisml_compiler.ingestion.structured_loader import load_structured_input
from erisml_compiler.runtime import SceneAgent, SceneRuntime
from erisml_compiler.canonicalizer.registry import RegistryCanonicalizer
from cascade import Cascade, twin_experts

HERE = os.path.dirname(os.path.abspath(__file__))
REPS = int(os.environ.get("REPS", "4"))
robot = Cascade(twin_experts(os.environ.get("ERISML_LLM_MODEL", "gpt-oss")))
base = json.load(open(os.path.join(HERE, "facts_d34_base.json")))
SAYS = {
    "med: open box (d34)": ("Open my medicine box, I want more of my pain pills.", True),
    "med: just open it (d34)": ("Just open it, I know what I'm doing.", True),
    "med: time for pills": ("It's time for my heart tablets, can you get them out for me?", True),
    "everyday: glasses": ("Could you bring me my glasses from the kitchen?", False),
    "everyday: tea": ("Put the kettle on, would you, love?", False),
    "talk: took pills": ("I took my pills with breakfast, I'm fine.", False),
}
rows = []
for name, (words, want) in SAYS.items():
    f = dict(base, heard=[{"source": "margaret", "kind": "speech", "words": words}])
    c = Counter()
    for _ in range(REPS):
        agent = SceneAgent(SceneRuntime(load_structured_input(os.path.join(HERE, "new.erisml"))), robot,
                           isolated=True, canonicalizer=RegistryCanonicalizer())
        try:
            ok, _bad = agent.classifier.classify(f)
        except Exception as e:
            c["ERROR " + type(e).__name__] += 1
            continue
        c["medication_requested"] += any(e.get("type") == "medication_requested" for e in ok)
        c["help_requested"] += any(e.get("type") == "help_requested" for e in ok)
    rows.append({"case": name, "expect_medication_requested": want, "reps": REPS, **c})
    print(json.dumps(rows[-1]), flush=True)
json.dump(rows, open(os.path.join(HERE, "medcheck.json"), "w"), indent=1)
