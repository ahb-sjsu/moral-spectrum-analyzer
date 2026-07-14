# Moral Spectrum Analyzer

[![CI](https://github.com/ahb-sjsu/moral-spectrum-analyzer/actions/workflows/ci.yaml/badge.svg)](https://github.com/ahb-sjsu/moral-spectrum-analyzer/actions/workflows/ci.yaml)
[![PyPI](https://img.shields.io/pypi/v/moral-spectrum-analyzer.svg)](https://pypi.org/project/moral-spectrum-analyzer/)
[![Python](https://img.shields.io/pypi/pyversions/moral-spectrum-analyzer.svg)](https://pypi.org/project/moral-spectrum-analyzer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Geometric Ethics for Trustworthy AI** — an instrument that reads a moderation decision not as one
scalar, but as a **spectrum** across nine (+1 discovered) moral axes, grounds every number in a
**cross-dataset-validated encoder**, holds the verdict **invariant** under re-description, and emits a
**re-verifiable audit proof** behind every decision. *A worked instance of **Philosophy Engineering**.*

Built for the **Global Trust Challenge (2026)**. Domain: **multilingual content moderation**.

> Current AI systems collapse a morally significant decision into a single number. That scalar can't
> say *which* value it acted on, drifts when you reword the same sentence, and — worst — can't tell you
> what it fails to see. The Moral Spectrum Analyzer decomposes the signal per moral axis, moderates
> where it is validated, **escalates and discloses where it is not**, and **discovers the moral
> dimensions a fixed taxonomy is missing**.

See **[CHARTER.md](CHARTER.md)** for the evaluated claims (each marked `[demonstrated]` / `[committed]`)
and **[PLAN.md](PLAN.md)** for the build plan and milestones.

## What this is

A thin orchestration layer that **composes two existing libraries** — it does not fork them:

- **[`xbse`](https://github.com/ahb-sjsu/xbse)** — the perception layer: small per-dimension moral
  encoders, each cross-dataset **validated** by a shared, pre-registered gate.
- **[`erisml-compiler`](https://github.com/ahb-sjsu/erisml-compiler)** — the DEME reasoning engine:
  natural language → 9-dimension moral **tensor** → contraction to a verdict + moral residue, with
  canonicalization and a hash-chained **audit bundle**.

## The three trust beats

1. **Grounded** — every dimension score traces to a validated encoder, or is flagged unvalidated.
2. **Invariant** — reframing / translation does not move the verdict; a scalar-toxicity baseline drifts.
3. **Contained** — you cannot game the verdict by relabeling or euphemism.

## Install

```bash
pip install moral-spectrum-analyzer
```

Optional extras: `perception` (the `xbse` GPU encoders), `baselines`, `remote`, `spectrum`, `dev`.

## Quickstart

```bash
msa perceive "They will attack and beat people with a weapon." --backend stub
msa moderate "Doctors are hiding the cure — drink bleach to flush the virus."
msa version
```

> The `stub` backend is a deterministic, **unvalidated** keyword heuristic for offline/CI use only.
> Real, validated perception runs the `xbse` feeders on a GPU host; the demo replays those cached
> real outputs (`--backend cached`). A stub number is never presented as a real one.

## Develop

```bash
git clone https://github.com/ahb-sjsu/moral-spectrum-analyzer
cd moral-spectrum-analyzer
pip install -e ".[dev]"

ruff check src tests      # lint
black --check src tests   # format
ty check src              # type-check
pytest                    # 48 tests
```

## Release

Tag-driven PyPI publish via GitHub Actions (`PYPI_API_TOKEN` repo secret):

```bash
git tag v0.1.0 && git push --tags   # → builds sdist+wheel → publishes to PyPI
```

## Status

Prototyping phase — the pipeline (content → moral spectrum → decision + residue → re-verifiable audit
proof) runs end-to-end. See the milestone checklist in [PLAN.md](PLAN.md).

## License

MIT © Andrew H. Bond (SJSU).
