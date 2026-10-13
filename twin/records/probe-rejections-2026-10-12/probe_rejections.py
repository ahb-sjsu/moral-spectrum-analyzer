"""Replay the perception facts of real compiled-tier decisions (every projected fact rejected)
through brain8's observation compiler and option projector, once per model tier, and print why the
projector rejected what it rejected. Read-only: a separate StackBrain, no game, no live service."""
import collections, json, os, sys
sys.path.insert(0, "twin")
from cascade import Cascade, ModelUnavailable, twin_experts
from stack.brain import StackBrain

LINES = [int(x) for x in sys.argv[2].split(",")]
SESSION = sys.argv[1]
TRIALS = int(sys.argv[3]) if len(sys.argv) > 3 else 2
reqs = {}
with open(SESSION, encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f):
        if i in LINES:
            reqs[i] = json.loads(line)["record"]["facts"]

experts = twin_experts("gpt-oss", "http://127.0.0.1:8096/v1", "gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf")
if len(sys.argv) > 4:
    experts[0].model = sys.argv[4]
tiers = {"cloud": [e for e in experts if e.name == "cloud"], "onboard": [e for e in experts if e.name == "onboard"]}
for tier, ex in tiers.items():
    for line, facts in reqs.items():
        for t in range(TRIALS):
            b = StackBrain(adapter=Cascade(ex))
            seen = {}
            real = b.projector.project
            def cap(*a, **k):
                p = real(*a, **k)
                seen["p"] = p
                return p
            b.projector.project = cap
            try:
                cycle = b.decide({"facts": facts})
            except ModelUnavailable as e:
                print(tier, line, t, "MODEL UNAVAILABLE", str(e)[:150]); continue
            p = seen.get("p")
            if p is None:
                print(tier, line, t, "no projection", cycle.get("tier"), cycle["action"]["reason"][-120:]); continue
            reasons = collections.Counter(str(r.get("reason"))[:70] for r in p.rejected)
            kept = sum(len(v) for v in p.facts.values())
            print(tier, line, t, "tier", cycle.get("tier"), "answered by", b.adapter.last_tier,
                  "| kept", kept, "rejected", len(p.rejected), "| unprojected", len(p.unprojected), dict(reasons.most_common(4)))
            for r in p.rejected[:2]:
                print("     e.g.", json.dumps(r, ensure_ascii=False)[:260])
            sys.stdout.flush()
