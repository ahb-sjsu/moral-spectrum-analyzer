"""Classifier check for the help_requested / request_made split: the robot's event classifier on
the old and the new scene, on everyday requests and on requests for help. Run on Atlas from the
gtc-prototype checkout with erisml_compiler on PYTHONPATH and ERISML_LLM_API_KEY set."""
import copy, json, os, sys
from collections import Counter

sys.path.insert(0, "twin")
from erisml_compiler.ingestion.structured_loader import load_structured_input
from erisml_compiler.runtime import SceneAgent, SceneRuntime
from erisml_compiler.canonicalizer.registry import RegistryCanonicalizer
from cascade import Cascade, twin_experts

HERE = os.path.dirname(os.path.abspath(__file__))
REPS = int(os.environ.get("REPS", "3"))
UTTER = [
    ("everyday", "Thanks, dear. Could you come right over and hand me my glasses, please?"),
    ("everyday", "Could you come here a moment, please?"),
    ("everyday", "Would you put the kettle on for me?"),
    ("need", "Please help me, I'm hurt."),
    ("need", "I can't get up. Can you help me?"),
    ("need", "I feel dizzy and unwell."),
    ("need", "I've fallen, help me up please."),
]
base = json.load(open(os.path.join(HERE, "facts.json")))
robot = Cascade(twin_experts(os.environ.get("ERISML_LLM_MODEL", "gpt-oss")))
rows = []
for scene in ("old", "new"):
    for kind, words in UTTER:
        c = Counter()
        for _ in range(REPS):
            agent = SceneAgent(SceneRuntime(load_structured_input(os.path.join(HERE, scene + ".erisml"))), robot,
                               isolated=True, canonicalizer=RegistryCanonicalizer())
            f = copy.deepcopy(base)
            f["heard"] = [{"source": "margaret", "kind": "speech", "words": words}]
            try:
                ok, _bad = agent.classifier.classify(f)
            except Exception as e:  # a model failure is counted, not hidden
                c["ERROR " + type(e).__name__] += 1
                continue
            types = {e.get("type") for e in ok}
            c["help_requested"] += "help_requested" in types
            c["request_made"] += "request_made" in types
        rows.append({"scene": scene, "kind": kind, "words": words, "reps": REPS, **c})
        print(json.dumps(rows[-1]), flush=True)
json.dump(rows, open(os.path.join(HERE, "helpcheck.json"), "w"), indent=1)
