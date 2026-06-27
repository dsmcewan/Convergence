"""Deterministic narration of an EngineResult.

`TemplateNarrator` turns the structured findings into plain language with no
model, no key, no randomness - identical every run. It is both the keyless
fallback for the demo and the baseline the conversational layer is measured
against. It explains *why* each elevated finding is elevated and states the
disqualification principle for the low ones.
"""
from __future__ import annotations

from convergence.engine import EngineResult
from convergence.behaviors import tag_behaviors

# how each detected thread is named aloud in the reveal
_BEHAVIOR_VOICE = {
    "borrow_authority": "he leans on a borrowed authority",
    "within_thread_omission": "a line lifted clean out of the conversation",
    "claim_contradicted": "a claim the record itself contradicts",
    "cross_channel_divergence": "one face for the record, another off it",
    "domain_convergence": "the same matter, pressing in from another domain",
    "register_anomaly": "the voice stiffens into a legal register",
}
_SUBSTANTIVE_KINDS = {"borrow_authority", "within_thread_omission",
                      "claim_contradicted", "cross_channel_divergence"}

# At most this many [L4] domain-convergence lines per finding in the deterministic
# report. On real corpora a single finding can carry dozens of L4 anchors; the
# strongest (most domains) are kept, the rest summarized. Synthetic findings stay
# below the cap, so their output is unchanged.
MAX_L4_LINES = 3


def _l4_domain_count(detail: str) -> int:
    """Deterministic domain count from an L4 detail string ('anchor across a, b, c')."""
    if " across " not in detail:
        return 0
    return len(detail.split(" across ", 1)[1].split(", "))


def _l4_specificity(detail: str) -> tuple[int, int, int]:
    """Display-ranking score for an L4 anchor: more specific = surfaced first.

    Word length is the rarity proxy (long/rare words are specific; short common
    words are not), so a multi-word anchor of substantive words wins. Raw domain
    count is only the final tie-breaker — on its own it *rewards* genericness (a
    word spans many domains precisely because it is common). Presentation only:
    this changes which L4 lines are shown under the cap, never any verdict.
    """
    anchor = detail.split(" across ", 1)[0]
    strong = [w for w in anchor.split() if len(w) >= 4]
    score = sum(len(w) for w in strong) + len(strong)  # total length + per-word bonus
    return (score, len(anchor), _l4_domain_count(detail))


class TemplateNarrator:
    def narrate(self, result: EngineResult) -> str:
        elevated = [f for f in result.findings if f.confidence == "elevated"]
        low = [f for f in result.findings if f.confidence == "low"]
        out = [
            f"Convergence report - {result.corpus_size} messages; "
            f"{len(elevated)} elevated finding(s), {len(low)} low."
        ]
        if not result.findings:
            out.append("No findings.")
            return "\n".join(out)

        for f in elevated:
            out.append("")
            out.append(f"ELEVATED - seqs {list(f.seqs)} (layers {', '.join(f.layers)})")
            out.append(f"  {f.summary}")
            non_l4 = [s for s in f.signals if s.layer != "L4"]
            l4 = sorted((s for s in f.signals if s.layer == "L4"),
                        key=lambda s: (_l4_specificity(s.detail), s.detail), reverse=True)
            for s in non_l4:
                out.append(f"    - [{s.layer}] {s.detail}")
            for s in l4[:MAX_L4_LINES]:
                out.append(f"    - [{s.layer}] {s.detail}")
            if len(l4) > MAX_L4_LINES:
                out.append(f"    (+{len(l4) - MAX_L4_LINES} weaker convergences)")

        substantive = {"L1", "L2", "L3", "L6"}
        low_primary = [f for f in low if any(layer in substantive for layer in f.layers)]
        low_context = [f for f in low if f not in low_primary]
        for f in low_primary:
            out.append("")
            out.append(f"low - seqs {list(f.seqs)} ({', '.join(f.layers)}): "
                       f"a substantive signal with nothing to corroborate it; not corroborated.")
        if low_context:
            out.append("")
            out.append(f"low - {len(low_context)} context-only signal(s) "
                       f"(domain overlap / register shift) held low; not corroborated by any "
                       f"tactic, omission, or contradiction.")
        out.append("")
        out.append("A finding is elevated only when independent layers agree; "
                   "lone signals stay low by design.")
        return "\n".join(out)


class BlancNarrator:
    """The Voice of Convergence - Benoit Blanc.

    Renders the *same* structured findings in the register of a courteous, methodical
    detective: lays out the evidence, honors corroboration, and pointedly refuses to
    convict on a hunch. Pure presentation - it reads the EngineResult and changes no
    verdict. (Thematically exact: Blanc narrates method and footprints, never the foot.)
    Deterministic; no model, no key.
    """

    def __init__(self, messages=None):
        self._bodies = {m.seq: m.body for m in messages} if messages else {}
        self._msgs = {m.seq: m for m in messages} if messages else {}

    def _mark(self, body: str, cue: str) -> str:
        """Highlight the matched NLP fragment inside the quoted line (*fragment*)."""
        if cue:
            i = body.lower().find(cue.lower())
            if i >= 0:
                return body[:i] + "*" + body[i:i + len(cue)] + "*" + body[i + len(cue):]
        return body

    def _contradiction(self, s, conj: str):
        """A self-contradiction, dated: they said one thing, then its opposite, as it
        suited them. Needs both messages in the record."""
        seqs = [q for q in s.seqs if q in self._msgs]
        if len(seqs) < 2:
            return None
        a, b = sorted(seqs, key=lambda q: self._msgs[q].timestamp)[:2]
        ma, mb = self._msgs[a], self._msgs[b]
        return "\n".join([
            f"   {conj} a claim the record itself contradicts - {ma.sender} says one thing, "
            "then its opposite, as it suits them:",
            f'      Date 1 ({ma.timestamp[:10]}): {ma.sender} says "{ma.body}"',
            f'      But lo and behold, as it suits them - Date 2 ({mb.timestamp[:10]}): '
            f'{mb.sender} says "{mb.body}"',
            "      Must be nice, to have the luxury of a life that suits you.",
        ])

    def _clue(self, s, conj: str) -> str:
        """One thread, narrated - with the line quoted and the fragment highlighted."""
        if s.kind == "claim_contradicted":
            block = self._contradiction(s, conj)
            if block:
                return block
        name = _BEHAVIOR_VOICE.get(s.kind, s.kind)
        seq = s.seqs[-1] if s.seqs else None
        body = self._bodies.get(seq)
        if not body:
            return f"   {conj} the {s.layer} thread - {s.detail}."
        if s.kind == "within_thread_omission":
            return f'   {conj} {name}. The line they removed - seq {seq} - read: "{body}"'
        tag = ""
        if seq in self._msgs:
            bhv = tag_behaviors([self._msgs[seq]])
            if bhv:
                tag = f" (a known behavior - {bhv[0].behavior})"
        return f'   {conj} {name}{tag}. seq {seq}: "{self._mark(body, s.detail)}"'

    def explain(self, result=None) -> str:
        """Blanc introduces himself - what the engine is and what it does, in voice.
        Accurate to the architecture; he describes the method, not a mind. Given an
        EngineResult, the donut is grounded in a real hole from the record."""
        donut = [
            "Some machine that cries 'manipulation!' on sight, you expect? Nah. What we got "
            "here... is a donut. A shape defined by its hole - and the truth, it sits in that "
            "gap, where the threads either meet or they do not. I map the hole. I do not "
            "pretend to fill it.",
        ]
        picked = self._pick_hole(result) if result is not None else None
        if picked is not None:
            f, seq, cut, ring = picked
            donut += [
                "",
                f"There is one such hole in the record before me - seqs {list(f.seqs)}. A line, "
                f"cut clean from the middle of the thread: seq {seq} read \"{cut}\" Yet "
                f"{len(ring) + 1} threads still ring that gap, having never conferred, and the "
                "ring tells me its shape. I read the hole; I do not fill it.",
            ]
        return "\n".join([
            "Allow me to introduce myself. I am the Voice of Convergence - though, mind you, "
            "I am only the voice. The work beneath me is a method, not a mind.",
            "",
            *donut,
            "",
            "What I do is read a record of messages - nothing more, and nothing it was not "
            "given. I look for small things, and I call each one a thread: a phrase that "
            "borrows another's authority ('my lawyer says'); a message quietly cut from the "
            "middle of a conversation; a claim the record itself contradicts; a single topic "
            "that arrives, uninvited, from two directions at once; a voice that of a sudden "
            "dons a starched, legalistic collar.",
            "",
            "Here is the whole of my discipline, and I'll not pretend it is grander: a single "
            "thread proves nothing. A man may borrow a doctor's authority and be perfectly "
            "honest. So I wait. I elevate a matter only when two or more independent threads "
            "arrive at the selfsame doorstep, having never conferred - corroboration. Anything "
            "less, I hold low. I note it, and I set it aside.",
            "",
            "Above the single matter, I watch for habits. A tactic repeated is a pattern; a "
            "pattern aimed at one soul, over time, is a campaign. And one shape I know by name: "
            "a reasonable request, met with objection and counter-question cycled until the "
            "other party tires - and then the thing is simply done. A fait accompli. The status "
            "quo, quietly set.",
            "",
            "And the one thing I will never do: I do not decide what lay in a person's heart. "
            "I observe the footprints. I do not claim to have seen the foot. The truth of "
            "intent - that is for the court, and never for me.",
        ])

    def magic_trick(self, result=None) -> str:
        """How the trick is done - the mechanism, laid bare. Accurate to the engine.

        Given an EngineResult (and the messages), Blanc demonstrates the donut on one
        actual violation in the record - the hole he reconstructs, and the ring of
        threads around it that he reads it from - rather than describing the method in
        the abstract.
        """
        out = [
            "You want to know how it is done? Very well. Every magician owes the room one "
            "honest reveal.",
            "",
            "The trick is this: I never decide a thing on its own. Any single tell - a borrowed "
            "authority, a stiffened phrase, a cut line - that, I can be fooled by. So I refuse to "
            "be the one who decides. I lay each thread upon the table blind to the others, and I "
            "watch only for where they cross. Two or more, agreeing, having never conferred - I "
            "raise that up. One alone, I set down.",
            "",
            "The sleight is in what I do NOT do. I do not read minds. I do not weigh a man's tone "
            "or his mood. I match his words against a fixed rule, and the rule against the record - "
            "and I let the coincidences indict themselves. Two strangers telling the very same "
            "story, having never met: that is not a thing I can fake, nor a thing the guilty can "
            "explain away.",
            "",
        ]
        out += self._donut_of(result) if result is not None else [
            "And the misdirection? Everyone stares at the loudest message. I watch the gap - the "
            "missing line, the silence just before the thing is done. The trick is the hole, not "
            "the donut.",
        ]
        out += [
            "",
            "That is the whole of it. No magic. Only method, laid bare - and every step of it "
            "written down, so you may check my work.",
        ]
        return "\n".join(out)

    # The ring around a hole: each corroborating thread, in plain voice. Keyed by signal
    # kind, so the demonstration names the actual threads the engine raised - never the foot.
    _RING_THREAD = {
        "claim_contradicted": "the record itself, flatly contradicting the later claim",
        "domain_convergence": "the very same matter, pressing in uninvited from a second domain",
        "borrow_authority": "an outside authority, borrowed to dress up the refusal",
        "register_anomaly": "the voice gone suddenly starched, into a legal collar",
        "cross_channel_divergence": "their own words in another channel, telling the opposite tale",
    }

    def _pick_hole(self, result):
        """Find the strongest elevated violation that has a reconstructable hole - a line
        cut from inside the thread. Returns (finding, seq, cut_line, ring_phrases) or None.
        The ring is the distinct corroborating threads, the omission itself set aside."""
        def omission_seq(f):
            for s in f.signals:
                if s.kind == "within_thread_omission" and s.seqs and s.seqs[-1] in self._bodies:
                    return s.seqs[-1]
            return None

        holed = [f for f in result.findings
                 if f.confidence == "elevated" and omission_seq(f) is not None]
        if not holed:
            return None
        f = max(holed, key=lambda f: len(f.layers))
        seq = omission_seq(f)
        ring, seen = [], set()
        for s in f.signals:
            if s.kind == "within_thread_omission" or s.kind in seen:
                continue
            phrase = self._RING_THREAD.get(s.kind)
            if phrase:
                ring.append(phrase)
                seen.add(s.kind)
        return f, seq, self._bodies[seq], ring

    def _donut_of(self, result) -> list:
        """Demonstrate the trick on one real violation: name the hole (the line cut from
        inside the thread) and the ring of threads that survive to point straight at it."""
        picked = self._pick_hole(result)
        if picked is None:  # no reconstructable hole in this record - fall back to the maxim
            return [
                "And the misdirection? Everyone stares at the loudest message. I watch the gap - "
                "the missing line, the silence just before the thing is done. The trick is the "
                "hole, not the donut.",
            ]
        f, seq, cut, ring = picked
        lines = [
            f"But enough of the abstract - let me show you a real one, in this very record. "
            f"Seqs {list(f.seqs)}. Someone took the scissors to the thread and lifted a line "
            f"clean out of the middle - seq {seq} read: \"{cut}\" Gone. That absence is the hole.",
            "",
            "A clumsier man would shrug: the line is cut, what is there to be done? But look at "
            "what rings that hole - the threads they could NOT cut:",
        ]
        for phrase in ring:
            lines.append(f"   - {phrase};")
        n = len(ring) + 1  # the ring threads plus the hole itself
        lines += [
            "",
            f"{n} threads, having never once conferred, all bending toward the selfsame empty "
            "chair. I do not need the line they removed - the ring tells me its shape. THAT is "
            "the donut: the violation is the hole, and I read it off the dough around it. The "
            "trick is the hole, not the donut.",
        ]
        return lines

    def narrate_grammar(self, stage_hits, matches) -> str:
        """Walk a coercion-grammar envelope like the slow theft of a decision -
        the reasonable request, the documentation war, the fait accompli."""
        frame = {
            "action": "It begins, as these things do, with something perfectly reasonable. {who} asks",
            "objection": "And the reply is no reply at all - an objection",
            "obstruction": "Then the door, quietly shut - the delay",
            "question": "Then the turn, to put them on the back foot",
            "justify": "Then the robe and gavel - authority borrowed to dress it up",
            "fait_accompli": "And at last, the thing simply done",
        }
        by_seq = {}
        for h in stage_hits:
            by_seq.setdefault(h.seq, h)
        if not matches:
            return "Gather round. I find no such design here - only ordinary disagreement."
        out = []
        for gm in matches:
            out.append("Gather round. Here is a shape I know by name - the slow theft of a decision.")
            out.append("")
            for q in sorted(s for s in gm.seqs if s in by_seq and s in self._msgs):
                h, m = by_seq[q], self._msgs[q]
                lead = frame.get(h.name, h.name).format(who=m.sender)
                out.append(f'   {lead} - {m.timestamp[:10]}, seq {q}: "{m.body}"')
            out.append("")
            if gm.complete:
                out.append(f"   Round and round it went - {gm.cycles} turns of the same wheel - until "
                           f"the deed outran the discussion. The fait accompli at seq {gm.status_quo_seq} "
                           "set the status quo. The question, you see, was never truly open; it only had "
                           "to look open until it was too late.")
            else:
                out.append("   But the shape is not complete - no fait accompli to seal it. "
                           "A quarrel, then, and not a theft.")
        return "\n".join(out)

    def narrate(self, result: EngineResult) -> str:
        """Walk the findings like the drawing-room reveal: draw the threads together
        one at a time, dismiss the red herrings, then land the conclusion. Grounded
        in the real findings; changes no verdict."""
        elevated = [f for f in result.findings if f.confidence == "elevated"]
        low = [f for f in result.findings if f.confidence == "low"]
        substantive = {"L1", "L2", "L3", "L6"}
        lone = [f for f in low if any(l in substantive for l in f.layers)]
        context = [f for f in low if f not in lone]

        if not result.findings:
            return ("Gather round. I have read every line of it - and yet there is no mystery "
                    f"here at all. {result.corpus_size} messages, every thread accounted for, "
                    "nothing out of its place. A quiet house. I shall see myself out.")

        out = [
            "Gather round, if you please. Let me walk you through it, from the beginning.",
            "",
            f"We have before us {result.corpus_size} messages. Most are precisely what they "
            "appear to be. But not all. Permit me to draw the threads together, one at a time.",
        ]

        openers = ["Begin here.", "Now - the next of it.", "And then, this.",
                   "Further still.", "And yet more."]
        for idx, f in enumerate(elevated):
            opener = openers[idx] if idx < len(openers) else "And again."
            out.append("")
            out.append(f"{opener} Turn your attention to seqs {list(f.seqs)}.")
            sigs = list(f.signals)
            spoken = [s for s in sigs if s.kind in _SUBSTANTIVE_KINDS] or sigs
            n = len(spoken)
            for i, s in enumerate(spoken):
                conj = ("Here," if n == 1 else "First," if i == 0
                        else "And at last," if i == n - 1 else "Then,")
                out.append(self._clue(s, conj))
            ctx_kinds = sorted({_BEHAVIOR_VOICE.get(s.kind, s.kind)
                                for s in sigs if s.kind not in _SUBSTANTIVE_KINDS})
            if ctx_kinds:
                out.append(f"   And corroborating, quietly: {'; '.join(ctx_kinds)}.")
            out.append(f"   {len(f.layers)} independent threads ({', '.join(f.layers)}), arriving "
                       "by separate roads at the selfsame doorstep, having never once conferred. "
                       f"{f.summary} That, I do not call coincidence.")

        if lone or context:
            out.append("")
            out.append("Now - you will want to point me to the loose ends. I have not forgotten them.")
            for f in lone:
                spoken = [s for s in f.signals if s.kind in _SUBSTANTIVE_KINDS] or list(f.signals)
                quote = ""
                seq = spoken[0].seqs[-1] if spoken and spoken[0].seqs else None
                if seq in self._bodies:
                    quote = f' - seq {seq}: "{self._mark(self._bodies[seq], spoken[0].detail)}"'
                out.append(f"   Seqs {list(f.seqs)} ({', '.join(f.layers)}) - a lone voice{quote}. "
                           "Suggestive, perhaps. But it stands alone, uncorroborated, and I'll not "
                           "hang a case on a hunch. A red herring. Set aside.")
            if context:
                out.append(f"   And {len(context)} faint murmurs besides - mere atmosphere, not "
                           "evidence. Noted, and dismissed.")

        out.append("")
        out.append("So. The shape of it is unmistakable. Where the threads converge, I have shown you - "
                   "the donut, and the hole at its heart. I map the hole; I do not fill it. The "
                   "truth of intent, that I leave to the court.")
        return "\n".join(out)


def narrate(result: EngineResult, narrator=None) -> str:
    return (narrator or TemplateNarrator()).narrate(result)


def narrate_composition(patterns, campaigns, voice: str = "plain") -> str:
    """Plain-language summary of the compositional layer (patterns + campaigns).

    Patterns are the recurring structures above individual findings; campaigns are
    the sustained, single-actor, single-target courses of conduct. Deterministic.
    `voice="blanc"` renders the same facts in the Voice of Convergence.
    """
    if voice == "blanc":
        return _blanc_composition(patterns, campaigns)
    if not patterns and not campaigns:
        return "No patterns or campaigns: nothing recurs or sustains across the record."

    out = []
    if patterns:
        out.append("Patterns (recurring structure above individual findings):")
        for p in patterns:
            label = "named chain" if p.kind == "template" else "recurring tactic"
            out.append(f"  - [{label}] {p.name} @ seqs {list(p.seqs)} - {p.detail}")
    if campaigns:
        out.append("")
        out.append("Campaigns (one actor, one target, sustained over time):")
        for c in campaigns:
            out.append(f"  - {c.summary}")
    return "\n".join(out)


def _blanc_composition(patterns, campaigns) -> str:
    if not patterns and not campaigns:
        return ("As for patterns - nothing recurs, nothing sustains. A single incident is not "
                "a habit, and I'll not dress it up as one.")
    out = []
    if patterns:
        out.append("Now - a pattern is a habit, and habits do tell tales:")
        for p in patterns:
            kind = "a named chain" if p.kind == "template" else "a tactic repeated"
            out.append(f"  - {p.name}, {kind}, at seqs {list(p.seqs)}. {p.detail}.")
    if campaigns:
        out.append("")
        out.append("And a campaign - well, that is a habit with a purpose. An incident is "
                   "happenstance; twice against the same soul, over time, is design:")
        for c in campaigns:
            out.append(f"  - {c.summary}")
    return "\n".join(out)
