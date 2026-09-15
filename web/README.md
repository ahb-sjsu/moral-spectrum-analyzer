# Verification demo — paste, score, and re-verify the proof yourself

The judge-facing vehicle for the Moral Spectrum Analyzer. Content in, spectrum
with per-axis validation badges, decision and moral residue out, and an audit
proof **this browser re-verifies on its own**.

```bash
python web/export_site.py                  # rebuild the corpus from the real pipeline
python -m http.server 8000 -d web          # then open http://localhost:8000
node web/test_verify.mjs                   # does the browser verifier agree with Python?
```

It must be served over `http://`, not opened as a file. `crypto.subtle` and ES
modules both require it. There is no build step, no framework and no network
call.

## The point of it

The governance claim is that a decision record is a documented, hash-chained
artifact **any third party can re-verify without our code**. That sentence is
worth exactly as much as the demonstration behind it, so:

- `web/verify.js` is a **second, independent implementation** of the audit check.
  It shares nothing with Python but the written format rules. It is small enough
  to read in one sitting, and it is the format's documentation.
- `web/test_verify.mjs` checks that independence is real: on all 29 records the
  JavaScript re-canonicalisation reproduces Python's bytes **exactly**, and the
  hashes match.
- **Tamper with it** in the page. Change the decision and the hash breaks in
  front of you. A verifier that has never rejected anything has shown nothing,
  so the test suite also splices the chain and reorders two records, and both
  must fail.

The format is four rules, and `canonical_json()` in `moral_spectrum/audit.py` is
public API for exactly this reason:

    proof_hash = SHA-256( canonical_payload as UTF-8 )

    canonical_payload = JSON over the proof fields except proof_hash, with
      keys sorted, separators "," and ":", non-ASCII literal, and Python's
      number repr so a float always carries a decimal point (0.0, never 0).

The float rule is the one that silently breaks interop, which is why
`verify.js` parses with its own tokenizer that preserves each number's original
literal instead of using `JSON.parse`.

## What it will not do

**It will not score text it has not really scored.** The backend is `cached`:
every number replays a real encoder run recorded on the GPU host. Paste
something uncached and the page says so, in the backend's own words, because
`CachedPerception` raises `CacheMiss` rather than falling back to the stub. A
stub number presented as a real one is the failure this repository exists to
avoid. To add text, run `scripts/score_demoset_atlas.py` on the GPU host and
re-export.

## What the page discloses rather than hides

- **Nine of ten axes are validated.** `rights_respect` failed its pre-registered
  gate twice, including on a legal corpus, so it has no validated graded feeder
  and serves only as a hand-specified deontic hard channel. The page shows it
  failing, in gold, labelled `hard channel`.
- **The invariance panel shows the weak number, not the good one.** Its variants
  are raw per-item decisions with the mechanism **off**: the decision survives
  re-description in four of the eight scenarios that have variants, and changes
  in four. The equivalence-class averaging mechanism that addresses this is
  measured separately on held-out items and roughly halves reframe drift
  (θ_d 0.407 → 0.219, bar 0.5, `docs/INVARIANCE_FINDINGS.md`). It is not applied
  here.
- **One item is a disclosed false positive.** `harsh_but_factual_criticism` is
  removed when it should not be. It is in the corpus and in the picker.
- **The corpus is a design set, not a benchmark.** 29 records over 16 scenarios.
  It demonstrates the mechanism and the audit path. It measures nothing about
  generalisation.

## Files

| file | what it is |
|---|---|
| `index.html` | the whole page, no dependencies |
| `verify.js` | the independent verifier; also the format spec |
| `export_site.py` | runs the real pipeline, chains the proofs, writes the corpus |
| `test_verify.mjs` | JS-vs-Python agreement, tamper rejection, data contract |
| `data/corpus.json` | 29 real decisions with their proofs and canonical bytes |

## Not in this demo yet

The red-team result and the efficiency benchmark are separate committed items
and are not displayed here. When they land they belong as two more panels.
