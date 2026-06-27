# Engineering principles & alignment

This project is a deliberate exercise in **using the simplest mechanism that works**.
Anthropic's [*Building effective agents*](https://www.anthropic.com/engineering)
argues for exactly this: reach for deterministic code first, workflows next, and an
autonomous agent only when the task genuinely needs one. This engine is a worked
example of that judgment — the verdict is 100% deterministic, and the LLM is
load-bearing nowhere a decision is made.

## The core decisions

1. **Deterministic detection, not a model.** Fragments → tactics → findings →
   patterns → campaigns are pure functions over message structure. The same input
   always yields the same output; tests run twice are byte-identical. A forensic
   tool's value is *provenance* — every signal traces to a named fragment in a named
   file — which a probabilistic classifier cannot give.
2. **The model sits at a narrow, grounded seam.** `conversation.py` receives only the
   *structured findings*, never the raw corpus or the detection logic, via an injected
   `complete()`. The model can rephrase or explain a verdict; it cannot move one. The
   SDK is touched in exactly one file (`adapters/`).
3. **Evals are first-class.** 100+ deterministic tests, a five-corpus discrimination
   eval, doc-sync guards that fail on drift, and a scored report
   (`demo.py --eval`). "It works" is replaced by numbers.
4. **Docs are checked artifacts.** `FRAGMENTS.md`, `INTENT.md`, `HIERARCHY.md`,
   `DYNAMICS.md` each have a test that fails if the doc drifts from the code.

## Alignment with the Anthropic engineering body of work

*Already embodied:*

| Principle | Where |
|---|---|
| Building effective agents — simplest mechanism first | the entire deterministic core; no agent where code suffices |
| Demystifying / AI-resistant evals | `evaluation.py`, the discrimination suite, synthetic held-out corpora, structural (not lexical) discriminator |
| Quantifying eval noise | zero noise — seeded generator, twice-identical tests |
| Effective context engineering | `conversation.py` passes minimal high-signal context (findings only) |
| Writing effective tools | small, composable, single-purpose pure functions per layer |

*Applies only with an agentic layer (see below):* managed-agent decoupling, advanced
tool use, code execution with MCP, Agent Skills, multi-agent research systems,
long-running harnesses.

*Not applicable* (Claude-product / infra / model-internals): containment across
products, Code quality reports, permission modes, eval-awareness, SWE-bench,
Contextual Retrieval, Desktop Extensions.

## The one place an agent is justified — and it's built

The detector had known blind spots — the *conflicted* corpus carries triangulation-
through-child and derogation-via-attribution that no fragment family caught. Closing
those is open-ended research, so it is where an agent earns its place. The
**investigator** (`convergence/investigator.py`) implements *multi-agent research
system* + *writing effective tools*: agents PROPOSE candidate fragment families; a
deterministic verifier DECIDES which ship, by adversarially testing each against the
labeled corpora (fires on target, silent on the benign corpora).

Result of the live run (6 parallel proposer agents):

| Source | Proposed | Shipped | Rejected |
|---|---|---|---|
| seed | triangulation, derogation, access_gatekeeping | triangulation, derogation | access_gatekeeping (1 hit) |
| 6 agents | isolation, surveillance_framing, conditional_threat, financial_leverage, love_bombing, stonewalling | isolation, surveillance_framing | conditional_threat, financial_leverage, love_bombing, stonewalling |

The shipped survivors live in `convergence/behaviors.py`. The decisive case:
**`conditional_threat`'s own rationale claimed it was verified to fire — the
deterministic verifier found it matched nothing in the real corpora and rejected
it.** The agent never moves a verdict: it proposes *detectors*; deterministic code
decides what is real. Footprints, not the foot — preserved even at the agentic layer.

Try it: `demo.py --investigate`.
