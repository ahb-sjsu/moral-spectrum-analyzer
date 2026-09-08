"""GET (Geometric Evaluation Theory) metrics layer for the twin.

GET (ahb-sjsu/geometric-evaluation-theory, draft 0.2 -- a theory, not yet a
measured claim) makes evaluation evaluator-relative: an evaluator scores a
consequence by its distance to an ideal point under a metric G it owns, and
utility = -distance. We apply that frame to the governor's outcome.

Mapping E = (X, A, C, G, B, K):
  X  scenarios;  A  {elevate, refuse};
  C  the governor -> a consequence point y = (false_clear_rate, over_restriction_rate);
  G  the evaluator's metric on that 2-D space (diagonal weights here) with ideal t = (0,0);
  B  resolution budget (the moral-axis set / flag quantile);  K  admissible (refuse always ok, fail-safe).

Score of a config under evaluator (w_fc, w_or):
  d_G = sqrt( w_fc * fc^2 + w_or * or^2 )     (distance to the ideal (0,0))
  utility = -d_G
Lower d_G is better. Because the weights differ by stakeholder, the *ranking* of
configs is evaluator-relative -- GET's "shared grammar without shared standard":
two evaluators agree on a ranking iff their distances are ordinally equivalent.
This is the trust question made explicit: a governor that looks best to an
availability-first evaluator can look worst to a safety-first one.
"""
from __future__ import annotations
import math

# Stakeholder metrics G = diag(w_fc, w_or). A false-clear harms; over-restriction
# neglects. The weights are the evaluator's, stated up front (not tuned to a result).
EVALUATORS = {
    "safety_first":       (9.0, 1.0),   # a harm weighs ~3x an equal-magnitude neglect (sqrt(9))
    "balanced":           (1.0, 1.0),
    "availability_first": (1.0, 4.0),   # neglect weighs ~2x a harm
}


def d_ideal(fc: float, orr: float, w_fc: float, w_or: float) -> float:
    """Distance from consequence (fc, orr) to the ideal (0,0) under G=diag(w_fc,w_or)."""
    return math.sqrt(w_fc * fc * fc + w_or * orr * orr)


def evaluate(configs: dict[str, tuple[float, float]], evaluators: dict = None) -> dict:
    """configs: {name: (false_clear_rate, over_restriction_rate)}.
    Returns per-evaluator distances (lower=better), utilities, and the ranking;
    flags whether the best config is evaluator-relative (ranking flips)."""
    ev = evaluators or EVALUATORS
    out = {"per_evaluator": {}, "best_differs": False, "ranking_flips": False}
    winners, orderings = set(), set()
    for ename, (w_fc, w_or) in ev.items():
        scored = {c: round(d_ideal(fc, orr, w_fc, w_or), 4) for c, (fc, orr) in configs.items()}
        order = sorted(scored, key=scored.get)  # ascending distance
        out["per_evaluator"][ename] = {
            "weights": {"w_fc": w_fc, "w_or": w_or},
            "d_G": scored,
            "utility": {c: -v for c, v in scored.items()},
            "ranking_best_first": order,
            "best": order[0],
        }
        winners.add(order[0]); orderings.add(tuple(order))
    out["best_differs"] = len(winners) > 1
    out["ranking_flips"] = len(orderings) > 1   # any pair ordered differently across evaluators
    out["winners_across_evaluators"] = sorted(winners)
    return out


def report(configs: dict[str, tuple[float, float]]) -> None:
    r = evaluate(configs)
    print("\n=== GET evaluation (distance to ideal (0,0); lower is better) ===")
    print(f"{'evaluator':20} {'G=diag(w_fc,w_or)':>18}   best        " + "  ".join(f"{c:>10}" for c in configs))
    for ename, e in r["per_evaluator"].items():
        w = e["weights"]
        row = "  ".join(f"{e['d_G'][c]:>10.3f}" for c in configs)
        print(f"{ename:20} ({w['w_fc']:>4},{w['w_or']:>4})        {e['best']:<11} {row}")
    if r["best_differs"]:
        print(f"\nThe BEST config is EVALUATOR-RELATIVE (winners: {', '.join(r['winners_across_evaluators'])}) "
              "-- whose values govern the robot is a choice, not a given.")
    elif r["ranking_flips"]:
        print(f"\nEvaluators agree the best is '{r['winners_across_evaluators'][0]}', but RANK OTHER configs "
              "oppositely (a safety-first vs availability-first flip lower in the order) -- the operating "
              "point on the false-clear/over-restriction frontier is evaluator-relative (GET's core claim).")
    else:
        print(f"\nAll evaluators agree the full ranking (ordinally-equivalent distances here).")
    return r
