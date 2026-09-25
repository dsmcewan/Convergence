# Convergence — Engineering Portfolio Brief

> **Hiring-manager path:** Convergence is the evidence-synthesis / explainability project in this portfolio. The main README documents the product; this page explains the engineering signal quickly.

## What it solves

Convergence is a deterministic communication-forensics and evidence-synthesis engine. It analyzes written records through six independent analytical layers and refuses to elevate a finding unless different mechanisms corroborate the same material.

The governing rule is:

> **An assertion cannot supply the evidence required to promote itself.**

Language models may explain structured findings. They do not determine verdicts.

## Why the architecture is different

A common AI-analysis pattern is:

```text
corpus → model → conclusion + confidence score
```

That leaves the same probabilistic component generating the claim, interpreting the evidence, and grading its own result.

Convergence instead uses six deterministic detectors that normalize to a common `Signal` model. Each signal retains the message material that produced it, and different layers have different evidentiary permissions.

## Evidence-promotion architecture

```text
fragment
   ↓ contextual match
tactic / Signal
   ↓ independent-layer corroboration
Finding
   ↓ named composition or recurrence
Pattern
   ↓ actor + target + time attribution
Campaign
```

Each arrow has a separate rule. The kind of claim changes only when the evidence burden for the next level is met.

### Evidentiary roles

- **Substantive:** L1 tactic, L2 omission, L3 contradiction, L6 cross-channel divergence.
- **Corroborator-only:** L4 domain convergence can strengthen an existing group but cannot create or merge findings.
- **Focal/contextual:** L5 register shift can bridge related material but cannot elevate a context-only group.

A finding becomes `elevated` only with **at least one substantive layer and at least two distinct layers total**. Lone signals remain low.

## Higher-order structure

`composition.py` operates above event-level findings:

- **Patterns** identify named tactic combinations or recurring substantive moves.
- **Campaigns** require multiple elevated findings attributable to the same actor against the same target over time.
- `coercion_grammar.py` separately tests ordered/cyclic structure and only completes when the full envelope is present; isolated stages do not inherit the higher-order conclusion.

This is not model voting. It is **evidence promotion through independent mechanisms, recurrence, attribution, and sequence**.

## Agent boundary

Convergence uses agents only where open-ended generation is useful. `investigator.py` can accept proposed detector families, but deterministic evaluation decides whether they ship. Candidate detectors must fire on target corpora while remaining quiet on defined benign corpora.

That preserves the same rule used by the core engine: **the proposer does not grade the proposal.**

## Proof points in the repository

- **272 deterministic tests** in the documented run path.
- Core engine is **standard-library only**; LLM integrations are optional adapters.
- Six detector modules feed one normalized signal representation.
- Synthetic discriminator evaluation explicitly labels its perfect score as synthetic-only and keeps a high-conflict corpus as a hard negative.
- Real-data evaluation uses documentary precision without pretending an incomplete evidence set provides recall ground truth.
- Optional Claude, OpenAI, Grok, Gemini, and CLI backends are isolated from the verdict path.

## Best code-review entry points

| Area | Start here |
| --- | --- |
| Signal normalization + convergence rule | `convergence/engine.py` |
| Patterns and campaigns | `convergence/composition.py` |
| Ordered structural grammar | `convergence/coercion_grammar.py` |
| Detector proposal / deterministic acceptance | `convergence/investigator.py` |
| Evaluation | `convergence/evaluation.py` |
| Grounded conversational seam | `convergence/conversation.py` |
| Promotion rules | `HIERARCHY.md` |
| Engineering rationale | `ENGINEERING.md` |

## What this demonstrates to an employer

Convergence is evidence of work in:

- deterministic AI-system design
- evidence fusion and provenance
- explainable analytical pipelines
- false-positive controls
- hierarchical and temporal reasoning
- adversarial evaluation
- provider abstraction
- corpus/data modeling
- test-driven implementation
- productizing a technical method as CLI, web output, Docker deployment, and grounded Q&A

## Relevant roles

AI Systems Engineer · Applied AI Engineer · Forward-Deployed Engineer · AI Evaluation / Assurance Engineer · Trust & Safety Engineer · Evidence / Investigation Platform Engineer

## Portfolio connection

**Convergence asks when evidence has earned a finding. TELOS asks when evidence has earned authority.** Both keep generation useful while making promotion depend on independently checkable structure.
