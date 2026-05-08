# Citation Audit v1

Two-round verification (codex web-fetch + arXiv/OpenReview cross-check) of citations referenced across `RSP_research_proposal.md` and `literature/`. Audit dates: 2026-05-08.

**Bottom line:** the lit-review file `literature/Lens–Voice Divergence A Role-Separated Stress Test for Superficial Alignment in Reasoning-Tuned LLMs.md` contained a substantial number of fabricated or mis-attributed citations (typical LLM-survey hallucination). Two rounds of verification have produced a clean usable subset.

---

## Verified citations — safe to use

| Key | arXiv ID | Title | Authors | Venue / status | Notes |
|---|---|---|---|---|---|
| `kutasov2025shadearena` | 2506.15740 | SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents | Jonathan Kutasov, Yuqi Sun, Paul Colognese, et al. | Anthropic Research; arXiv preprint | No formal conference venue confirmed; cite as Anthropic 2025 |
| `shin2026compliancegap` | 2605.01771 | The Compliance Gap: Why AI Systems Promise to Follow Process Instructions but Don't | Kwan Soo Shin (single author) | arXiv preprint; submitted to NeurIPS 2026 ED Track | Theorem 1 / 2 confirmed; VCR/ACR formalisation present |
| `ye2026roleconfusion` | 2603.12277 | Prompt Injection as Role Confusion | Charles Ye, Jasmine Cui, Dylan Hadfield-Menell | ICML 2026 Poster | role-probe finding; ICML downloads page lists it |
| `hubinger2024sleeper` | 2401.05566 | Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training | Evan Hubinger et al. | Anthropic 2024 | – |
| `wallace2024instruction` | 2404.13208 | The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions | Eric Wallace et al. | arXiv preprint | – |
| `shen2024dan` | 2308.03825 | "Do Anything Now": Characterizing and Evaluating In-The-Wild Jailbreak Prompts on Large Language Models | Xinyue Shen et al. | – | – |
| `wang2026beyondcontent` | 2603.25412 | Beyond Content Safety: Real-Time Monitoring for Reasoning Vulnerabilities in Large Language Models | Xunguang Wang et al. | arXiv preprint | – |
| `liu2026beyondrefusals` | OpenReview 9146 | Beyond Refusals: Fine-grained Safety Alignment for Reasoning LLMs | Zhendong Liu et al. | OpenReview submission | CMI-loss + shortcut alignment formalism |
| `li2026ssah` | 2410.10862 | Superficial Safety Alignment Hypothesis | Jianwei Li, Jung-Eun Kim | ICLR 2026 Poster (OpenReview 9yS40pO1RF) | **Note: not Zhou et al. as miscited in lit file #2** |
| `zhao2025cothijack` | 2510.26418 | Chain-of-Thought Hijacking | Jianli Zhao, Tingchen Fu, Rylan Schaeffer, et al. | arXiv preprint; ICLR 2026 desk-rejected | Authors confirmed; cite as preprint |
| `hung2026graytone` | 2604.15717 | Into the Gray Zone: Domain Contexts Can Blur LLM Safety Boundaries | Ki Sen Hung, Xi Yang, Chang Liu, et al. | arXiv preprint; per arXiv comments → ACL 2026 Main | "Jargon" is the framework name in-paper, not the paper title |
| `sandhan2026phish` | 2601.16466 | Persona Jailbreaking in Large Language Models | Jivnesh Sandhan et al. | EACL 2026 Findings | PHISH = Persona Hijacking via Implicit Steering in History (in-paper framework name) |
| `collu2023jekyll` | 2312.03853 | Dr. Jekyll and Mr. Hyde: Two Faces of LLMs | Matteo Gioele Collu et al. | arXiv preprint | **Note: not Rando et al. as miscited in lit file #2** |
| `xiao2026safestyle` | OpenReview a8QTAl5Hnb | When Style Breaks Safety: Defending LLMs Against Superficial Style Alignment | Yuxin Xiao et al. | OpenReview submission | "SafeStyle" is the method name |
| `akbulut2026manipulation` | 2603.25326 | Evaluating Language Models for Harmful Manipulation | Canfer Akbulut et al. (incl. Laura Weidinger) | arXiv preprint | Replaces the bogus ResearchGate ID |

## Discarded — fabricated or unverifiable

| Original claim | Issue |
|---|---|
| arXiv:2605.05678 — "Chain of Risk: Safety Failures in Large Reasoning Models..." (Anonymous 2026) | **Does not exist.** Multiple sections of `literature/...Stress Test...md` cited this as a primary anchor; remove all references. |
| arXiv:2604.17023 — "Agentic Disinformation: Scaling Propaganda Operations via LLM-based Multi-Agent Systems" (Barman et al.) | ID points to an unrelated paper ("The Instrumental Dissolution of Typing"). |
| arXiv:2310.01234 — "Personas as a Way to Model Truthfulness in Language Models" (Rando et al.) | ID points to an optics/metasurface paper. |
| ResearchGate publication 398225449 — "Evaluating Harmful AI Manipulation via Context-Specific Human-AI Interaction Studies" (Weidinger et al.) | ID does not resolve. Same-topic paper exists at arXiv:2603.25326 (Akbulut et al., included above). |

## Mis-attribution corrections (compared to BibTeX in `literature/...Stress Test...md`)

| Correct | Was miscited as |
|---|---|
| Li & Kim (SSAH) | "Zhou et al." |
| Collu et al. (Dr. Jekyll & Hyde) | "Rando et al." |
| Hung et al. ("Into the Gray Zone") | "Mustafa et al." |
| Single-author Kwan Soo Shin (Compliance Gap) | not credited at all in lit file BibTeX |

## Things to redo if discrepancies arise

- ACL 2026 Main acceptance for Hung et al. is currently per arXiv comments only; re-verify after ACL Anthology publishes.
- SHADE-Arena: cite as Anthropic 2025 / arXiv; do not claim a venue beyond that.
- CoT Hijacking is desk-rejected from ICLR 2026 — cite as arXiv preprint; do not claim conference acceptance.

## Action items propagated from this audit

1. `literature/...Stress Test....md`: substantial rewrite needed — remove all "Chain of Risk" anchors, fix author attributions, retitle "Jargon" / "PHISH" to actual paper titles. **(Defer until paper writing phase; don't rewrite now.)**
2. `RSP_research_proposal.md` §15: replace single-paragraph related work with the differentiation table in `notes/repositioning_v1.md`.
3. `notes/repositioning_v1.md`: keep current text; all in-text citations are now consistent with this audit.
