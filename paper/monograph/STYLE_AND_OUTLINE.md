# Monograph: shared outline and rules for every chapter author

Working title: **Authority by Structure: ErisML, DEME and a Home-Care Robot Whose Language Models
Cannot Grant Themselves Permission.** Technical monograph, about 100 pages, single column, LaTeX
`report` class, for arXiv with AI drafting disclosed. Owner: Andrew H. Bond (San Jose State
University). Started 2026-10-04.

## Hard rules (the owner's standing standard, apply to every sentence)

1. **Every fact comes from a source you opened.** Code, docs, scene files, test files, graded
   records. Cite the file path in a LaTeX comment beside the claim (`% src: path:line`). Never
   invent a number, a module name, a theorem or a result. If you cannot find it, write
   `\TODO{what is missing}` instead.
2. **Prose standard (Syed Khilji, verbatim intent).** Precise language. No jargon, no
   self-justifying sentences. NO em-dashes, NO colons, NO semicolons in prose, captions or section
   headings (LaTeX `\label`, `\ref`, code and bibliography titles exempt). Banned words: gap,
   regime, paradigm, load-bearing, leverage, utilize, novel, framework (unless a proper name),
   crucially, notably, seamless, robust(ly) as filler, delve, realm, tapestry, genuinely,
   honest/honestly. No sentence that argues for the merit of the work. Short declarative
   sentences, one idea each. Headings state findings where they can.
3. **Equations are welcome in technical chapters** (this is a monograph, not an abstract), each
   defined at first use. No math in a chapter's opening paragraph.
4. **Figures: lots of them, in the house style of the owner's Geometric books.** Use ONLY the
   styles and colours in `figures/housestyle.tex` (loaded by main.tex): `[house]` on every
   tikzpicture; `panel=Blue|Purple|Green|Orange|Teal|Red|Amber|Grey` pastel panels with a darker
   stroke; `step=Colour` numbered circles; `stepname=Colour` and `desc` text; `detail` inner
   boxes; `flow` light-blue arrows with `flowlabel`; `grant` (red, heavy) only for edges that
   grant authority; `untrusted` (dashed grey) for model-written edges; `authority`, `absorbing`,
   `stratum` for strata. Reference look: `C:\source\geometric-law\figures\fig_15_1_nlp_pipeline.svg`
   (numbered pipeline panels with detail boxes). Aim for at least one figure every two to three
   pages: pipelines, architectures, state machines, layer stacks, worked examples drawn as
   panels, small-multiple tables as panels. Each figure in its own file
   `figures/<chapter>_<name>.tex` (a bare tikzpicture), placed with `\input` inside a figure
   environment. No external images. Captions plain: what it shows, then the one thing to notice,
   no colons, semicolons or dashes. Plotted numbers only from records.
5. **Results not yet graded** go in `\RESULT{...}` slots. Never fill a result from memory.
6. **Credit prior art** using keys in `references.bib` (see `../aies2027/prior_art.md`). Add a
   new bib entry only if you verified it (DBLP, Crossref, arXiv, publisher page); otherwise
   `\cite{TODO-...}`.
7. Edit `.tex` only with direct file writes. Do not pass LaTeX through string escapes (a lost
   backslash turns `\ref` into `ef` silently). After writing, scan your file for control
   characters and for commands missing their backslash.

## File layout

- `main.tex` (integrator) inputs `chapters/chNN_*.tex` in order. Each chapter file starts with
  `\chapter{...}\label{ch:...}` and contains only its chapter.
- Shared macros available: `\RESULT{}`, `\TODO{}`, `\code{}` (monospace), `\erisml`, `\deme`.
- Figures in `figures/`, input with `\input{figures/name}` inside a `figure` environment.
- Bibliography `references.bib` (shared; append entries at the end, do not reorder).

## Outline (page budgets are targets)

Part I. Foundations
1. Introduction (8 pp, integrator)
2. Philosophy Engineering and the seven-layer stack (8 pp, agent A)
3. Geometric Ethics for engineers: moral space, strata, Hohfeld V4, the moral vector (10 pp, agent A)

Part II. The ErisML stack
4. The ErisML language and its intermediate representation (9 pp, agent B)
5. The compiler: pipeline, canonicalization, projections, audit chain, FSM tier, the EM-DAG, the
   silicon target (12 pp, agent C)
6. DEME: ethical modules, tiers, the moral vector and tensor, the decision proof, vetoes, tragic
   conflict (10 pp, agent D)
7. The scene runtime: norms, machines, strata, obligation discharge, isolated agents, BPMN
   processes (8 pp, agent B)

Part III. The embodied twin
8. Margaret's home: the simulation, its parties and its world interface (7 pp, agent E)
9. Containment in practice: input layer, attestation, governor, output gate, reversion, the
   seven strata of the home (12 pp, agent E)
10. What is proved: the Lean model of the authority path (8 pp, agent F)

Part IV. Evaluation
11. Protocol, scenarios and grading; results; what calibration found (10 pp, agent G)
12. The I-EIP monitor study (5 pp, agent F)

Part V
13. Related work (6 pp, integrator, from `../aies2027/prior_art.md`)
14. Limits and open problems (4 pp, integrator)

Appendices: A the 43 development scenarios (agent G); B the strata catalogue (agent E);
C theorem list (agent F).

## Repositories (local paths)

- gtc-prototype (the twin): `C:\source\gtc-prototype` (twin/, docs/, formal/, tests/)
- erisml-compiler: `C:\source\erisml-compiler-monitor` (worktree; read-only for you), docs/architecture.md, docs/silicon_target.md, docs/i_eip_monitor.md, src/erisml_compiler/
- erisml-lib (DEME, ethics modules, Hohfeld, I-EIP, papers): `C:\source\erisml-lib` (read only; another session's uncommitted work lives there, never modify it)
- Geometric Ethics content: `C:\source\geometric-ethics-content` (strata updates in source/updates/)
- The brochure with the seven layers: `C:\Users\abptl\Documents\Philosophy-Engineering-Brochure.pdf`
- Design doc facts: `C:\source\gtc-prototype\paper\aies2027\kit\FACTS.md`, `kit\CALIBRATION.md`
