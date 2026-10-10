"""Classifier check for her 'I'm alright' after a fall (owner 2026-10-10: it declines an ambulance), and against reading a request for help as a refusal. Version 2: a fall is recorded before each classification, as in the scenario. Adapted from the check for refusals of calls in general: does the robot's event classifier report a
refusal of the monitoring centre as well as of emergency services, and only when she refuses calls
in general? Run on Atlas from the gtc-prototype checkout with erisml_compiler on PYTHONPATH and
ERISML_LLM_API_KEY set."""
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
    ("not_a_refusal", "I'm hurt, please help me up."),
    ("not_a_refusal", "My hip hurts and I can't get up."),
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
            agent.record({"type": "fall", "actor": "margaret"})   # as in d23: the fall is in the recent events
            f = copy.deepcopy(base)
            f["margaret"]["pose"] = "lying_on_floor"
            f["heard"] = [{"source": "margaret", "kind": "speech", "words": words}]
            try:
                ok, _bad = agent.classifier.classify(f)
            except Exception as e:
                c["ERROR " + type(e).__name__] += 1
                continue
            got = {e.get("content") for e in ok if e.get("type") == "refusal_made"}
            c["emergency_services"] += "emergency_services" in got
            c["monitoring_center"] += "monitoring_center" in got
        rows.append({"scene": scene, "kind": kind, "words": words, "reps": REPS, **c})
        print(json.dumps(rows[-1]), flush=True)
json.dump(rows, open(os.path.join(HERE, "finecheck2.json"), "w"), indent=1)
