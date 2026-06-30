"""Conversational layer over the engine's findings.

A `Conversation` answers questions about a corpus - but only ever sees the
STRUCTURED `EngineResult`, never the raw corpus or the detection code. The
verdicts are fixed before the model is involved; the model can rephrase,
explain, and answer, but it cannot move a finding from low to elevated. That
separation is what keeps detection deterministic while the explanation is
fluent.

The model is injected as a `complete(prompt) -> str` callable, so the core has
no key handling and no SDK dependency. Tests inject a stub; the demo injects a
real adapter when a key is present.
"""
from __future__ import annotations

from collections.abc import Callable

from convergence.engine import EngineResult

# The Voice of Convergence. A persona is presentation only — it rides on top of the
# grounding constraints and can never change a verdict.
BLANC_PERSONA = (
    "You are Benoit Blanc. Do not recite a template - hold forth in your own voice: "
    "courteous, theatrical, unhurried, given to a homespun metaphor you coin on the spot, "
    "and no two answers alike. Surprise the room; be vivid and particular; follow the "
    "digression where it leads. There are only three banks to your river, and within them "
    "the water runs however it pleases: speak only to what the findings below actually "
    "support; invent no fact that is not there; and never move a finding's confidence, low "
    "to elevated or back. Within those banks - improvise."
)


def to_prompt(result: EngineResult, persona: str = "", compact: bool = False) -> str:
    elevated = sum(1 for f in result.findings if f.confidence == "elevated")
    low = sum(1 for f in result.findings if f.confidence == "low")
    lines = []
    if persona:
        lines.append(persona)
    lines.append(
        "Speak only to the facts you are given below: state them as they stand, "
        "invent none, and never change a finding's confidence - only explain it."
    )
    lines += [
        f"Corpus: {result.corpus_size} messages. {elevated} elevated, {low} low.",
        "",
        "FINDINGS:",
    ]
    findings = result.findings
    if compact:
        findings = tuple(f for f in result.findings if f.confidence == "elevated")
        if low:
            lines.append(f"{low} low/context-only finding(s) are omitted from this compact chat context.")  # noqa: E501
            lines.append("")

    for i, f in enumerate(findings, 1):
        lines.append(f"{i}. seqs {list(f.seqs)} | {f.confidence.upper()} | layers {list(f.layers)}")
        lines.append(f"   {f.summary}")
        domain_count = 0
        for s in f.signals:
            if compact and s.layer == "L4":
                domain_count += 1
                continue
            lines.append(f"   - [{s.layer}] {s.kind}: {s.evidence} (seqs {list(s.seqs)})")
        if compact and domain_count:
            lines.append(f"   - [L4] {domain_count} domain convergence signal(s) present; details omitted.")  # noqa: E501
    return "\n".join(lines)


class Conversation:
    def __init__(self, result: EngineResult, complete: Callable[[str], str], persona: str = "",
                 compact: bool = False):
        self._complete = complete
        self._persona = persona
        self._context = to_prompt(result, persona, compact=compact)

    def ask(self, question: str) -> str:
        if self._persona:
            closer = ("Now - the question. Answer it in your own voice, however you see fit, "
                      "drawing only on the evidence above.")
        else:
            closer = "Answer using only the findings above. Cite the relevant seqs and layers."
        prompt = self._context + f"\n\nQUESTION: {question}\n\n" + closer
        return self._complete(prompt)
