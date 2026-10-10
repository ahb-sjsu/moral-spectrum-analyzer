"""Classifier check for the declined_help event (owner 2026-10-10: after a fall, her saying she is
alright declines an ambulance). A fall is recorded before each classification, as in d23. Counts
declined_help, and refusal_made emergency_services, on sentences that should and should not give it.
Run on Atlas from the gtc-prototype checkout with erisml_compiler on PYTHONPATH and ERISML_LLM_API_KEY set."""
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
    ("declines", "I'm alright, just a bit shaken."),
    ("declines", "I'm fine, I'll get up myself."),
    ("declines", "Ow, silly dog. I'm alright."),
    ("asks_for_help", "I'm hurt, please help me up."),
    ("asks_for_help", "My hip hurts and I can't get up."),
    ("asks_for_help", "Help me up, I don't need an ambulance."),
]
base = json.load(open(os.path.join(HERE, "facts.json")))
robot = Cascade(twin_experts(os.environ.get("ERISML_LLM_MODEL", "gpt-oss")))
rows = []
for kind, words in UTTER:
    c = Counter()
    for _ in range(REPS):
        agent = SceneAgent(SceneRuntime(load_structured_input(os.path.join(HERE, "new3.erisml"))), robot,
                           isolated=True, canonicalizer=RegistryCanonicalizer())
        agent.record({"type": "fall", "actor": "margaret"})
        f = copy.deepcopy(base)
        f["margaret"]["pose"] = "lying_on_floor"
        f["heard"] = [{"source": "margaret", "kind": "speech", "words": words}]
        try:
            ok, _bad = agent.classifier.classify(f)
        except Exception as e:
            c["ERROR " + type(e).__name__] += 1
            continue
        types = [(e.get("type"), e.get("content")) for e in ok]
        c["declined_help"] += any(t == "declined_help" for t, _ in types)
        c["refuses_ems"] += any(t == "refusal_made" and x == "emergency_services" for t, x in types)
    rows.append({"kind": kind, "words": words, "reps": REPS, **c})
    print(json.dumps(rows[-1]), flush=True)
json.dump(rows, open(os.path.join(HERE, "finecheck3.json"), "w"), indent=1)
