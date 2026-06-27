# Intent — what the fragments and combinations are *for*

[`FRAGMENTS.md`](FRAGMENTS.md) catalogs **what fires** — the controlled vocabulary
each layer matches. This document catalogs **what the move is for** — the
communicative *function* a fragment, or a combination of fragments, is built to
achieve.

## The line this document does not cross

The engine's governing principle is **footprints, not the foot**: it emits the
observable structure (this phrase, this gap, this divergence) and **never asserts a
particular person's state of mind**. So everything below describes the *function of
a move-category* — what this kind of move is designed to accomplish as a matter of
rhetoric, the same way a linguist describes what a passive construction is *for* —
**not** what any individual speaker intended.

> A documented function is a **hypothesis the structure raises**, available for a
> human to weigh. It is never the engine's verdict. The engine "cannot grade its
> own homework": it can show you that a borrow-authority fragment appears and tell
> you what that move-category typically accomplishes; it cannot tell you the sender
> meant it. That judgment is the reader's.

Intent is also **compositional** — it escalates as you move up the hierarchy:

```
fragment        → a local function   ("make this look non-negotiable")
combination     → a strategic function("deny the fact AND block the rebuttal")
campaign        → an objective against a target ("control the medical narrative")
```

---

## Fragment-level function

### L1 · borrow-authority → *displace accountability*
**Function:** convert a contestable personal choice into the apparent dictate of an
outside authority ("the policy says", "my lawyer says"), so refusing it means
"arguing with the doctor/court," not with the speaker. It pre-loads the recipient's
options: pushing back now looks unreasonable. The speaker owns neither the decision
nor its consequences.

### L3 · claim-contradicted (denial-of-agreement) → *rewrite the shared record*
**Function:** deny a thing that happened ("we never agreed") to shift the burden of
proof onto the other party and destabilize their account. If unchallenged, the
denial *becomes* the record. (This is why L3 is inert without an external record to
test it against — the function only matters where there's a truth to overwrite.)

### L5 · formal-register tokens (`register_anomaly`) → *audience-shift / posture*
**Function (contextual, not a tactic alone):** signal that a message is "for the
record." A sudden legalistic register from an otherwise-casual sender reframes a
private exchange as a document aimed at a future official reader, and can carry an
intimidation or documentation posture. It colors intent; it does not establish it.

### L6 · cross-channel divergence → *audience-selected self-presentation*
**Function:** present the favorable version in the channel that will be read
officially while the private channel shows otherwise ("I always kept you informed"
on the record vs. "forgot to tell you" off it). The move's purpose is the *gap
itself*: a face managed per audience.

### L2 · within-thread omission (structural) → *curate the record*
**Function:** change the meaning of a record by removing interior context, not by
lying within it. The excerpt is literally true and materially misleading. The
function lives in what's missing.

### L4 · domain convergence (`domain_convergence`, structural) → *reveal a shared objective*
**Function (corroborator, not a move):** not something a speaker *does* but something
the analysis *surfaces* — independent topics bending toward one underlying decision.
Its "intent" is diagnostic: it shows that scattered messages are about the same
thing.

---

## Combination-level function (the part most often asked about)

Single fragments have local functions; their **combinations** are where strategy
appears. These are the `composition.py` templates, stated as purpose:

### `sanitize-record` = claim_contradicted + within_thread_omission
**Function:** assert a falsehood **while suppressing the very evidence that would
disprove it**. The denial and the cut are not two incidents — together they
manufacture a clean record: say "I never agreed," and ensure the message where you
agreed isn't in the exhibit. Either alone is weak; the combination is the strategy.

### `defer-and-deny` = borrow_authority + claim_contradicted
**Function:** deny a fact **and** pre-empt the rebuttal in one move — attribute the
denial to an authority so contesting it means contesting the authority. Denial
provides the content; borrowed authority provides the armor.

### `two-faced` = cross_channel_divergence
**Function:** sustain incompatible self-presentations across audiences as a
*standing posture*, not a slip — the record-facing face and the private face,
maintained in parallel.

### `repeated:<tactic>` (recurrence) → *normalize or wear down*
**Function:** a substantive move used past a threshold stops being an incident and
becomes a method — either **normalization** (establish the move as the baseline) or
**attrition** (exhaust the other party's capacity to contest each instance).
Recurrence counts only *substantive* moves, because repetition of a move is
strategy; repetition of ambient context (topic overlap, register) is not.

### campaign (actor → target over time) → *a sustained objective against a target*
**Function:** the top of the intent hierarchy. When one actor drives several
elevated findings against one target over time, the individual functions resolve
into a single objective — e.g., in the demo, one sender's repeated deferral to
medical/legal authority in the medical thread resolves to **control the medical
narrative to deny an agreed schedule swap**. The campaign names the *what-for* that
no single message reveals.

---

## The coercion grammar — stage functions

The named, **reactive** envelope `1 Action → [(2 objection ⇄ 3 obstruction) ⇄
(4 question ⇄ 5 justify)]^n → 6 fait accompli` (`coercion_grammar.py`). Its function
as a whole: **convert the other party's legitimate action into a fait accompli that
overrides it.** Per stage:

| # | Stage | Function |
|---|---|---|
| 1 | **action** | *the trigger* — the other party's legitimate move (a request, a boundary, exercising a right). Not the actor's; the grammar is a *reaction* to it. |
| 2 | **objection** | dispute the merits — refuse to agree, to keep the matter open |
| 3 | **obstruction** | block the mechanism — stonewall, delay, defer; the objection's enforcement arm |
| 4 | **question** | interrogate the other side's standing — make *them* the one who must justify |
| 5 | **justify** | supply one's own rationale (often via borrowed authority) — control the legitimacy frame |
| 6 | **fait accompli** | execute unilaterally and announce as done — **set the status quo** |

**The two engines and the war.** (2⇄3) is the *refusal engine* (prevent resolution);
(4⇄5) is the *legitimacy engine* (control the frame). Cycling `^n`, they are a
**documentation war**: back-and-forth that generates record, runs the clock, and
exhausts the other party. The war is not the objective — it is **cover**. The
objective is node 6: the **fait accompli sets the status quo**, and once the new
arrangement persists it is hard to disturb. So the function of the whole grammar is
temporal — *spend the other party's capacity to contest until the unilateral act has
become the baseline.*

**Why the envelope, not the stage, carries the intent.** Every stage is individually
deniable ("I was just asking"; "I'm only protecting her"; "the lawyer did say that").
But a legitimate action met with a sustained refusal+legitimacy cycle terminating in
a fait accompli is not deniable *as a shape*. No single message is the foot; the
envelope is the footprint trail. The engine still emits only the fragments and the
structure — a human reads the intent.

## Why function ≠ verdict (the calibration boundary)

The engine documents function so a human can ask the right question — *"is this what
was meant?"* — not so the machine can answer it. Three guards keep the line:

1. **Structure is emitted; intent is inferred by the reader.** Every signal carries
   its evidence (the phrase, the gap, the date); the function above is reference,
   not an assertion attached to the finding.
2. **Corroboration before weight.** A move's documented function only matters once
   the engine has *elevated* the finding (≥2 independent layers). A lone fragment's
   function is noted but uncorroborated — see the convergence rule in the README.
3. **The same move can have a benign function.** "My doctor says" can be a genuine
   report. The catalog gives the *manipulative-category* function; the precision
   boundaries in `FRAGMENTS.md` and the corroboration rule are what keep a benign
   instance from being read as the tactic.

Every detectable move has an entry here, and `tests/test_intent_doc.py` fails if a
tactic or template is added in code without a documented function — so a move can
never be detected without its "what-for" written down.
