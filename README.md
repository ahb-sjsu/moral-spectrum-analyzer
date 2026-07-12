# gtc-prototype

**Geometric Ethics for Trustworthy AI** — prototype for the **Global Trust Challenge (2025)**.
Domain: **multilingual content moderation**.

> Current AI systems collapse morally significant decisions into a single scalar. This prototype
> instead represents each decision as a **tensor** over nine moral dimensions, grounds every number
> in a **cross-dataset-validated encoder**, verifies **invariance** under re-description, and proves
> **structural containment** against relabeling attacks — trust as a measurable property, not a hope.

See **[PLAN.md](PLAN.md)** for the full build plan, verified recon, and milestone checklist.

## What this repo is

A thin orchestration layer that composes two existing libraries — it does **not** fork them:

- **[`xbse`](https://github.com/ahb-sjsu/xbse)** — the perception layer: small per-dimension moral
  encoders, each cross-dataset **validated** by a shared, pre-registered gate.
- **[`erisml-compiler`](https://github.com/ahb-sjsu/erisml-compiler)** — the DEME reasoning engine:
  natural language → 9-dimension moral **tensor** → contraction to a verdict + moral residue, with
  LaBSE canonicalization and a hash-chained **audit bundle**.

## The three trust beats

1. **Grounded** — every dimension score traces to a validated encoder, or is flagged unvalidated.
2. **Invariant** — reframing / translation does not move the verdict; a scalar-toxicity baseline drifts.
3. **Contained** — you cannot game the verdict by relabeling or euphemism.

## Quickstart

```bash
pip install -e ".[dev]"
pytest -q
gtc perceive "They will attack and beat people with a weapon." --backend stub
```

> The `stub` backend is a deterministic, **unvalidated** keyword heuristic for offline/CI use only.
> Real, validated perception runs the `xbse` feeders on a GPU host (Atlas); the web demo replays
> those cached real outputs. A stub number is never presented as a real one.

## Status

Phase 0 (scaffold) — in progress. See the milestone checklist in [PLAN.md](PLAN.md).

## License

MIT © Andrew H. Bond (SJSU).
