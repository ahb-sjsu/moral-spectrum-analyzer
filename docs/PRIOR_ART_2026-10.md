# Prior art: monitoring internal representations, and containing LLM-driven robots

Scan of 2026-10-02, for docs/PREREG_IEIP_TWIN.md and docs/AUTONOMY_PLAN.md. Each entry was
checked against a search result or a fetched abstract page during the scan; several are 2026
arXiv preprints, recent and not peer reviewed. Absence below means "not found in this scan", not
"does not exist".

## 1. Monitoring internal representations for consistency or invariance

**Consistency rules on activations, and their failure**
- Burns et al., Discovering Latent Knowledge in Language Models Without Supervision (CCS), ICLR 2023. https://arxiv.org/abs/2212.03827. A truth direction from one consistency rule (a statement and its negation take opposite values).
- Farquhar et al., Challenges with unsupervised LLM knowledge discovery, arXiv:2312.10029. https://arxiv.org/abs/2312.10029. Negative: arbitrary features satisfy the CCS rule, so it finds the most prominent feature, not knowledge.
- ARC, Eliciting Latent Knowledge (2021). https://www.alignment.org/blog/arcs-first-technical-report-eliciting-latent-knowledge/

**Truth and lie probes, and generalization**
- Marks & Tegmark, The Geometry of Truth, arXiv:2310.06824. https://arxiv.org/abs/2310.06824
- Bürger et al., Truth is Universal, arXiv:2407.12831. https://arxiv.org/abs/2407.12831
- Bao et al., Probing the Geometry of Truth, Findings of ACL 2025, arXiv:2506.00823. https://arxiv.org/abs/2506.00823
- Levinstein & Herrmann, Still no lie detector for language models, Philosophical Studies 2025. https://link.springer.com/article/10.1007/s11098-023-02094-3. Negative.
- Goldowsky-Dill et al., Detecting Strategic Deception Using Linear Probes, arXiv:2502.03407. https://arxiv.org/abs/2502.03407
- Kretschmar et al., Liars' Bench, arXiv:2511.16035. https://arxiv.org/abs/2511.16035. Negative: white- and black-box detectors miss whole kinds of lies.
- Yoo et al., Probe Generalization as Subspace Selection for OOD Deception Detection, arXiv:2609.02893. https://arxiv.org/abs/2609.02893

**Uncertainty and out-of-distribution signals in hidden states**
- Lee et al., Mahalanobis OOD detection, NeurIPS 2018. https://proceedings.neurips.cc/paper/2018/hash/abdeb6f575ac5c6676b747bca8d09cc2-Abstract.html
- Chen et al., INSIDE (EigenScore), ICLR 2024, arXiv:2402.03744. https://arxiv.org/abs/2402.03744
- Kossen et al., Semantic Entropy Probes, arXiv:2406.15927. https://arxiv.org/abs/2406.15927

**Equivariance and invariance of representations**
- Lenc & Vedaldi, Understanding Image Representations by Measuring Their Equivariance and Equivalence, CVPR 2015. https://openaccess.thecvf.com/content_cvpr_2015/html/Lenc_Understanding_Image_Representations_2015_CVPR_paper.html. The same form h(g·x) ≈ rho(g) h(x), on vision CNNs under geometric transforms, not as a runtime gate.
- Kornblith et al., Similarity of Neural Network Representations Revisited (CKA), ICML 2019. https://arxiv.org/abs/1905.00414
- Invariant Reasoning Directions in Latent Trajectories of Language Models, arXiv:2606.29164. https://arxiv.org/html/2606.29164
- de Zarzà et al., Semantic Invariance in Agentic AI, arXiv:2603.13173. https://arxiv.org/abs/2603.13173. Metamorphic testing on outputs only.

**White-box monitors in AI control, and attacks on them**
- McKenzie et al., Detecting High-Stakes Interactions with Activation Probes, NeurIPS 2025. https://arxiv.org/abs/2506.10805
- Bailey et al., Obfuscated Activations Bypass LLM Latent-Space Defenses, arXiv:2412.09565. https://arxiv.org/abs/2412.09565. Negative: probes and latent OOD detectors can be evaded.
- Zou et al., Representation Engineering, arXiv:2310.01405. https://arxiv.org/abs/2310.01405

## 2. Containing LLM-driven robots and agents

**Robot guardrails**
- Ravichandran et al., Safety Guardrails for LLM-Enabled Robots (RoboGuard), arXiv:2503.07885. https://arxiv.org/abs/2503.07885. A root-of-trust LLM grounds rules into LTL, then control synthesis.
- Yang et al., Plug in the Safety Chip, arXiv:2309.09919. https://arxiv.org/abs/2309.09919
- Yin et al., SafeAgentBench, arXiv:2412.13178. https://arxiv.org/abs/2412.13178
- Ranathunga et al., When Agents Control Robots: A Zero Trust Policy Model, arXiv:2605.25653. https://arxiv.org/abs/2605.25653

**Shielding and runtime assurance**
- Alshiekh et al., Safe Reinforcement Learning via Shielding, AAAI 2018. https://ojs.aaai.org/index.php/AAAI/article/view/11797
- Sha, Using simplicity to control complexity (Simplex), IEEE Software 2001; Black-Box Simplex, arXiv:2102.12981. https://arxiv.org/abs/2102.12981
- Arkin, Governing Lethal Behavior in Autonomous Robots (the ethical governor). https://www.routledge.com/Governing-Lethal-Behavior-in-Autonomous-Robots/Arkin/p/book/9781420085945

**AI control and guaranteed safety**
- Greenblatt et al., AI Control: Improving Safety Despite Intentional Subversion, arXiv:2312.06942. https://arxiv.org/abs/2312.06942
- Dalrymple et al., Towards Guaranteed Safe AI, arXiv:2405.06624. https://arxiv.org/abs/2405.06624

**Policy enforcement and formal verification of agents**
- Wang, Poskitt & Sun, AgentSpec, ICSE 2026. https://arxiv.org/abs/2503.18666
- Chen, Kang & Li, ShieldAgent, arXiv:2503.22738. https://arxiv.org/abs/2503.22738
- Wang et al., Lean4Agent, arXiv:2606.06523. https://arxiv.org/abs/2606.06523
- Koomullil, Proof-Carrying Certificates for LLM Pipelines, arXiv:2605.16407. https://arxiv.org/abs/2605.16407. Lean 4 proofs about the deterministic code around the LLM.

**Information-flow control by design**
- Willison, The Dual LLM pattern (2023). https://simonwillison.net/2023/Apr/25/dual-llm-pattern/
- Debenedetti et al., Defeating Prompt Injections by Design (CaMeL), arXiv:2503.18813. https://arxiv.org/abs/2503.18813
- Costa et al., Securing AI Agents with Information-Flow Control (FIDES), arXiv:2505.23643. https://arxiv.org/abs/2505.23643
- Beurer-Kellner et al., Design Patterns for Securing LLM Agents against Prompt Injections, arXiv:2506.08837. https://arxiv.org/abs/2506.08837

**Attestation, care robots, governance**
- Ghaeini et al., PAtt: Physics-based Attestation of Control Systems, RAID 2019. https://www.usenix.org/system/files/raid2019-ghaeini.pdf
- Yang et al., Medical robotics: regulatory, ethical and legal considerations for increasing levels of autonomy, Science Robotics. https://www.science.org/doi/10.1126/scirobotics.aam8638
- Redefining Elderly Care with Agentic AI, arXiv:2507.14912. https://arxiv.org/abs/2507.14912
- Eide et al., ARC: Autonomous Robotics Compliance, arXiv:2609.12932. https://arxiv.org/abs/2609.12932

**Stratified or gauge-theoretic ethics:** none found outside the owner's own work.

## 3. What bears on this project

- **For I-EIP (PREREG_IEIP_TWIN.md):** Farquhar et al. is the threat to answer. A consistency rule
  can be satisfied by features that have nothing to do with correctness, so an equivariance error
  that predicts errors needs controls, which the registered null transform (g0) and the
  output-invariance comparison (H2) partly provide. Bailey et al. show activation monitors can be
  evaded, which fits the twin's use of I-EIP as a cautious-path trigger, never as authority.
- **For containment:** RoboGuard and the Safety Chip gate an LLM robot with temporal-logic rules
  but still trust a model to ground the rules, and neither requires attested physical evidence.
  CaMeL and FIDES make tool permissions structurally independent of untrusted model content, the
  closest relative of the twin's Lean result, but for data flow rather than physical action.
  Proof-carrying certificates and Lean4Agent prove properties of the code around a model, as
  formal/twin-containment does.
- **Possibly open:** a runtime monitor testing a learned rho on LLM hidden states under
  meaning-preserving rewrites; several attested physical witnesses as a precondition for an LLM
  robot's actions; a machine-checked proof that an embodied care robot's permissions are
  independent of model outputs; stratified spaces in machine ethics. Each is a hedged observation
  from one scan.
