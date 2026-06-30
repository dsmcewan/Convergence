# Phrase fragments — the building blocks

A **fragment** is the smallest unit the engine matches: a controlled word or short
phrase that, in context, signals a communicative *move*. The thesis of this engine
is that coercive/evasive communication is **rule-governed** — it reuses a finite,
catalogable vocabulary — so it can be parsed deterministically rather than guessed
at statistically. The payoff is **provenance**: every signal traces to a named
fragment in a named file, so a finding is auditable rather than asserted.

Fragments are the bottom of the hierarchy:

```
fragments → tactics (layer signals) → findings → patterns → campaigns
```

This document catalogs **what each fragment fires on**. For **what each fragment and
combination is *for*** — its communicative function, framed as a hypothesis the
structure raises rather than the engine's verdict — see [`INTENT.md`](INTENT.md).

This document catalogs every fragment vocabulary currently in the engine, drawn
**verbatim from the source**. Each entry lists what it detects, the exact
vocabulary, the **precision boundary** (the negative cases that must *not* fire),
and where to extend it.

> Not every layer is lexical. Two of the strongest signals are **structural**, not
> phrase-based (L2 omission, L4 convergence) — see "Non-lexical building blocks"
> below. Fragments are the building blocks of the *lexical* layers; the engine is
> deliberately not fragments-only.

---

## L1 · borrow-authority / displace-accountability
`layers/pattern_detector.py`

Presenting a decision as the dictate of an outside authority ("the platform's
policy says…", "my accountant says…") so the speaker never owns it. A fragment
fires only when an **authority root** is bound to an **assertion verb** within a
short window — mentioning an authority alone is not the tactic.

**Authority roots**
> platform, policy, accountant, doctor, lawyer, attorney, court, hr, mediator,
> teacher, pediatrician, bank

**Assertion verbs**
> says, said, recommends, recommended, requires, required, advises, advised,
> states, stated

**Binding rule:** authority and verb within **3 tokens** of each other (`WINDOW`);
possessive `'s` is stripped so "platform's policy says" matches.

**Precision boundary (must NOT fire):** a direct factual assertion that merely
names a document — *"Revisions are included; I can send you the policy section"* —
has no authority-bound assertion verb, so it does not fire. (This is the contractor
corpus seq-6 negative case.)

---

## L3 · claim contradicted (denial of agreement)
`layers/third_party.py`

A denial fragment whose factual claim is tested against an external records set.
The denial is only the *trigger*; the contradiction is confirmed by a record, not
by the phrase alone.

**Denial fragments** (regex)
> `never (agreed | approved | consented)`
> `(didn't | did not) (agree | approve | consent)`

**Precision boundary:** the fragment emits a contradiction **only** when a record
shows agreement on the same topic (predicate shares a content word with the claim).
No matching record → nothing emitted. The engine never invents a contradiction.

---

## L5 · register anomaly (formal-register fragments)
`layers/phrase_fragmentation.py`

Not a tactic by itself — a *contextual* signal. These legalistic tokens raise a
message's "formal share"; a spike above the sender's own baseline flags a register
shift (a casual author suddenly writing like a contract).

**Formal lexicon**
> pursuant, policy, approving, authorization, authorize, review, accordance,
> consent, provision, hereby, basis, stated, require, required, custody, order,
> aforementioned, herein

**Precision boundary:** the lexicon only contributes to a *per-sender, leave-one-out*
baseline deviation. A uniformly formal sender does not flag (no deviation); a
single formal word in an otherwise casual message can. It corroborates — it never
elevates a finding alone.

---

## L6 · cross-channel divergence (claim vs. admission)
`layers/cross_channel.py`

Paired fragments: a favorable **claim** in one channel vs. the same sender's
contradicting **admission** in another. Aligned by sender *and* predicate.

**Predicate `kept_informed`**
- claim: `always (kept | keep) [you/him/her/them] [fully] (informed | updated | apprised | in the loop)`
- admission: `forgot to (tell | mention | inform)` · `did(n't) (tell | mention | inform | notify)` · `never told`

**Predicate `paid_ontime`**
- claim: `always paid`
- admission: `skipped (paying | payment | the)` · `never paid` · `did(n't) pay` · `forgot to pay`

**Precision boundary:** a divergence emits only when the **same sender** makes the
claim in the primary channel *and* the admission in the cross channel. A consistent
or silent cross channel, or an admission by a different sender, emits nothing.

---

## Coercion-grammar stage fragments
`coercion_grammar.py`

Six fragment families, one per stage of the reactive coercion grammar
`1 → [(2⇄3)⇄(4⇄5)]^n → 6` (see `HIERARCHY.md` for the envelope and `INTENT.md` for
each stage's function). Each is a controlled vocabulary over normalized text.

| # | Stage | Representative cues |
|---|---|---|
| 1 | **action** | can we / could you / i'd like to / i'm taking / please confirm / like we agreed |
| 2 | **objection** | don't agree / do not agree / i disagree / that won't work / i'm not comfortable / i refuse / i don't think X is right / i'm not sure about X / i don't know anything about X |
| 3 | **obstruction** | let's talk about this later / i'll get back to you / we'll discuss / i need more time / i'm done discussing |
| 4 | **question** | why would you / on what basis / who said / what makes you think / since when / says who |
| 5 | **justify** | i'm only trying to / for her safety / the (policy\|agreement\|order) says / my (lawyer\|doctor) … says/said/told me / pursuant to / per the (agreement\|order\|policy\|parenting plan) |
| 6 | **fait_accompli** | i've already / i went ahead and / it's already done / it's final / we've moved / i (enrolled\|booked\|registered\|scheduled\|withdrew\|switched\|moved) / there's nothing to discuss |

**Precision boundary:** these are deliberately dual-use — *question* must not fire on
an ordinary logistics question ("what time is pickup?"), and *justify* ("for her
safety") can be a genuine concern. A single stage in isolation is **deniable**; the
fragments only carry weight inside the **envelope** (action + cover cycles + fait
accompli), which the matcher requires. Stage 5 overlaps L1 `borrow_authority` — the
same "the lawyer says" fragment, now read as the *justify* role.

## Non-lexical building blocks

Two layers carry no phrase fragments — their signal is **structure**, which is why
they are often the most decisive:

- **L2 · within-thread omission** (`layers/gap_detector.py`) — the building block is
  a *gap*: a message cut from inside one continuous thread (its shown neighbors on
  both sides share its thread). You cannot see a splice by reading the splice; you
  reconstruct the record and watch which interior pieces are missing.
- **L4 · domain convergence** (`layers/domain_convergence.py`) — the building block
  is a shared **anchor** (a content word/bigram, ≥4 chars, non-stopword) recurring
  across ≥2 independent domains. It also maintains an *anti-fragment* `STOPWORDS`
  list — the connective tissue and generic verbs that must never count as anchors.

---

## Composition · fragments of tactics

One level up, the same idea repeats: a **template pattern** is a fragment whose
"tokens" are *tactics* rather than words. `composition.py`:

| Template | Required signal kinds (the chain) |
|---|---|
| `sanitize-record` | claim_contradicted + within_thread_omission |
| `defer-and-deny`  | borrow_authority + claim_contradicted |
| `two-faced`       | cross_channel_divergence |

A **recurrence pattern** is one *substantive* fragment-tactic repeated past a
threshold — and pointedly excludes the contextual signals (domain overlap, register
shift), which are ambient, not moves.

---

## Extending the catalog

Every vocabulary above is a module-level constant or small registry — extension is
adding an entry, not changing logic:

| Add a… | Where |
|---|---|
| authority root / assertion verb | `pattern_detector.py` → `AUTHORITY_ROOTS` / `ASSERTION_VERBS` |
| denial / claim family | `third_party.py` → `_DENIAL` (+ predicate topic) |
| formal-register token | `phrase_fragmentation.py` → `FORMAL_LEXICON` |
| cross-channel claim/admission pair | `cross_channel.py` → `_CROSS_RULES` |
| named tactic-chain | `composition.py` → `_TEMPLATES` |

**Calibration rule:** every fragment added should come with both a positive example
(it must fire) and a precision boundary (a near-miss it must *not* fire on). Loosening
a fragment to catch one more case usually re-admits noise; the durable fix is a new,
specific fragment plus its negative — not a broader regex.
