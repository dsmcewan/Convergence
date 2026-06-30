"""The five coparenting-dynamics corpora and the engine's discrimination.

Five synthetic 3-year records (cooperative, parallel, conflicted, high-conflict,
coercive), each encoding the structural DNA of its type per the literature
(Maccoby & Mnookin; Ahrons; Kelly & Johnson; Hardesty; Stark). The headline claim
the engine must satisfy: the coercion-grammar envelope (action -> documentation war
-> fait accompli, by ONE actor) fires on the coercive corpus and on NO other -
including high-conflict, which is equally hostile but *bilateral*. The discriminator
is structure (asymmetry), not vocabulary. Synthetic data only.
"""
from pathlib import Path

from convergence.coercion_grammar import match_grammar, tag_stages
from convergence.corpus import load_corpus

DATA = Path(__file__).parent.parent / "data"

CORPORA = {
    "cooperative": "dyn_cooperative.json",
    "parallel": "dyn_parallel.json",
    "conflicted": "dyn_conflicted.json",
    "high_conflict": "dyn_high_conflict.json",
    "coercive": "dyn_coercive.json",
}


def _complete(name):
    msgs = load_corpus(DATA / CORPORA[name])
    return [m for m in match_grammar(msgs) if m.complete]


def test_only_coercive_yields_complete_envelopes():
    for name in CORPORA:
        complete = _complete(name)
        if name == "coercive":
            assert len(complete) >= 1, "coercive must contain the full coercion-grammar envelope"
        else:
            assert complete == [], f"{name} must NOT contain a complete coercion envelope"


def test_coercive_has_two_envelopes_across_three_years():
    # the 2023 preschool and 2025 summer/relocation fait-accompli envelopes
    complete = _complete("coercive")
    threads = {m.thread for m in complete}
    assert {"preschool", "summer"} <= threads


def test_high_conflict_is_hot_but_not_coercive_grammar():
    # the centerpiece: high-conflict has stage activity (it is hostile) yet no
    # complete envelope (the escalation is bilateral, not a one-actor campaign)
    msgs = load_corpus(DATA / CORPORA["high_conflict"])
    assert tag_stages(msgs) != [], "high-conflict should still show stage activity"
    assert _complete("high_conflict") == []


def test_cooperative_and_parallel_are_quiet():
    assert _complete("cooperative") == []
    assert _complete("parallel") == []


def test_coercive_envelopes_are_single_coercer():
    complete = _complete("coercive")
    assert complete, "coercive must still complete under the sender-aware machine"
    assert all(m.coercer == "Victor" for m in complete)  # one coercer drives every envelope


def test_coercive_fait_accompli_sets_status_quo():
    # each complete envelope marks the seq where the fait accompli set the status quo
    for m in _complete("coercive"):
        assert m.status_quo_seq is not None


def test_all_corpora_span_three_years():
    for name, fname in CORPORA.items():
        msgs = load_corpus(DATA / fname)
        years = {int(m.timestamp[:4]) for m in msgs}
        assert min(years) == 2023 and max(years) == 2025, f"{name} should span 2023-2025"


def test_every_corpus_documented_in_dynamics_md():
    doc = (DATA.parent / "DYNAMICS.md").read_text(encoding="utf-8")
    for name, fname in CORPORA.items():
        stem = fname.replace(".json", "")
        assert stem in doc, f"DYNAMICS.md missing corpus {stem}"
        assert name.replace("_", "-") in doc or name in doc, f"DYNAMICS.md missing type {name}"
