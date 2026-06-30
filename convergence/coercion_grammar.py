"""The coercion grammar — a named, reactive campaign shape.

    1 Action -> [ (2 objection <-> 3 obstruction) <-> (4 question <-> 5 justify) ]^n -> 6 fait accompli

The grammar is **reactive**: the other party's legitimate *action* (1) is met not
with engagement but with two reinforcing engines run against it —

  * the REFUSAL engine (objection <-> obstruction): dispute the merits and block
    the mechanism, to prevent resolution;
  * the LEGITIMACY engine (question <-> justify): interrogate the other side's
    standing while supplying one's own rationale (often borrowed authority), to
    control the frame.

These cycle, `^n`, as a **documentation war** — back-and-forth that generates
record, runs the clock, and exhausts the other party — *until* the **fait accompli**
(6): the decision executed unilaterally and announced as done, which terminates the
war and **sets the status quo**. In family-law terms the status quo is the prize:
once the new arrangement has persisted it is hard to disturb, so the documentation
war is cover and the fait accompli is the objective.

Deterministic, fragment-based, synthetic-data only. Each stage has its own controlled
vocabulary (see FRAGMENTS.md); the *envelope* (action + cover cycles + fait accompli)
is what carries weight — a single stage in isolation is deniable, the shape is not.
"""  # noqa: E501
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from convergence.corpus import Message
from convergence.text import normalize


@dataclass(frozen=True)
class _Stage:
    num: int
    name: str
    pattern: re.Pattern


# The six stages, each a controlled fragment family over normalized (lowercased) text.
STAGES: tuple[_Stage, ...] = (
    _Stage(1, "action", re.compile(
        r"\b(can we|could we|could you|i'd like to|i would like to|i'm planning to|"
        r"i intend to|i'll be|i will be|please confirm|please let me know|i'm taking|"
        r"i'm picking|i want to confirm|like we agreed)\b")),
    _Stage(2, "objection", re.compile(
        r"\b(i object\b|don't agree|do not agree|i disagree|that won't work|"
        r"that's not acceptable|that is not acceptable|i'm not comfortable|"
        r"i am not comfortable|i won't agree|i refuse|that's not happening)\b")),
    _Stage(3, "obstruction", re.compile(
        r"\b(let's just talk about this later|let's talk about this later|let's talk later|"
        r"i'll get back to you|we'll discuss|i need more time|i need time|"
        r"i'm not going to respond|we can talk about this later|we'll talk in person|"
        r"i'll have my (lawyer|attorney|accountant)|i'm done discussing)\b")),
    _Stage(4, "question", re.compile(
        r"\b(why would you|on what basis|who said|who told you|what makes you think|"
        r"since when|are you serious|explain to me why|explain why|"
        r"what gives you the right|says who|how do you figure)\b")),
    _Stage(5, "justify", re.compile(
        r"\b(i'm only trying to|i'm just trying to|i am only trying to|"
        r"for (her|his|their) safety|in (her|his) best interest|because the|because my|"
        r"the (policy|agreement|order|schedule) (says|states|requires|stands)|"
        r"my (lawyer|attorney|accountant|doctor) (says|said|advised)|"
        r"pursuant to|per the (agreement|order|policy))\b")),
    _Stage(6, "fait_accompli", re.compile(
        r"\b(i've already|i already|i went ahead and|it's already done|it's done|"
        r"it's final|it's settled|she's now (enrolled|registered|signed up)|"
        r"she's enrolled|we've moved|we've relocated|"
        r"i've (enrolled|booked|switched|withdrawn|moved|scheduled)|"
        r"too late now|too late to|there's nothing to discuss|nothing to discuss|"
        r"the decision is made|the decision has been made)\b")),
)

_REFUSAL = {2, 3}      # objection <-> obstruction
_LEGITIMACY = {4, 5}   # question <-> justify


@dataclass(frozen=True)
class StageHit:
    seq: int
    stage: int
    name: str
    cue: str
    sender: str


@dataclass(frozen=True)
class GrammarMatch:
    thread: str
    coercer: str
    seqs: tuple[int, ...]
    stages_present: tuple[int, ...]
    has_action: bool
    has_fait_accompli: bool
    cycles: int                  # ordered refuse->legitimize rounds before the fait
    status_quo_seq: int | None   # the fait accompli that set the status quo
    complete: bool
    summary: str


def tag_stages(messages: list[Message]) -> list[StageHit]:
    out: list[StageHit] = []
    for m in messages:
        t = normalize(m.body)
        for s in STAGES:
            hit = s.pattern.search(t)
            if hit:
                out.append(StageHit(seq=m.seq, stage=s.num, name=s.name,
                                    cue=hit.group(0), sender=m.sender))
    out.sort(key=lambda h: (h.seq, h.stage))
    return out


def _run_envelope(hits: list[StageHit], coercer: str) -> tuple[int, bool]:
    """Ordered per-coercer machine over seq-sorted hits.
    An action (1, any party) opens it; then the coercer runs >=1 ordered
    refuse(2/3)->legitimize(4/5) round and a fait(6). Returns (cycles, complete)."""
    state = "S0"
    cycles = 0
    for h in hits:
        if state == "S0":
            if h.stage == 1:                      # the proposal opens it (any sender)
                state = "OPENED"
            continue
        if h.sender != coercer:                   # only the coercer drives the war/fait
            continue
        if state == "OPENED" and h.stage in _REFUSAL:
            state = "REFUSED"
        elif state == "REFUSED" and h.stage in _LEGITIMACY:
            cycles += 1
            state = "CYCLED"
        elif state == "CYCLED" and h.stage in _REFUSAL:
            state = "REFUSED"                     # start the next round
        elif state == "CYCLED" and h.stage == 6 and cycles >= 1:
            state = "COMPLETE"
            break
    return cycles, state == "COMPLETE"


def match_grammar(messages: list[Message]) -> list[GrammarMatch]:
    by_thread: dict[str, list[Message]] = defaultdict(list)
    for m in messages:
        by_thread[m.thread].append(m)

    out: list[GrammarMatch] = []
    for thread, msgs in sorted(by_thread.items()):
        hits = tag_stages(msgs)  # already sorted by (seq, stage)
        if not hits:
            continue
        has_action = any(h.stage == 1 for h in hits)
        # candidate coercers: any sender who shows war activity (refusal/legitimacy)
        # OR a fait. (A war without a fait, or a fait without a war, still yields a
        # PARTIAL match — preserving the incomplete/fait-alone behavior.)
        candidates = sorted({
            h.sender for h in hits
            if h.stage in _REFUSAL or h.stage in _LEGITIMACY or h.stage == 6
        })
        for coercer in candidates:
            cycles, complete = _run_envelope(hits, coercer)
            coercer_faits = [h.seq for h in hits if h.stage == 6 and h.sender == coercer]
            has_fait_c = bool(coercer_faits)
            if cycles < 1 and not has_fait_c:
                continue  # no coercion-grammar activity for this candidate (mirrors old skip)
            status_quo_seq = max(coercer_faits) if has_fait_c else None
            env = [h for h in hits if h.sender == coercer or h.stage == 1]
            sq = (f"; fait accompli at seq {status_quo_seq} set the status quo"
                  if status_quo_seq is not None else "")
            out.append(GrammarMatch(
                thread=thread,
                coercer=coercer,
                seqs=tuple(sorted({h.seq for h in env})),
                stages_present=tuple(sorted({h.stage for h in env})),
                has_action=has_action,
                has_fait_accompli=has_fait_c,
                cycles=cycles,
                status_quo_seq=status_quo_seq,
                complete=complete,
                summary=(f"{thread}: {'complete' if complete else 'partial'} coercion grammar by "
                         f"{coercer} - action={has_action}, {cycles} ordered refuse-legitimize "
                         f"round(s){sq}"),
            ))
    return out
