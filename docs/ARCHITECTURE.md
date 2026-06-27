# Architecture

`convergence` is a pipeline of independent **layers** that each emit **signals**, an **engine**
that combines signals into a **convergence verdict**, and a **narration** surface that explains
the verdict without being able to change it.

```
corpus + (optional) exhibit + (optional) records
        │
        ▼
   ┌─────────────── layers (each independent, deterministic) ───────────────┐
   │ L1 pattern_detector   L2 gap_detector   L3 third_party                  │
   │ L4 domain_convergence L5 phrase_fragmentation                          │
   └────────────────────────────────┬───────────────────────────────────────┘
        every layer output → a common Signal(layer, seqs, kind, detail)
        │
        ▼
   engine.run_engine()  ── group signals · apply the convergence rule ──▶ EngineResult(findings)
        │
        ▼
   narration.narrate()  (deterministic)   ·   conversation.Conversation (LLM seam, optional)
```

## Data model (`corpus.py`, `records.py`)

- `Message(seq, thread, sender, timestamp, domain, body)` — one message. `seq` is the monotonic
  position in the *complete* record; `thread` is the conversation; `domain` is the topic.
- `Record(id, subject, predicate, value, source_seq, note)` — an external fact (a log, an
  attendance sheet, an agency finding) with `source_seq` pointing at the message that proves it.

The engine never assumes anything about the parties, domain, or subject — swap the JSON in
`data/` and everything still runs.

## The layers

| Layer | Module | Input → output | Method |
|---|---|---|---|
| 1 | `pattern_detector` | messages → `PatternHit` | Lexicon of authority nouns bound to assertion verbs within a token window. The negative case matters: *mentioning* an authority is not the tactic. |
| 2 | `gap_detector` | full record + included seqs → `Gap` | Reconstruct omissions; flag **within-thread** cuts (neighbors share the omitted message's thread) apart from boundary trims. |
| 3 | `third_party` | messages + records → `Contradiction` | Denial-of-agreement claims tested against records on a shared topic; points back at `source_seq`. Never invents a contradiction it can't ground. |
| 4 | `domain_convergence` | messages → `Convergence` | Content anchors (non-stopword tokens/bigrams) appearing across ≥2 distinct domains. |
| 5 | `phrase_fragmentation` | messages → `RegisterAnomaly`, `RecurringPhrase` | Per-sender **leave-one-out** baseline of register features; flag deviations. Floats rounded; runs are identical. |

Every layer is a pure function over `list[Message]`, returns deterministically sorted output,
and uses only the standard library (`text.py` provides shared `normalize`/`tokens`/`ngrams`).

## The engine (`engine.py`)

1. **Normalize** every layer output to `Signal(layer, seqs, kind, detail)`.
2. **Group** signals. L1/L2/L3/L5 are *focal* — they form clusters and may merge when they share
   a `seq` (e.g. an L3 contradiction names the `source_seq` an L2 omission removed, binding them).
   L4 is a *corroborator* — it strengthens clusters it overlaps but never merges two that would
   otherwise be separate.
3. **Verdict.** Substantive layers = {L1, L2, L3}; contextual = {L4, L5}. A group is
   `elevated` iff it has ≥1 substantive layer **and** ≥2 distinct layers; otherwise `low`.

Result: `EngineResult(findings, all_signals, corpus_size)`, findings sorted elevated-first.

### Worked example (contractor corpus)
- seqs **{3, 10}** → L3 contradiction + L2 omission of the proof → **elevated** (headline).
- seq **5** → L1 borrow-authority + L2 (it was cut) + L5 register shift → **elevated**.
- seq **12** → L1 only → **low** (self-disqualification: a tactic with no corroboration).

## Narration (`narration.py`, `conversation.py`, `adapters/`)

- `TemplateNarrator` — deterministic, keyless, explains each finding and the disqualification
  principle. The default and the test baseline.
- `Conversation(result, complete, messages=None)` — a Q&A layer. With no `messages` it is built
  from `to_prompt(result)` and handed only the **structured findings**. With `messages` it builds
  the **Benoit Blanc** persona context (`persona.py`) — the structured findings plus the text of
  the messages those findings implicate — and gains `narrate_case()` for the opening summary.
  Either way the verdicts are fixed before any model is involved, and the `complete(prompt) -> str`
  callable is *injected*, so the core never touches an SDK or a key.
- `adapters/anthropic_llm.py` — Claude provider over the optional `anthropic` SDK.
- `adapters/openai_llm.py` — OpenAI provider over the optional `openai` SDK.
- `adapters/grok_llm.py` — Grok/xAI provider through the OpenAI-compatible xAI API.

Adapters are imported lazily by the demo, never by the core.

## Determinism

No `random`, no wall-clock, no network in the core. Floats are rounded before comparison;
all collections are explicitly sorted. `pytest -q` run twice produces identical results — the
CI runs it twice on purpose.
