# The hierarchy — tactics → findings → patterns → campaigns

[`FRAGMENTS.md`](FRAGMENTS.md) documents the bottom rung (the lexical building
blocks) and [`INTENT.md`](INTENT.md) cuts across every rung (what each move is
*for*). This document is the **spine**: the four tiers above fragments, and — the
part that matters most — the **rule at each arrow**, because the arrows are where
the engine earns its conclusions.

```
fragment → TACTIC → FINDING → PATTERN → CAMPAIGN
  (match)   (converge)  (compose)  (attribute)
```

Each arrow is a different *kind* of evidence-raising. A move is only ever promoted
up a rung by a rule that can be stated, tested, and audited — never by a guess.

| Arrow | Rule | Lives in |
|---|---|---|
| fragment → tactic | a controlled fragment matches **in context** | `layers/*.py` |
| tactic → finding | tactics on the **same material** corroborate (≥2 independent layers) | `engine.py` |
| finding → pattern | findings exhibit a **named chain** or a **repeated move** | `composition.py` |
| pattern → campaign | one **actor** sustains it against one **target over time** | `composition.py` |

---

## Tier 1 · Tactics (layer signals)

**What:** a single communicative move, detected by one layer and normalized to a
common shape so the rest of the engine never has to know which layer produced it.

**Code:** `engine.Signal(layer, seqs, kind, detail)` — emitted by L1–L6 in
`_collect_signals`.

**Built from:** a fragment (or a structural fact) firing in context — see
`FRAGMENTS.md`. One layer, one move.

**Governing constraint:** a tactic is an *observation*, not a verdict. It carries
its own evidence (`seqs`, `detail`) and nothing more. Substantive tactics (L1
borrow_authority, L2 within_thread_omission, L3 claim_contradicted, L6
cross_channel_divergence) are *moves*; contextual ones (L4 domain_convergence, L5
register_anomaly) are *coloring*. A lone tactic proves nothing.

**Worked example (contractor):** `L1 borrow_authority @ seq 5` ("the platform's
billing policy says…") and `L3 claim_contradicted @ seqs (3,10)` ("I never agreed"
vs. the record) are two tactics. On their own, neither is a finding.

---

## Tier 2 · Findings (convergence)

**What:** a cluster of tactics on the same material, with a confidence. This is the
engine's per-event verdict.

**Code:** `engine.Finding(seqs, confidence, layers, signals, summary)` — produced by
`run_engine`.

**Built from tactics — the convergence rule (the whole thesis):** focal tactics
(L1/L2/L3/L5/L6) that share a seq are merged into one group; L4 attaches as a
corroborator without expanding the group. A group is **`elevated`** iff it carries
**≥1 substantive layer AND ≥2 distinct layers**; otherwise **`low`**.

**Governing constraint:** the engine is built to *disqualify its own findings*.
A move only counts once a second, independent layer agrees on the same material —
it cannot grade its own homework. Context-only clusters (L4/L5) and lone tactics
stay low.

**Worked examples (contractor):**
- `{3,10}` → **elevated** (L2 omission + L3 contradiction + L4): the "I never agreed"
  claim is contradicted by the record whose proof (seq 3) was cut from the exhibit.
  The headline.
- `seq 12` → **low** (L1 only): "my accountant says I only owe the original quote" —
  a substantive tactic with nothing to corroborate it. The self-disqualification
  demo.

---

## Tier 3 · Patterns (composition)

**What:** recurring structure *across* findings — the first tier that sees more than
one event at a time.

**Code:** `composition.Pattern(name, kind, seqs, detail)` — produced by
`find_patterns(result)`. Two kinds:
- **template** — a named tactic-chain (the corpus-agnostic analog of DARVO), fired
  when a single finding carries all of a template's required signal kinds:
  `sanitize-record`, `defer-and-deny`, `two-faced`.
- **recurrence** — one **substantive** tactic repeated across ≥ `recurrence_min`
  distinct messages (a habit, not an incident).

**Built from findings/tactics:** templates read the kind-set of each finding;
recurrence counts distinct seqs per substantive kind across all tactics.

**Governing constraint:** recurrence excludes contextual kinds — repeated domain
overlap or register shift is ambient, not a method, and counting it would only add
noise. A pattern is structure, still not attribution.

**Worked examples:**
- contractor: `sanitize-record @ (3,10)` (template) + `repeated:within_thread_omission
  @ (3,5,11)` (recurrence — the exhibit cut three interior messages).
- coparenting: `repeated:borrow_authority @ (8,10,13)` — defer-to-authority used three
  times.
- channels: `two-faced @ (2)` — the cross-channel divergence.

---

## Tier 4 · Campaigns (attribution over time)

**What:** a sustained course of conduct — one actor driving the structure against one
target across time. The top of the hierarchy; the tier that names a *what-for* no
single message reveals.

**Code:** `composition.Campaign(actor, target, patterns, findings, seqs, span,
summary)` — produced by `find_campaigns(result, messages)`.

**Built from patterns + findings:** each elevated finding (and each pattern) is
attributed to an **actor** (the modal sender of its seqs) and a **target** (the modal
topical domain), read from the messages. A campaign is emitted when one
`(actor, target)` accounts for **≥2 elevated findings**; its **span** is the time
window of those findings.

**Governing constraint:** the span is defined by the *corroborated elevated
findings*, not by attached patterns (which may reach adjacent material) — so the
"over time" window stays honest. One elevated finding is an incident; two against
the same target is a campaign.

**Worked example (coparenting):** **Sam → medical**, two elevated borrow_authority
findings (`{8}`, `{10}`) spanning `2025-04-11T09:03 .. 09:31`, with the
`repeated:borrow_authority` pattern attached. Reads as: *one sender repeatedly
deferring to medical/legal authority in the medical thread to deny an agreed
schedule swap.* The contractor record, by contrast, yields patterns but **no
campaign** — its two elevated findings hit different targets, so it stays an
incident.

---

## A named campaign-shape: the coercion grammar

Campaigns above are *emergent* — the engine discovers an actor sustaining findings
against a target. A **named campaign-shape** is the dual: a known envelope the system
looks *for*. The first is the reactive coercion grammar (`coercion_grammar.py`):

```
1 Action ──▶ [ (2 objection ⇄ 3 obstruction) ⇄ (4 question ⇄ 5 justify) ]^n ──▶ 6 fait accompli
 trigger        refusal engine            legitimacy engine                       sets the status quo
 (the other     (prevent resolution)      (control the frame)                     (overrides the action)
  party's
  legit move)        └──────── documentation war, cycled n times ────────┘
```

**Reactive:** node 1 is the *other party's* legitimate action; stages 2–6 are run
against it. **Two engines:** refusal (2⇄3) keeps the matter open; legitimacy (4⇄5)
makes the other side justify themselves. **The war:** cycling `^n` generates record,
runs the clock, and exhausts — it is cover, not objective. **The objective:** node 6,
the fait accompli, terminates the war and **sets the status quo** — and once the new
arrangement persists it is hard to reverse.

- **Code:** `coercion_grammar.tag_stages` (label each message's stage) and
  `match_grammar` (recognize the envelope per thread, count the documentation-war
  cycles, mark the seq at which the fait accompli set the status quo).
- **Built from fragments directly** (six stage families, see `FRAGMENTS.md`), not from
  engine signals — it is an ordered, cyclic grammar, where the engine's templates are
  unordered. Stage 5 reuses L1 `borrow_authority` in the *justify* role.
- **Governing constraint:** a single stage is deniable; only the **complete envelope**
  (action + ≥1 cycle + fait accompli) is treated as the grammar. See `INTENT.md` for
  why the shape, not the stage, carries the intent.

**Worked example (`demo.py --corpus grammar`):** a swap request (seq 1, Alex) is met
with a 3-cycle documentation war (seqs 2–7, Sam) terminating in a fait accompli
(seq 8) that sets the status quo — a *complete* envelope.

## The calibration thread that runs the whole way up

The same discipline holds at every rung, which is what makes the top defensible:

1. **Evidence travels with the claim.** A tactic carries its phrase; a finding its
   tactics; a pattern its seqs; a campaign its findings and span. Nothing is asserted
   without its footprints.
2. **Promotion requires corroboration.** Nothing rises a rung on its own weight: a
   tactic needs a second layer to become a finding; a finding needs to recur or chain
   to become a pattern; a pattern needs an actor-and-target-over-time to become a
   campaign.
3. **The engine stops at structure.** Even at the campaign tier it names *what the
   structure is*, not *what was intended* — `INTENT.md` documents function as a
   hypothesis for a human to weigh, never the engine's verdict.

Every tier's data structure (`Signal`, `Finding`, `Pattern`, `Campaign`) and every
layer (L1–L6) named here is checked against the code by `tests/test_hierarchy_doc.py`,
so the spine cannot drift from what the engine actually builds.
