# Prior art: AIES 2027 paper on the GTC home-care twin (Margaret)

Compiled 2026-10-03. Bibliographic records were checked against Crossref, the arXiv API, and publisher or proceedings pages. DBLP blocked automated access, so it was not used. Citation keys refer to `references.bib` in this folder. "Must credit" means the work does something close enough to a claimed contribution that a reviewer would flag its absence.

The system, in one line: an LLM may only classify perception into scene events and choose among already-permitted actions. Authority (the right to override her wishes, restrain, or call emergency services) moves only on system events: attested physical sensor witnesses (2 to elevate, 3 for restraint), authenticated channels, and governor rulings. A compiled deontic runtime, strata with semantic gates, a DEME veto gate, a BPMN escalation ladder, and Lean 4 proofs back this up.

---

## 1. Ethical governors (Arkin and successors)

**Arkin, *Governing Lethal Behavior* (2009 book; 2008 HRI paper; 2009 tech report with Ulam & Duncan; 2012 Proc. IEEE)** (`arkin2009governing`, `arkin2008governing`, `arkin2009ethicalgovernor`, `arkin2012moral`).
What it does: an "ethical governor" sits between a robot's behavioral controller and its actuators. It checks each proposed lethal action against constraints derived from the Laws of War and Rules of Engagement, suppresses impermissible actions, and requires obligations to be satisfied before lethal force is allowed. Responsibility is assigned through an operator-override interface.
How it differs: Arkin's constraints are hand-coded logical predicates evaluated over situational beliefs, with no learned or LLM components and no treatment of where those beliefs come from. Our system treats belief provenance as the central question: who may assert the facts that unlock authority. It also adds multi-witness sensor attestation, strata, and machine-checked proofs.
Credit: **must credit.** "A governor that sits between proposal and actuation and vetoes impermissible actions" is Arkin's architecture. The paper should present its governor as a descendant and should probably rename it, or explicitly say "in the sense of Arkin", to avoid seeming to claim the term.

**Shim, Arkin & Pettinatti 2017, an intervening ethical governor for a robot mediator in patient–caregiver relationships (ICRA)** (`shim2017intervening`).
What it does: applies the governor architecture to a care setting. A robot mediates between patients with Parkinson's disease (whose reduced facial expressivity can lead to stigmatization) and their caregivers, and the governor intervenes to preserve patient and caregiver dignity.
How it differs: it covers dyadic interaction mediation, with no authority escalation, no LLM, and no consent or legitimacy state machines.
Credit: **must credit.** It is the direct precedent for "governor in a care context", and a reviewer from HRI will know it.

**Critiques: Matthias 2011; Sharkey 2010** (`matthias2011governor`, `sharkey2010sayingno`).
Matthias argues the governor conflates legal codes (LOW/ROE) with morality and cannot provide moral dissent. Sharkey argues that robots cannot reliably make the perceptual discriminations (combatant vs. civilian) that such rules presuppose.
How they relate: Sharkey's perceptual-discrimination objection is exactly the problem the attestation/witness design addresses. The system refuses to let a perceptual classifier's output carry authority. The paper should cite Sharkey as motivation, not as a rival. Matthias's "law ≠ ethics" point applies to the DEME/Geneva veto modules and should be acknowledged in limitations.
Credit: cite both. They are critiques, not competing systems.

## 2. Winfield et al.: consequence engine and ethical black box

**Winfield, Blum & Liu 2014 (TAROS); Vanderelst & Winfield 2018 (Cognitive Systems Research)** (`winfield2014towards`, `vanderelst2018architecture`).
What it does: the "consequence engine" runs an internal simulation of each candidate action, predicts outcomes for the robot and for humans, and has an ethical layer that filters actions (an Asimovian robot diverting a human from a hole).
How it differs: the selection is consequence-based, using simulation of outcomes. Our system is deontic and authority-based. A Unity digital twin could be confused with a consequence engine, so the paper must make clear that the twin is the *test environment*, not an internal model used for action selection (if that is true).
Credit: **must credit** as the main alternative architecture, consequentialist rather than deontic.

**Vanderelst & Winfield 2018, "The Dark Side of Ethical Robots" (AIES 2018)** (`vanderelst2018darkside`).
What it does: shows that the same ethical-robot architecture can be made competitive or aggressive by trivially altering its evaluation function, so an "ethical" robot is only as safe as its value module's integrity.
How it relates: this is the strongest published motivation for *structural* containment, meaning the model must not be able to rewrite what authorizes action. It was published at AIES itself.
Credit: **must cite**, as motivation.

**Winfield & Jirotka 2017 (ethical black box); Winfield et al. 2022 (draft EBB standard); Winfield & Jirotka 2018 (ethical governance)** (`winfield2017ebb`, `winfield2022ebbstandard`, `winfield2018governance`).
What it does: proposes a flight-recorder-style log of sensor inputs, decisions, and internal state for accident investigation, and later a draft open standard for social robots.
How it differs: the EBB is post-hoc accountability, not runtime constraint. If the system logs witness attestations, rulings, and stratum transitions, that log is an EBB in Winfield's sense.
Credit: cite. If the paper presents an audit trail, it **must** credit the EBB.

## 3. Verifiable machine ethics (Dennis, Fisher et al.) and logicist robot ethics (Bringsjord)

**Dennis, Fisher, Slavkovik & Webster 2016, "Formal verification of ethical choices in autonomous systems" (RAS 77)** (`dennis2016formal`).
What it does: the ETHAN framework. A BDI agent selects plans and an ethical layer chooses among them using ordered ethical principles when no plan is fully ethical. The agent program is model-checked (AJPF) to prove it always picks the least-unethical option.
How it differs: the proofs are about *plan selection under an ethical ordering*. Our Lean proofs are about *information flow to authority*: no model-classified event reaches an authority-granting stratum. Both are "formal guarantees about an ethical layer", so the paper must state precisely what its theorem says and does not say (it does not prove the robot's choices are ethical).
Credit: **must credit** as the canonical "verified ethical choice" work. Also cite `dennis2016practical` for the agent-verification method.

**Bremner, Dennis, Fisher & Winfield 2019 (Proc. IEEE)** (`bremner2019proactive`).
What it does: joins Winfield's consequence engine with Dennis/Fisher verification on a real NAO robot. An ethical governor (their term) is formally verified and tested.
How it differs: there is no LLM and no authority or attestation model. Still, the combination "ethical governor + formal verification + implemented robot" already exists.
Credit: **must credit.** It undercuts any claim to be "the first verified ethical governor for a robot".

**Bringsjord, Arkoudas & Bello 2006 (IEEE Intelligent Systems)** (`bringsjord2006toward`).
What it does: argues that robot ethics should be engineered in deontic logic with proof-checked permissibility, so that a robot acts only when a proof that the action is permissible exists.
How it differs: it is logicist end to end, with no learned perception. Our system uses deontic norms at runtime and proofs offline.
Credit: cite as the origin of "deontic logic as the robot's operational code".

**Anderson, Anderson & Berenz 2019, a value-driven eldercare robot (Proc. IEEE)** (`anderson2019eldercare`).
What it does: an eldercare robot (simulated and on a NAO) whose action choice comes from an ethical principle learned from ethicist-judged cases. Its behaviors include reminding about medication, deciding when to notify an overseer, and respecting autonomy versus preventing harm.
How it differs: its principle is learned from cases (the GenEth line of work; I did not re-read the paper to confirm the learning method) and it has no authority model. But "eldercare robot balancing autonomy against harm, deciding when to escalate to a human overseer" is **the same scenario family** as Margaret.
Credit: **must credit.** This is the closest eldercare precedent and reviewers in machine ethics will expect it.

**Tolmeijer et al. 2021 (ACM CSUR)** (`tolmeijer2021implementations`): survey of machine-ethics implementations. Cite it to place the system in the top-down/rule-based family.

## 4. Normative multi-agent systems and normative requirements for robots (SLEEC)

**Boella, van der Torre & Verhagen 2006** (`boella2006normative`): the standard introduction to normative MAS (obligations, permissions, violations, sanctions). Cite as background for the deontic runtime. No novelty conflict.

**SLEEC line (York/Toronto): Getir Yaman et al. 2023 (FASE), 2024 (SCP toolkit), 2025 (JSS); Feng et al. 2024 (RE, LLMs for operationalizing normative requirements); Ribeiro et al. 2026 (FM, "The SLEEC Framework")** (`getiryaman2023sleec`, `getiryaman2024sleectoolkit`, `getiryaman2025sleecjss`, `feng2024normative`, `ribeiro2026sleecframework`).
What it does: a DSL for social, legal, ethical, empathetic and cultural (SLEEC) rules for autonomous agents. Rules take the form "when event then response *unless* defeater", which is defeasible. There are conflict and redundancy checks and verification against robot models (CSP/RoboChart), with assistive and care robots as running examples. (I did not open the full texts; check that the specific care examples match before describing them.) Feng et al. 2024 uses LLMs to help operationalize such rules.
How it differs: SLEEC is mainly a requirements-engineering and design-time verification approach. It does not model authority provenance, attested witnesses, strata, or an LLM acting at runtime.
Credit: **must credit, prominently.** "Declarative defeasible norms for care robots, compiled and checked formally" is SLEEC's territory. The paper must not claim novelty for the norm language as such. Novelty has to rest on the authority/provenance layer and the LLM containment.

**De Sanctis et al. 2026, "Runtime Enforcement for Operationalizing Ethics in Autonomous Systems" (arXiv 2604.03714, preprint)** (`desanctis2026sleecruntime`).
What it does: SLEEC@run.time enforces SLEEC rules at runtime via Abstract State Machines in a MAPE-K loop, demonstrated on an **assistive robot scenario**.
How it differs: there is no LLM threat model and no attestation or authority gating, but it is runtime enforcement of declarative care norms on an assistive robot.
Credit: **must credit** as close concurrent work. (It is unrefereed as of 2026-10-03; cite as a preprint.)

**Joshi, Finin, Joshi & Kagal 2026, deontic policies for runtime governance of agentic AI (ICWS 2026; arXiv 2606.19464)** (`joshi2026deontic`).
What it does: AgenticRei applies the Rei policy language (permissions, prohibitions, obligations, dispensations, meta-policy for conflicts) to govern LLM agents' tool calls at runtime.
How it differs: it covers enterprise IT agents, not embodied care, and has no sensor attestation. Still, "a deontic runtime with obligations and conflict resolution governing an LLM agent" exists.
Credit: **must credit** as concurrent work. It undercuts any claim to be the first deontic runtime for LLM agents.

## 5. Safety shields and runtime verification

**Alshiekh et al. 2018, "Safe Reinforcement Learning via Shielding" (AAAI); Bloem et al. 2015, shield synthesis (TACAS)** (`alshiekh2018shielding`, `bloem2015shield`).
What it does: a shield synthesized from a temporal-logic safety specification sits before (preemptive) or after (post-posed) a learning agent. It removes or corrects unsafe actions, with a correctness guarantee relative to the specification and an abstraction of the environment.
How it differs: shields handle safety (LTL) properties over an MDP abstraction. Our gate handles normative and authority properties, and its guarantee is about *who may assert inputs*, not about the action's state-space safety. The pattern "untrusted learner proposes, verified component disposes" is the shield pattern.
Credit: **must credit.** The output gate and "LLM chooses only among allowed actions" are a post-posed or preemptive shield respectively. Say so explicitly.

**Ferrando et al. 2020, ROSMonitoring (TAROS); Luckcuck et al. 2019 survey (ACM CSUR)** (`ferrando2020rosmonitoring`, `luckcuck2019formal`).
What it does: ROSMonitoring generates runtime monitors from formal specifications that intercept ROS topic messages and can filter (block) violating messages. The survey maps formal specification and verification for autonomous robots, including runtime verification.
How it differs: these are generic RV infrastructure without a normative or authority semantics.
Credit: cite as the RV background. The output gate is an RV monitor with enforcement. Not a novelty threat, but expected.

## 6. LLM guardrails and LLM-driven robots

**NeMo Guardrails (Rebedea et al., EMNLP 2023 demos); Llama Guard (Inan et al. 2023); Constitutional AI (Bai et al. 2022)** (`rebedea2023nemo`, `inan2023llamaguard`, `bai2022constitutional`).
What they do: programmable dialogue rails (Colang) around an LLM, an LLM classifier for unsafe inputs and outputs, and training-time harmlessness from AI feedback against a written constitution.
How they differ: all three put the safety judgement *in a model* (a classifier or the policy model itself). The system's thesis is the opposite: models may propose and classify, but nothing a model emits can grant authority.
Credit: cite as the contrast class, with no novelty conflict. Note that the DEME veto gate, if any module is LLM-based, falls into this class. State which DEME modules are deterministic.

**SayCan (Ahn/Ichter et al., CoRL 2022)** (`ahn2022saycan`).
What it does: an LLM proposes skills and learned affordance (value) functions score feasibility. The robot executes the product.
How it differs: affordance filters on *feasibility*, not permissibility. "LLM chooses among a pre-filtered action set" structurally resembles our "LLM chooses among allowed actions".
Credit: cite as the origin of LLM selection over a constrained skill set.

**Yang, Raman, Shah & Tellex 2024, "Plug in the Safety Chip" (ICRA)** (`yang2024safetychip`).
What it does: translates natural-language constraints into LTL and enforces them over an LLM robot agent's plans via a monitor that blocks violating actions and re-prompts.
How it differs: the constraints concern physical and task safety, specified by the user. There is no authority or legitimacy model and no attestation.
Credit: **must credit.** It is "LLM robot + formal constraint checker that vetoes", the clearest robotics precedent for the output-gate pattern.

**Robey et al. 2025, "Jailbreaking LLM-Controlled Robots" (ICRA); Ravichandran et al. 2026, RoboGuard, "Safety Guardrails for LLM-Enabled Robots" (IEEE RA-L 11(4))** (`robey2025jailbreaking`, `ravichandran2026roboguard`).
What they do: RoboPAIR shows that LLM-controlled robots can be jailbroken into harmful physical actions. RoboGuard answers this with a two-stage guardrail: a "root-of-trust" LLM, shielded from user prompts, grounds predefined safety rules into temporal-logic specifications for the current scene, and a control-synthesis step then enforces them on the planner's output. Unsafe-plan execution dropped from about 92% to under 2.5–3%.
How they differ: RoboGuard still relies on an LLM (the root-of-trust) to instantiate the specification, so a model sits in the trust path. Our system's claim is that no model output enters the authority path at all. RoboGuard covers physical-harm rules, not consent, legitimacy, or escalation of authority.
Credit: **must credit both, prominently.** RoboGuard is the nearest LLM-robot guardrail architecture. The paper should contrast "trusted LLM grounds the spec" with "no LLM output can grant authority". Robey et al. supplies the threat model.

**Nakao & Takemoto 2026, LLM safety for robotic health-attendant control (R. Soc. Open Sci.)** (`nakao2026healthattendant`).
What it does: benchmarks 72 LLMs on 270 harmful instructions for a simulated health-attendant robot. The mean violation rate is 54.4%, with "emergency delay" and device manipulation hardest to refuse.
Credit: cite as empirical motivation that model-internal refusal is unreliable in exactly this domain. No novelty conflict.

## 7. Structural / capability-based containment of LLM agents

**Willison 2023, the dual-LLM pattern (blog)** (`willison2023dualllm`).
What it does: a privileged LLM holds tools but never sees untrusted text. A quarantined LLM reads untrusted text but has no tools and returns only opaque references.
How it relates: our perception-classifier LLM is effectively a quarantined LLM, since its outputs are events that cannot carry authority.
Credit: **must credit** as the origin of the idea. It is a blog post, so cite it as such.

**Debenedetti et al. 2026, CaMeL, "Defeating Prompt Injections by Design" (IEEE SaTML 2026, pp. 587–618)** (`debenedetti2026camel`).
What it does: extracts control and data flow from the trusted user query. A quarantined LLM handles untrusted data, a custom interpreter tracks provenance and capabilities on every value, and explicit security policies block flows. Security holds by construction even if the model is compromised.
How it differs: CaMeL operates in a digital tool-use setting and its trusted root is the *user's query*. Ours is embodied, the trusted root is *attested physical sensing*, and authority is graded (strata) rather than binary data-flow policy.
Credit: **must credit, prominently.** The core claim "an LLM cannot grant itself authority because provenance is tracked and checked outside the model" is CaMeL's design principle. The paper's novelty is transferring it to embodied care with physical attestation, multi-witness thresholds, and revocation on evidence lapse, not the principle itself.

**Beurer-Kellner et al. 2025, design patterns for securing LLM agents (arXiv)** (`beurerkellner2025patterns`).
What it does: catalogues provably injection-resistant agent patterns (action-selector, plan-then-execute, dual-LLM, code-then-execute, context-minimization).
How it relates: our "LLM chooses among allowed actions" is their **action-selector** pattern, almost verbatim.
Credit: **must credit.** Name the pattern.

**Shi et al. 2025, Progent (arXiv); Wang, Poskitt & Sun 2026, AgentSpec (ICSE '26)** (`shi2025progent`, `wang2026agentspec`).
What they do: deterministic, programmable privilege policies (Progent) and a DSL of trigger–predicate–enforcement rules (AgentSpec) checked on every LLM agent action. AgentSpec includes embodied-agent and autonomous-vehicle case studies.
Credit: cite as runtime-enforcement frameworks for LLM agents. AgentSpec in particular weakens any "first runtime rule language for LLM agents" claim.

**Dalrymple et al. 2024, "Towards Guaranteed Safe AI" (arXiv)** (`dalrymple2024guaranteed`).
What it does: proposes an architecture of world model + safety specification + verifier, with a gatekeeper that only lets verified actions through.
Credit: cite as the high-level framing the system instantiates in a narrow domain.

**Rashie & Rashi 2026, Lean 4 guardrails for financial agents (arXiv 2604.01483, unrefereed)** (`rashie2026typechecked`).
What it does: auto-formalizes compliance policies into Lean 4 and treats each proposed agent action as a conjecture to be proved before execution.
How it differs: Lean is used *at runtime per action*. Our Lean proofs are offline meta-theorems about the architecture (non-reachability of authority strata from model-classified events).
Credit: optional. Cite only if the paper says "Lean-verified LLM guardrail", to avoid a "first" claim. It is a weak preprint.

## 8. Care-robot ethics, consent, mandatory reporting

**Sharkey & Sharkey 2012, "Granny and the robots" (Ethics & IT)** (`sharkey2012granny`).
What it does: identifies the central eldercare robot risks: reduced human contact, objectification, **loss of privacy, loss of personal liberty (restraint)**, deception, and infantilization. It explicitly discusses robots restraining older people and when that could be justified.
Credit: **must credit.** The restraint threshold (3 witnesses) and the privacy metrics answer concerns this paper raised. Cite it in the motivation and map each metric to a risk it names.

**Sparrow & Sparrow 2006, "In the hands of machines?" (Minds & Machines)** (`sparrow2006hands`).
What it does: argues that robots cannot provide genuine care and that their use in aged care risks deception and neglect of emotional needs.
Credit: cite. The paper should concede that its system addresses the *authority and harm* problem, not the *care* problem Sparrow raises.

**Vandemeulebroucke, Dierckx de Casterlé & Gastmans 2018 (Arch. Gerontol. Geriatr.)** (`vandemeulebroucke2018care`).
What it does: a systematic review of argument-based ethics literature on care robots in aged care, covering autonomy, consent, privacy, and dignity.
Credit: cite as the consent and autonomy review.

**Mandatory reporting / elder abuse:** I searched and **found no robotics paper on care robots as mandatory reporters of elder abuse.** Non-robotics legal literature exists (e.g., a 2020 Temple Law Review article on carebots surfaced in search), but I did not read or verify it, and it is not in the .bib. If the paper claims to be the first to treat mandatory reporting in a robot's norm set, that claim is *not contradicted by anything I found*, but my search was shallow. Run a targeted search (Google Scholar: "care robot" "elder abuse" reporting) before stating it.

## 9. BPMN for robots

**Corradini et al. 2023, a BPMN-driven framework for multi-robot system development (RAS 160)** (`corradini2023bpmn`); BPMN 2.0 specification (`omg2011bpmn`).
What it does: models multi-robot missions as BPMN collaborations and executes them on ROS.
How it differs: it uses BPMN for mission orchestration, not escalation of human authority or interop with care-service workflows.
Credit: cite as the precedent for BPMN as robot process language. The escalation ladder's BPMN round-trip is an engineering choice, not a research claim. Do not over-sell it.

## 10. Trusted sensing / sensor attestation

**Liu, Saroiu, Wolman & Raj 2012, "Software abstractions for trusted sensors" (MobiSys)** (`liu2012trustedsensors`).
What it does: proposes two software abstractions for trusted sensors on mobile devices. In sensor attestation, each reading is signed with a TPM Attestation Identity Key so that a remote party can verify its authenticity and integrity. The authors implement a trusted GPS on x86 and ARM.
How it differs: there is no multi-witness quorum, no freshness or replay policy tied to authority, and no normative use.
Credit: **must credit** for "cryptographically signed sensor readings". The novelty is using attested readings as the *only* key to normative authority, with quorum thresholds and expiry. I did not do a thorough search of remote-attestation or IoT-attestation literature. A security reviewer may expect one or two more citations (e.g., a remote-attestation survey). Flagged, not added.

---

## Claims the prior art undercuts (summary)

1. **"Ethical governor"** as a term and an architecture: Arkin 2009, applied to care in Shim & Arkin 2017, and formally verified on a robot in Bremner et al. 2019. Do not claim the governor architecture, or a verified governor, as new.
2. **"Declarative defeasible care norms compiled for a robot"**: SLEEC (2023–2026), with runtime enforcement on an assistive robot in De Sanctis et al. 2026. The norm language alone is not novel.
3. **"The LLM cannot grant itself authority" / structural containment**: dual-LLM (2023), CaMeL (2025/2026), the action-selector pattern (2025). The principle is not novel. The embodied, sensor-attested, quorum-and-expiry version may be.
4. **"Formal guarantee about an LLM robot guardrail"**: RoboGuard (2026) and Safety Chip (2024) give LTL-based guarantees. Dennis et al. 2016 gives verified ethical choice. Phrase the Lean result narrowly, as non-reachability of authority strata from model-classified events.
5. **"Eldercare robot deciding when to escalate"**: Anderson et al. 2019.
6. **"Deontic runtime for LLM agents"**: AgenticRei (Joshi et al. 2026), and AgentSpec in a looser sense.

What I did **not** find in any prior work: authority elevation gated on a *quorum of attested physical sensor witnesses* (2 to elevate, 3 for restraint), rights that *revert when the evidence lapses*, and strata whose authority-granting gates are provably closed to model-originated events. The paper's defensible novelty is that combination, together with the care-ethics framing (restraint, privacy, consent) and the R0–R3 held-out evaluation. "Not found" reflects searches of a few hours, not a systematic review.

---

## AIES 2027

**Status as of 2026-10-03: no AIES 2027 call for papers is published.** The conference site (https://www.aies-conference.com/, checked 2026-10-03) lists only AIES 2026 and earlier editions, and a web search for an AIES 2027 CFP found none. **AIES 2027 dates, deadlines, and rules are unknown. Everything below is AIES 2026, reported as the best available proxy.**

AIES 2026 facts (source: https://www.aies-conference.com/2026/call-for-papers/, checked 2026-10-03; CFP PDF at https://www.aies-conference.com/2026/wp-content/uploads/2026/02/AIES-CFP-2026.pdf):

- **Conference:** October 12–14, 2026, Malmö, Sweden (home page describes it as the Ninth AAAI/ACM Conference on AI, Ethics, and Society).
- **Abstract registration:** May 14, 2026, 11:59 AoE.
- **Full paper submission:** May 21, 2026, 11:59 pm AoE.
- **Notification:** July 16, 2026.
- **Submission site:** EasyChair (https://easychair.org/conferences/?conf=aies26).
- **Page limit:** at most 10 pages including figures and tables. Unlimited pages for non-discursive references.
- **Template:** the 2-column style of the **AAAI-2026 Author Kit** (https://aaai.org/authorkit26-1/). It is AAAI style, not ACM.
- **Optional statements:** ethical considerations, researcher positionality, and adverse impact statements may go on one extra page at the end, before the references, which does not count toward the limit.
- **Anonymity:** review is doubly anonymized. Remove identifying information.
- **Prior publication:** papers must not be published or accepted at an archival conference or journal before submission. Preprints (arXiv, SSRN) are allowed. Extensions of formally published workshop papers need "substantial new content".
- **Non-archival option:** accepted papers may appear as a one-page abstract plus a URL to the full paper.
- **Appendices:** may be submitted separately. Reviewers are not required to read them.
- **Generative-AI policy:** "Papers that include text generated from a large-scale language model (LLM) such as ChatGPT are prohibited unless the produced text is presented as a part of the paper's experimental analysis." Using an LLM to edit author-written text is permitted. AI systems cannot be authors or cited sources.

Implications if 2027 follows 2026 (an assumption, not a fact):
- Plan for a May 2027 deadline and the AAAI-2027 author kit.
- Double-blind review conflicts with self-citation of Geometric Ethics, ErisML, and DEME. Cite them in the third person and do not link to the author's GitHub in the submission.
- **The LLM-text prohibition matters for this paper.** Any prose drafted by Claude would have to be rewritten by the author, since editing author-written text is allowed but generated text is not. Verify the 2027 wording when the CFP appears.

Re-check https://www.aies-conference.com/ for the 2027 call. Based on 2026, it would be expected around February 2027, but that is an inference.
