# Convergence — Engineering Portfolio Brief

## What I built

Convergence is a deterministic communication-forensics and evidence-synthesis engine. It analyzes written records through six independent analytical layers and refuses to elevate a finding unless independent forms of evidence corroborate the same material.

The core design principle is simple:

> **An assertion cannot supply the evidence required to promote itself.**

Language models may explain structured findings, but they do not determine verdicts.

## The engineering problem

Many AI analysis systems ask a model to inspect a corpus and return a conclusion with a confidence score. That creates a difficult verification problem: the same probabilistic component generates the claim, interprets the evidence, and grades its own result.

Convergence separates those responsibilities.

Six deterministic detectors emit a common `Signal` representation. Signals have different evidentiary roles: substantive signals represent actual moves; contextual signals may strengthen or connect evidence but cannot independently manufacture a high-confidence finding. The engine promotes a finding only when at least one substantive signal is corroborated by a second independent layer.

This makes confidence a property of **independent evidence structure**, not model certainty.

## Architecture at a glance

```text
raw records
    ↓
independent deterministic detectors (L1–L6)
    ↓
normalized Signals
    ↓
independent-layer corroboration
    ↓
Findings
    ↓
recurrence / named composition
    ↓
Patterns
    ↓
actor + target + time attribution
    ↓
Campaigns
```

A separate ordered grammar can identify higher-order temporal structures only when the complete sequence is present. Individual stages do not inherit the conclusion of the complete pattern.

## What this demonstrates

- **AI systems architecture** — probabilistic models are kept behind a narrow explanatory seam rather than placed in the verdict path.
- **Deterministic validation** — findings are promoted by explicit, testable rules.
- **Evidence fusion** — heterogeneous analytical layers normalize to a common signal model while retaining provenance.
- **False-positive control** — contextual signals cannot independently elevate findings; lone signals remain low confidence.
- **Hierarchical inference** — fragments become tactics, tactics become corroborated findings, findings compose into patterns, and sustained attributed findings become campaigns.
- **Temporal / structural reasoning** — ordered grammars distinguish isolated events from complete behavioral sequences.
- **Extensible detector research** — agent-proposed detector families are treated as untrusted candidates and must pass deterministic adversarial checks before shipping.
- **Provider abstraction** — optional Claude, OpenAI, Grok, Gemini, and CLI adapters are isolated from the dependency-free core.
- **Evaluation discipline** — synthetic labeled discrimination is kept separate from real-data documentary precision so metrics do not claim more than the available ground truth supports.
- **Product engineering** — CLI, static build, web presentation, Docker deployment, grounded conversational explanation, and automated tests surround the core engine.

## Code worth reviewing

| Area | File | Why it matters |
|---|---|---|
| Evidence convergence | `convergence/engine.py` | Normalizes signals, constructs evidence groups, and enforces the independent-layer elevation rule. |
| Higher-order composition | `convergence/composition.py` | Promotes corroborated events into recurring patterns and actor/target/time campaigns. |
| Ordered structural analysis | `convergence/coercion_grammar.py` | Recognizes a complete cyclic/temporal envelope rather than classifying isolated phrases. |
| Detector research | `convergence/investigator.py` | Separates agent proposal from deterministic acceptance testing. |
| Evaluation | `convergence/evaluation.py` | Keeps synthetic discriminator metrics distinct from documentary corroboration on real records. |
| Model boundary | `convergence/conversation.py` | Lets an LLM explain fixed structured findings without changing them. |
| Architecture | `HIERARCHY.md` | Documents the promotion rules from tactic → finding → pattern → campaign. |
| Engineering rationale | `ENGINEERING.md` | Explains deterministic-over-agentic design decisions and evaluation strategy. |

## The unusual part

Convergence is not an ensemble-voting system.

Several models agreeing is still potentially one correlated failure mode. Convergence instead asks whether **different analytical mechanisms independently produce compatible evidence**, and then changes the kind of claim it is willing to make as evidence survives successive promotion rules.

```text
observation ≠ finding
finding ≠ pattern
pattern ≠ sustained campaign
```

Each transition has a separate burden of proof.

## Relevant roles

This project is representative of work in:

- AI Systems Engineering
- Applied AI / Generative AI Engineering
- AI Evaluation and Verification
- Forward-Deployed Engineering
- AI Governance and Assurance
- Evidence / Investigation Platforms
- Trust & Safety Engineering
- Technical Product Incubation

## Design philosophy

Convergence is one implementation of a broader systems principle I use across AI projects:

> **Generation may propose. Promotion requires independent evidence.**

That same principle appears in TELOS, where independently attributable review and deterministic verification govern when proposed AI-mediated work earns implementation authority.