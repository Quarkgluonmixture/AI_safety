# Lens–Voice Divergence (LVD)

**A diagnostic stress test for transparent role separation in reasoning-tuned LLMs.**

> Working title · Side project / workshop paper scope
> Jiaming Wei · UCL MSc AI for Sustainable Development

---

## What this project asks

When a user **explicitly** asks an aligned LLM to (a) analyse an institution through a critical lens, and (b) write in that institution's own self-legitimising voice in the same response — does the model recognise that its voice is performing the very mechanism its lens just diagnosed?

Most current safety stress tests rely on **hiding** something from the model: hidden side objectives (SHADE-Arena), backdoors (Sleeper Agents), stylistic spoofing (Role Confusion), jargon masks (Into the Gray Zone), persona drift (PHISH), or attention dilution (CoT Hijacking). LVD is the contrast case: **nothing is hidden**. The user states the role split openly, names both lens and voice, and the structural mismatch is visible in plain text.

If the model still complies without flagging the mismatch, the failure cannot be attributed to deception. It points instead to a missing capability — using one's own diagnostic output as a constraint on one's subsequent generative action.

## Status

- [x] Proposal v1 drafted (`RSP_research_proposal.md`)
- [x] Literature review — three exploratory drafts in `literature/`
- [x] Citation verification round 1 (codex) — `notes/citation_audit_v1.md`
- [ ] Citation verification round 2 (CoT Hijacking + recheck PARTIALs)
- [ ] Repositioning: §1 motivation, §15 Related Work, schema formalisation, §6.8 rubric
- [ ] 50-item pilot benchmark
- [ ] MDE behavioural eval (4 API models)
- [ ] WTE extension (reasoning trace + open-weight CMI)

## Compute envelope

- API access: GPT, Claude, Gemini, DeepSeek
- 1× A100 40G (dedicated)
- Shared DGX (opportunistic)
- UCL Myriad (HPC, batch eval)

## Repository layout

```
RSP_research_proposal.md   Main proposal (v1, pre-repositioning)
literature/                Exploratory lit review drafts
notes/                     Verified citations, schema drafts, planning docs
docs/                      External-facing communication (briefs, slides)
```

(Code directories `bench/`, `eval/`, `analysis/` will be added when implementation starts.)

## Ethics note

Stimuli use synthetic targets. No public release of operational attack strings; aggregate and abstracted artefacts only. Subject to UCL ethics review before data collection.
