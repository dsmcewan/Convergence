# convergence — a communication-forensics engine (demo)

[![tests](https://github.com/dsmcewan/Convergence/actions/workflows/ci.yml/badge.svg)](https://github.com/dsmcewan/Convergence/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)

A six-layer engine for analyzing a corpus of written communications. It does
**not** know or care whose messages it is fed. It was *built from* the structure
of message records — not *tailored to* any one conversation — so the **same
engine** runs on unrelated corpora with no code changes. (Fourteen data files
across the bundled corpora ship here — contractor, coparenting, channels,
grammar, and five dynamics variants; the only difference between runs is the
data in `data/`.)

**Who it's for:** anyone who must show *why* a message is manipulative with an
**auditable, deterministic** method instead of a black-box classifier —
investigators, analysts, and litigants working from a written record. Every
verdict traces to specific messages and the independent layers that corroborate
it; a language model can *explain* a finding but can never move one.

> **Privacy:** The shipped demo and every bundled corpus are **synthetic** —
> `data/` is fictional and nothing is imported from any private system. The
> optional `--corpus db` path reads a private SQLite database **you** supply,
> read-only; it is never bundled and never leaves your machine.

> **Built fast by a Claude-led multi-model agentic system** — Claude as lead
> architect, Codex on implementation feasibility, Agy on phase-gating, Grok as
> adversarial reviewer. The whole of it — six-layer engine, five validated
> corpora, scored eval, Blanc narrator, and this web demo — came together across
> **25–26 Jun 2026**, with the multi-model substrate itself stood up in a **single
> morning**. A fast multi-model build, not a long hand-coded grind.

## The six layers

1. **Pattern detection** (`layers/pattern_detector.py`) — tags a message with the
   communicative tactic it makes, starting with *borrow-authority /
   displace-accountability* ("the platform's policy says…", "my lawyer says…").
2. **Record-vs-exhibit reconstruction / "frog DNA"** (`layers/gap_detector.py`) —
   given the full record and a curated *exhibit subset of it*, reconstructs what was
   removed and flags **within-thread** omissions (a message cut from inside one
   continuous conversation) apart from ordinary boundary trims.
3. **Third-party referencing** (`layers/third_party.py`) — tests claims against an
   external records set and surfaces contradictions, pointing back at the message
   that proves the truth.
4. **Domain convergence** (`layers/domain_convergence.py`) — detects where
   independent topical domains converge on a single anchor.
5. **Phrase fragmentation** (`layers/phrase_fragmentation.py`) — register anomalies
   (a sender departing from their own baseline) and recurring n-grams.
6. **Cross-channel correlation** (`layers/cross_channel.py`) — tests a sender's
   *claim* in one channel against that **same sender's own words in a second
   channel**, aligned by sender and predicate ("I always kept you informed" in the
   formal channel vs. "forgot to tell you…" in the casual one). Flags the divergence
   on the claiming message and cites the contradicting cross-channel message.

## The convergence rule

Every layer is reduced to a common `Signal`; `engine.py` groups signals and
elevates a finding only when independent layers agree. The layers are weighted:

- **Substantive** — L1 (tactic), L2 (omission), L3 (contradiction), L6
  (cross-channel divergence): the actual moves.
- **Corroborator** — L4 (domain overlap): strengthens clusters it overlaps but
  never forms or merges a finding on its own.
- **Focal-but-contextual** — L5 (register shift): bridges clusters like a focal
  layer but is not substantive; cannot make a finding without a substantive layer.

A group is **elevated** only when it carries ≥1 substantive layer **and** ≥2
distinct layers total. Context-only groups, and lone signals, stay **low**. The
engine is built to *disqualify its own findings* unless they survive corroboration
— it cannot grade its own homework.

## Composition: patterns and campaigns

The engine answers a per-event question ("is this one finding corroborated?").
`composition.py` sits above it and reads the structured result — **no engine
changes** — to answer two higher-order questions:

- **Patterns** (`find_patterns`) — recurring structure across findings:
  - *named chains* (templates, the corpus-agnostic analog of DARVO): e.g.
    `sanitize-record` = contradiction + within-thread omission; `two-faced` =
    cross-channel divergence; `defer-and-deny` = borrow-authority + contradiction.
  - *recurring tactics*: one **substantive** move repeated past a threshold (a
    habit, not an incident). Contextual signals (domain overlap, register shift)
    are excluded — they are ambient, not moves.
- **Campaigns** (`find_campaigns`) — a **sustained course of conduct**: one *actor*
  (sender) driving ≥2 elevated findings against one *target* (topical domain) over
  time. Attribution and the time span come from the messages; the verdicts remain
  the engine's. One elevated finding is an incident; two against the same target is
  a campaign.

This is the `fragments → tactics → findings → patterns → campaigns` hierarchy: the
demo corpora show a `sanitize-record` chain in the contractor record (an incident),
and in the co-parenting record a real campaign — one sender repeatedly deferring to
medical/legal authority in the medical thread to deny an agreed schedule swap.

Three documents describe this hierarchy, each kept in sync with the code by a test:

- [`FRAGMENTS.md`](FRAGMENTS.md) — the bottom rung: the controlled fragment
  vocabularies each layer matches, with their precision boundaries (*what fires*).
- [`INTENT.md`](INTENT.md) — cuts across every rung: the communicative **function**
  of each fragment and combination, framed as a hypothesis the structure raises,
  never the engine's verdict (*what for*).
- [`HIERARCHY.md`](HIERARCHY.md) — the spine: the four tiers `tactics → findings →
  patterns → campaigns` and the **rule at each arrow** that promotes a move up a rung
  (*how it adds up*) — including the first **named campaign-shape**, the reactive
  coercion grammar `1 Action → [(2⇄3)⇄(4⇄5)]^n → 6 fait accompli`
  (`convergence/coercion_grammar.py`; try `demo.py --corpus grammar`).

(Guards: `tests/test_fragments_doc.py`, `tests/test_intent_doc.py`,
`tests/test_hierarchy_doc.py`.)

[`ENGINEERING.md`](ENGINEERING.md) records the deterministic-over-agentic judgment and
maps the codebase to Anthropic's engineering principles (evals-first, narrow grounded
model seam, composable tools). `demo.py --eval` prints the scored discriminator report
(precision / recall / F1 / specificity, with the hard-negative call-out).

[`DYNAMICS.md`](DYNAMICS.md) documents five synthetic 3-year coparenting corpora
(`data/dyn_*.json`) spanning the validated spectrum **cooperative → parallel →
conflicted → high-conflict → coercive-controlling**, each anchored to the literature
(Maccoby & Mnookin; Ahrons; Kelly & Johnson; Stark). `demo.py --corpus dynamics`
shows the engine separating **coercive control from high-conflict by structure, not
vocabulary** — the coercion-grammar envelope completes only for the unilateral case.

## Narration

`engine.py` emits structured findings; the verdicts are fixed before any model is
involved.

- **`narration.py`** — `TemplateNarrator`: deterministic, keyless plain-language
  explanation. The default, the test baseline, and the fallback.
- **The Voice of Convergence — `BlancNarrator`** (`--voice blanc`): renders the *same*
  structured findings, patterns, and campaigns in the register of Benoit Blanc — a
  methodical detective who lays out the evidence, honors corroboration, and refuses to
  convict on a hunch. Thematically exact: Blanc narrates method and footprints, never
  the foot. It is **pure presentation** — deterministic, keyless, and it changes no
  verdict (a test asserts Blanc reports the same elevated seqs as the plain narrator).
- **`conversation.py`** — `Conversation`: a Q&A layer that answers from the
  **structured findings only** (never the raw corpus or the detection code), via an
  injected `complete(prompt) -> str`. The model can explain a verdict; it cannot
  move one. An optional persona (`BLANC_PERSONA`) rides on top of the grounding — the
  voice changes, the constraints do not.
- **`adapters/anthropic_llm.py`** — optional Claude backend (needs `anthropic` +
  `ANTHROPIC_API_KEY`).
- **`adapters/openai_llm.py`** — optional OpenAI backend (needs `openai` +
  `OPENAI_API_KEY`).
- **`adapters/grok_llm.py`** — optional Grok/xAI backend (uses the OpenAI-compatible
  xAI API; needs `openai` + `XAI_API_KEY` or `GROK_API_KEY`).
- **`adapters/antigravity_cli_llm.py`** — optional **keyless** backend that drives the
  installed Antigravity CLI (`agy`, a fast Gemini backend via the app's OAuth). `agy`
  only prints its answer to a real terminal, so this adapter runs it inside a ConPTY
  (needs `pywinpty`) and strips the terminal control bytes. `--model agy`.

Adapters are the only places third-party SDKs are touched; the core never imports
them. Keys can live in the environment or in a local `.env` file. The optional
backend dependencies are listed in [`requirements.txt`](requirements.txt) (the
engine core needs none of them).

## Install

Requires **Python 3.10+** and `git`. The engine core is **stdlib-only** — the
install pulls no runtime dependencies; the optional `llm` extra is only for the
conversational backends.

```bash
git clone https://github.com/dsmcewan/convergence
cd convergence

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (Git Bash):    source .venv/Scripts/activate
# macOS / Linux:         source .venv/bin/activate

pip install -e ".[dev]"        # core + pytest; add ,llm for the optional chat backends
```

This installs three console commands — `convergence`, `convergence-web`, and
`convergence-build` — so nothing depends on the path you cloned into. (Every
command below also works as `python demo.py …` / `python -m web.server` from the
repo root if you prefer not to install.)

## Run

```bash
pytest tests/ -q                 # 191 deterministic tests

convergence-build                # write web/site/data/*.json (auto-runs on first serve)
convergence-web                  # local frontend: http://127.0.0.1:8765/

convergence --corpus contractor      # default
convergence --corpus coparenting     # same engine, other corpus
convergence --corpus channels        # two-channel corpus (Layer 6)
convergence --about                  # the Voice of Convergence explains itself
convergence --trick                  # ... explains the magic trick (the method)
convergence --corpus contractor --voice blanc  # the Voice of Convergence
convergence --corpus grammar         # coercion-grammar structural analysis
convergence --corpus dynamics        # 5-type discrimination table
convergence --corpus db --db /path/to/your.db   # run on your own SQLite export
convergence --eval                   # scored discriminator report
convergence --investigate            # propose + verify new detectors
convergence --chat --voice blanc     # conversational Blanc with Claude
convergence --chat --model openai    # use OpenAI
convergence --chat --model grok      # use Grok/xAI
convergence --chat --voice blanc --model agy  # keyless, via the Antigravity CLI
```

Optional chat backends read keys from the environment or a local `.env`
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`/`GROK_API_KEY`); each
degrades to the deterministic narrator when its key/CLI is absent.

### Docker

```bash
docker build -t convergence .
docker run --rm -p 8765:8765 convergence                                      # local only (no API key needed)
docker run --rm -p 8765:8765 -e CONVERGENCE_API_KEY=<key> convergence        # required for any exposed deployment
```

The image binds `0.0.0.0` (via `CONVERGENCE_HOST`) so the port is reachable from
the host; the app still defaults to `127.0.0.1` everywhere else. `/api/chat`
proxies to paid LLM backends, so only publish this port behind a trusted
boundary.

## Evaluation

Two complementary measures, because they answer different questions:

- **Synthetic discriminator (labeled ground truth).** `convergence --eval` scores
  the coercion-grammar discriminator over the five labeled dynamics corpora:
  `precision = recall = F1 = 1.00` **on synthetic, labeled data** (not a
  general-population metric), with the high-conflict corpus held as a *hard
  negative* (hostile, many stage-hits, but correctly not coercive). A perfect
  score on synthetic data proves the discriminator separates the classes it was
  designed around — nothing more.

- **Real-data documentary precision (no labeled truth).** On a real corpus there
  is usually no ground truth, only pipeline triage labels — and scoring the engine
  against those would be circular. `evaluation.documentary_precision` instead asks
  a *precision-only* question: of the messages the engine **elevates**, how many
  are independently anchored to a document or exhibit (via
  `corpus.load_documentary_ids`, pointed at your own evidence tables)? **No recall
  is claimed** — a documentary set is incomplete, so an uncorroborated finding is a
  pointer to review, not a false positive. This honors documentary primacy:
  documents are evidence; labels only triage. Bring your own corroboration source
  to run it on your data.

## Deploying

Two modes, by whether you need the live chat endpoint:

- **Static-only (no server, no chat).** `convergence-build` writes
  `web/site/data/*.json`; the whole `web/site/` folder is then a static site you
  can host anywhere (GitHub Pages, S3, Netlify). The lecture deck, corpora, and
  scorecard all work from the static JSON — only `/api/chat` is unavailable. This
  is the safest deployment: no backend, no keys, no egress.

- **Full-stack (with chat).** Run the server (`convergence-web`) or the Docker
  image. `/api/chat` proxies to paid LLM backends, so for any exposed deployment:
  set `CONVERGENCE_HOST=0.0.0.0`, set `CONVERGENCE_API_KEY` (clients send
  `X-API-Key`), and front it with a TLS-terminating reverse proxy that rate-limits.
  See `SECURITY.md` for the full threat model.

## Layout

```
convergence/            engine (corpus-agnostic; stdlib only in core)
  corpus.py             Message model + JSON / SQLite loaders
  records.py            third-party Record model + loader
  text.py               shared deterministic text helpers
  engine.py             signal normalization + convergence verdict
  composition.py        patterns (L7) + campaigns (L8), above the engine
  narration.py          deterministic TemplateNarrator (+ composition narration)
  conversation.py       grounded Q&A seam (model injected)
  layers/               one module per analytical layer (L1–L6)
  adapters/             optional LLM adapters (Claude, OpenAI, Grok, Gemini, agy)
data/                   14 data files: contractor (sample_*), coparenting, channels (formal+casual), grammar, dynamics (dyn_*)
tools/                  generate_dynamics.py — seeded dynamics-corpus generator
tests/                  191 deterministic tests
web/                    static frontend + local stdlib server
  serialize.py          engine result -> browser JSON
  build.py              writes web/site/data/*.json for static hosting
  server.py             local frontend + /api/chat
  site/                 vanilla HTML/CSS/JS demo
demo.py                 narrated walkthrough (--corpus, --chat, --model)
requirements.txt        optional backend deps (core is stdlib only)
```
