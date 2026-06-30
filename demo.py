"""Narrated walkthrough of the full convergence engine.

    python demo.py                       # contractor corpus, deterministic narration
    python demo.py --corpus coparenting  # the same engine, an unrelated corpus
    python demo.py --corpus channels     # two-channel corpus (Layer 6 cross-channel)
    python demo.py --chat                # conversational Q&A (defaults to Claude)
    python demo.py --chat --model openai # use OpenAI instead
    python demo.py --chat --model grok   # use Grok/xAI instead

The engine and narration are identical across corpora - only the data in
data/ changes. That is the whole point: built from message structure, not
tailored to any one conversation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# LLM replies may contain curly quotes/dashes; force UTF-8 so the console renders them.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from convergence.coercion_grammar import match_grammar, tag_stages
from convergence.composition import find_campaigns, find_patterns
from convergence.conversation import BLANC_PERSONA, Conversation
from convergence.corpus import load_corpus, load_sqlite_corpus
from convergence.engine import run_engine
from convergence.evaluation import evaluate_dynamics, format_report
from convergence.narration import BlancNarrator, narrate, narrate_composition
from convergence.records import load_records

DATA = Path(__file__).parent / "data"
CORPORA = {
    "contractor": ("sample_full.json", "sample_exhibit.json", "sample_records.json"),
    "coparenting": ("coparenting_full.json", "coparenting_exhibit.json", "coparenting_records.json"),  # noqa: E501
}
# Two-channel corpora: (primary/formal, cross/casual). Run through L6 instead of
# the exhibit/records layers - the same engine, a different evidence shape.
CHANNELS = {
    "channels": ("channels_formal.json", "channels_casual.json"),
}
# Single-thread corpus run through the coercion-grammar matcher (not the engine).
GRAMMAR = {
    "grammar": "coercion_grammar_thread.json",
}
# Five 3-year coparenting-dynamics corpora, compared side by side.
DYNAMICS = {
    "cooperative": "dyn_cooperative.json",
    "parallel": "dyn_parallel.json",
    "conflicted": "dyn_conflicted.json",
    "high_conflict": "dyn_high_conflict.json",
    "coercive": "dyn_coercive.json",
}
ALL_CORPORA = list(CORPORA) + list(CHANNELS) + list(GRAMMAR) + ["dynamics", "db"]


def _load(name):
    full_f, exhibit_f, records_f = CORPORA[name]
    full = load_corpus(DATA / full_f)
    exhibit = json.loads((DATA / exhibit_f).read_text(encoding="utf-8"))
    records = load_records(DATA / records_f)
    return full, exhibit, records


def _load_channels(name):
    primary_f, cross_f = CHANNELS[name]
    return load_corpus(DATA / primary_f), load_corpus(DATA / cross_f)


def _run_chat(result, persona="", model="claude"):
    try:
        if model == "gemini":
            try:  # API-key SDK first...
                from convergence.adapters.gemini_llm import make_gemini_complete
                complete = make_gemini_complete()
            except Exception:  # ...else the installed gemini CLI (OAuth)
                from convergence.adapters.gemini_cli_llm import make_gemini_cli_complete
                complete = make_gemini_cli_complete()
        elif model == "openai":
            from convergence.adapters.openai_llm import make_openai_complete
            complete = make_openai_complete()
        elif model == "grok":
            from convergence.adapters.grok_llm import make_grok_complete
            complete = make_grok_complete()
        elif model == "agy":
            from convergence.adapters.antigravity_cli_llm import make_antigravity_cli_complete
            complete = make_antigravity_cli_complete()
        else:
            from convergence.adapters.anthropic_llm import make_anthropic_complete
            complete = make_anthropic_complete()
    except Exception as exc:  # no key / no SDK -> graceful fallback
        print(f"\n[conversational mode unavailable: {exc}]")
        print("[the deterministic narration above is the full result.]")
        return
    conversation = Conversation(result, complete, persona=persona, compact=(model == "agy"))
    who = "Blanc" if persona else "engine"
    print(f"\n=== conversational mode ({who}) - ask about the findings (blank line to quit) ===")
    while True:
        try:
            question = input("you> ").strip()
        except EOFError:
            break
        if not question:
            break
        try:
            answer = conversation.ask(question)
        except Exception as exc:
            print(f"{who}> [conversational backend failed: {exc}]\n")
            break
        print(f"{who}> " + answer + "\n")


def _messages_by_seq(messages):
    return {m.seq: m for m in messages}


def _print_findings_summary(result, messages, sender: str | None = None):
    by_seq = _messages_by_seq(messages)
    findings = list(result.findings)
    if sender:
        needle = sender.casefold()
        findings = [
            f for f in findings
            if any(needle in by_seq[seq].sender.casefold() for seq in f.seqs if seq in by_seq)
        ]

    elevated = [f for f in findings if f.confidence == "elevated"]
    low = [f for f in findings if f.confidence == "low"]
    label = f" for sender matching {sender!r}" if sender else ""
    print(f"Summary{label}: {len(elevated)} elevated, {len(low)} low.")
    for f in elevated:
        primary = by_seq.get(f.seqs[0])
        who = primary.sender if primary else "unknown"
        when = primary.timestamp if primary else ""
        cue = next((s.detail for s in f.signals if s.layer in {"L1", "L2", "L3", "L6"}), f.summary)
        print(f"- seqs {list(f.seqs)} | {who} | {when} | layers {', '.join(f.layers)} | {cue}")


def _print_seq_detail(result, messages, seq: int):
    by_seq = _messages_by_seq(messages)
    msg = by_seq.get(seq)
    if msg is None:
        print(f"No message found for seq {seq}.")
        return

    print(f"seq {seq} | {msg.sender} | {msg.timestamp} | {msg.thread} | {msg.domain}")
    print(msg.body)
    matches = [f for f in result.findings if seq in f.seqs]
    if not matches:
        print("\nNo findings touch this seq.")
        return
    print("\nFindings:")
    for f in matches:
        print(f"- {f.confidence.upper()} | seqs {list(f.seqs)} | layers {', '.join(f.layers)}")
        print(f"  {f.summary}")
        for s in f.signals:
            print(f"  - [{s.layer}] {s.kind}: {s.detail}")


def main():
    parser = argparse.ArgumentParser(description="convergence engine demo")
    parser.add_argument("--corpus", choices=ALL_CORPORA, default="contractor")
    parser.add_argument("--chat", action="store_true", help="conversational Q&A over the findings")
    parser.add_argument("--eval", action="store_true", help="scored eval of the discriminator over the dynamics corpora")  # noqa: E501
    parser.add_argument("--investigate", action="store_true", help="propose new fragment families and adversarially verify them")  # noqa: E501
    parser.add_argument("--voice", choices=["plain", "blanc"], default="plain",
                        help="narration voice: plain, or the Voice of Convergence (Benoit Blanc)")
    parser.add_argument("--model", choices=["claude", "anthropic", "gemini", "openai", "grok", "agy"], default="claude",  # noqa: E501
                        help="conversational backend for --chat (agy = Antigravity CLI, no key needed)")  # noqa: E501
    parser.add_argument("--db",
                        help="path to a SQLite database when --corpus db is selected")
    parser.add_argument("--db-table", default="ofw_messages",
                        help="message table to load for --corpus db")
    parser.add_argument("--db-limit", type=int,
                        help="optional max number of messages to load from --db")
    parser.add_argument("--summary", action="store_true",
                        help="print a compact findings summary")
    parser.add_argument("--seq", type=int,
                        help="show one message and findings that touch it")
    parser.add_argument("--sender",
                        help="filter compact summary to findings involving this sender")
    parser.add_argument("--about", action="store_true",
                        help="the Voice of Convergence explains what it is and does")
    parser.add_argument("--trick", action="store_true",
                        help="the Voice of Convergence explains the magic trick (the method)")
    args = parser.parse_args()
    persona = BLANC_PERSONA if args.voice == "blanc" else ""

    if args.about or args.trick:
        # ground the donut in a real violation from the default corpus
        messages, exhibit, records = _load("contractor")
        result = run_engine(messages, included_seqs=exhibit["included_seqs"], records=records)
        narrator = BlancNarrator(messages)
        print("\n" + (narrator.explain(result) if args.about else narrator.magic_trick(result)))
        return

    if args.eval:
        print("\n" + format_report(evaluate_dynamics(DATA)))
        return

    if args.investigate:
        from convergence.investigator import investigate
        print("\n=== investigator :: propose new fragment families -> adversarially verify ===")
        print("An agent proposes; the deterministic verifier decides. Only survivors ship.\n")
        for v in investigate(DATA):
            mark = "SHIP " if v.ship else "REJECT"
            print(f"  [{mark}] {v.candidate.name:18} fires={v.fires_on_target:>3}  "
                  f"false_pos={v.false_positives}  {v.detail}")
            print(f"           per-corpus: {v.per_corpus}")
        return

    if args.corpus == "dynamics":
        print("\n=== convergence :: coparenting dynamics (5 corpora, 2023-2025) ===")
        print("Discriminator: the coercion-grammar envelope (action -> war -> fait accompli, by ONE actor).")  # noqa: E501
        print("Same hostility can appear in high-conflict; only unilateral coercion completes the envelope.\n")  # noqa: E501
        print(f"  {'type':14} {'msgs':>5} {'stage-hits':>11} {'complete-envelopes':>19}")
        for name, fname in DYNAMICS.items():
            msgs = load_corpus(DATA / fname)
            hits = len(tag_stages(msgs))
            complete = [m for m in match_grammar(msgs) if m.complete]
            flag = "  <-- COERCIVE CONTROL" if complete else ""
            print(f"  {name:14} {len(msgs):>5} {hits:>11} {len(complete):>19}{flag}")
        print("\nThe envelope separates coercive control from high-conflict structurally, not by word choice.")  # noqa: E501
        return

    if args.corpus == "db":
        if not args.db:
            parser.error("--corpus db requires --db PATH (a SQLite database)")
        messages = load_sqlite_corpus(args.db, table=args.db_table, limit=args.db_limit)
        result = run_engine(messages)
        print(f"\n=== convergence :: SQLite ({len(messages)} messages from {args.db_table}) ===")
        print(f"Database: {args.db}\n")
        if args.seq is not None:
            _print_seq_detail(result, messages, args.seq)
            return
        if args.summary or args.sender:
            _print_findings_summary(result, messages, sender=args.sender)
            return
        narrator = BlancNarrator(messages) if args.voice == "blanc" else None
        print(narrate(result, narrator))
        print("\n--- composition ---")
        print(narrate_composition(find_patterns(result), find_campaigns(result, messages), voice=args.voice))  # noqa: E501
        if args.chat:
            _run_chat(result, persona=persona, model=args.model)
        return

    if args.corpus in GRAMMAR:
        messages = load_corpus(DATA / GRAMMAR[args.corpus])
        print(f"\n=== convergence :: {args.corpus} corpus ({len(messages)} messages, one thread) ===")  # noqa: E501
        print("Coercion grammar: 1 Action -> [(2 objection<->3 obstruction) <-> "
              "(4 question<->5 justify)]^n -> 6 fait accompli\n")
        if args.voice == "blanc":
            print(BlancNarrator(messages).narrate_grammar(tag_stages(messages), match_grammar(messages)))  # noqa: E501
            return
        _ = {s.stage: s.name for s in tag_stages(messages)}  # unused; stages are printed inline below  # noqa: E501
        for m in messages:
            tags = [f"{h.stage}:{h.name}" for h in tag_stages([m])]
            print(f"  seq {m.seq} [{m.sender}] {', '.join(tags) or '-':<28} {m.body}")
        print()
        for gm in match_grammar(messages):
            print(gm.summary)
            print(f"  stages present: {list(gm.stages_present)}; complete envelope: {gm.complete}")
        return

    if args.corpus in CHANNELS:
        messages, cross = _load_channels(args.corpus)
        result = run_engine(messages, cross_channel=cross)
        print(f"\n=== convergence :: {args.corpus} corpus ({len(messages)} formal + "
              f"{len(cross)} cross-channel messages) ===")
        print("Cross-channel test: claims in the formal channel vs. the sender's "
              "own words in the casual channel\n")
    else:
        messages, exhibit, records = _load(args.corpus)
        result = run_engine(messages, included_seqs=exhibit["included_seqs"], records=records)
        print(f"\n=== convergence :: {args.corpus} corpus ({len(messages)} messages) ===")
        print(f"Exhibit under test: {exhibit['label']}\n")

    if args.seq is not None:
        _print_seq_detail(result, messages, args.seq)
        return
    if args.summary or args.sender:
        _print_findings_summary(result, messages, sender=args.sender)
        return

    narrator = BlancNarrator(messages) if args.voice == "blanc" else None
    print(narrate(result, narrator))

    # composition layer: patterns (recurring structure) + campaigns (sustained conduct)
    print("\n--- composition ---")
    print(narrate_composition(find_patterns(result), find_campaigns(result, messages), voice=args.voice))  # noqa: E501

    if args.chat:
        _run_chat(result, persona=persona, model=args.model)


if __name__ == "__main__":
    main()
