# Holistic AI Public Output Scan — 2025-05 to 2026-05

Codex-driven scan of holisticai.com (papers/blog/press-release). Date: 2026-05-08.

## Bottom line

**No direct collision with LVD.** HAI is heavily in agentic safety + red-teaming + runtime governance. They do not appear to have any public work explicitly framing "transparent role separation" or "lens–voice divergence" as a construct. The framing in `notes/repositioning_v1.md` ("transparent role separation diagnostic, complementary to concealment-based red-teaming") is independently validated by this scan as the correct positioning.

## High-relevance items (must cite or differentiate from)

| Item | Date | Why it matters | Treatment |
|---|---|---|---|
| **CorrSteer** — sparse-autoencoder feature selection for reasoning-trace attacks | 2025-08-18 | Mechanistic defense for the same failure surface LVD probes behaviourally | Cite if §9 mechanistic extension is pursued; complementary, not competing |
| **Mind the Gap / AgentSeer** — model-level vs agentic-level vulnerabilities | 2025-09-05 | Establishes that agent-level red-teaming surfaces failures single-turn evals miss | Cite as adjacent: LVD operates *one level below* AgentSeer (single-turn, no agency) and tests for failures their layer misses |
| **Red Teaming Chinese Open Models** — DeepSeek / Qwen / Kimi / MiniMax with role-play + movie-scene jailbreak | 2025-11-13 | Closest existing HAI work on the same model set + role-play methodology | **Differentiate explicitly:** their role-play is concealment (movie-scene fiction); LVD is transparent (user states the role split openly). No harmful-output target in LVD |
| **Runtime Agentic Enforcement** — separating "what agent says" from "what agent does" | 2026-04-16 | Compliance-Gap-adjacent framing in HAI's own vocabulary | Useful to cite when positioning LVD vs Compliance Gap |

## Medium-relevance (cite if relevant, otherwise note)

CorrSteer family (Aug 2025), AgentGraph (Oct 2025), Great Agent Hack (Nov 2025), Bias Amplification (May 2025), MPF (Jul 2025), Grok 4 governance post (Jul 2025), LLM Decision Hub (Sep 2025), AI-governing-AI (Jan 2026), Gartner Guardian Agent Guide (Mar 2026), AI-That-Governs-AI (Apr 2026), Programmable Controls (May 2026).

## Low-relevance / unrelated

LibVulnWatch (open-source library audit), Don't Throw Good Agents After Bad (governance), Shadow AI Discovery (asset discovery).

## Recommended framing adjustments before talking to 学长

1. **Lead with complementarity, not competition.** HAI has invested heavily in agentic-level red-teaming (AgentSeer, AgentGraph, Runtime Enforcement). LVD is single-turn, no agency, no tool use. Position it as the layer that isolates the reasoning–output coherence question their agent-level evals don't directly probe.

2. **Acknowledge the role-play overlap upfront.** Their "Red Teaming Chinese Open Models" used role-play / movie-scene jailbreaks on DeepSeek + Qwen. The differentiator: LVD prompts are transparent (no fiction wrapper, no harmful-content target) and the DV is mismatch recognition, not ASR.

3. **CorrSteer is a potential co-author topic if §9 is pursued.** If the optional mechanistic extension goes ahead, CorrSteer's SAE-based feature selection is the closest existing HAI work. Worth flagging proactively to 学长.

4. **Avoid "jailbreak benchmark" framing entirely.** If 学长 hears "another jailbreak eval," collision risk with their existing red-teaming portfolio is HIGH. Lead instead with "concealment-free diagnostic for reasoning-output coherence — sits one level below agent-level audit."

## Action items

- [x] Update `docs/brief_for_holistic_ai.md` to incorporate complementarity framing and acknowledge AgentSeer / CorrSteer / Red-Teaming-Chinese-Models upfront.
- [ ] When 学长 conversation happens, ask specifically: "Has HAI considered tests for reasoning–output coherence at the single-turn level, or does AgentSeer cover that territory?"
- [ ] If §9 mechanistic extension is greenlit, treat CorrSteer as the closest prior work and consider reaching out for collaboration.
