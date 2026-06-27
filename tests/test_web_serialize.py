from convergence.engine import run_engine
from convergence.records import load_records
from convergence.corpus import load_corpus
from web.serialize import DATA, serialize_corpus, serialize_dynamics


def test_serialized_elevated_seqs_match_engine():
    messages = load_corpus(DATA / "sample_full.json")
    records = load_records(DATA / "sample_records.json")
    result = run_engine(
        messages,
        included_seqs={1, 2, 4, 6, 7, 8, 9, 10, 12, 13, 14},
        records=records,
    )
    payload = serialize_corpus("contractor")

    engine_seqs = [list(f.seqs) for f in result.findings if f.confidence == "elevated"]
    web_seqs = [f["seqs"] for f in payload["findings"] if f["confidence"] == "elevated"]

    assert web_seqs == engine_seqs


def test_serialized_corpus_has_frontend_contract():
    payload = serialize_corpus("coparenting")

    assert payload["corpus"]["name"] == "coparenting"
    assert payload["messages"]
    assert {"plain", "blanc"} <= set(payload["narration"])
    assert {"plain", "blanc"} <= set(payload["composition_narration"])
    assert all({"seqs", "confidence", "layers", "signals", "messages"} <= set(f) for f in payload["findings"])


def test_serialized_dynamics_scorecard_is_perfect_for_demo_corpora():
    payload = serialize_dynamics()

    assert len(payload["rows"]) == 5
    assert payload["scorecard"]["precision"] == 1.0
    assert payload["scorecard"]["recall"] == 1.0
    assert payload["scorecard"]["specificity"] == 1.0
    assert payload["hard_negative"]["name"] == "high_conflict"

