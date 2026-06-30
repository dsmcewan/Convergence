from convergence.corpus import load_corpus
from convergence.engine import run_engine
from convergence.records import load_records
from web.curated import serialize_corpus
from web.serialize import DATA, serialize_dynamics


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


def test_serialized_engine_core_is_blanc_free():
    from web.serialize import serialize_engine
    core = serialize_engine("coparenting")
    assert core["corpus"]["name"] == "coparenting"
    assert core["messages"]
    assert set(core["narration"]) == {"plain"}
    assert set(core["composition_narration"]) == {"plain"}
    assert "curated" not in core
    assert all("blanc" not in f.get("narration", {}) for f in core["findings"])
    assert all({"seqs", "confidence", "layers", "signals", "messages"} <= set(f) for f in core["findings"])  # noqa: E501


def test_composed_corpus_has_curated_section():
    payload = serialize_corpus("coparenting")
    # generic core present
    assert set(payload["narration"]) == {"plain"}
    # curated section present and aligned
    cur = payload["curated"]
    assert isinstance(cur["narration_blanc"], str) and cur["narration_blanc"]
    assert isinstance(cur["composition_blanc"], str)
    assert len(cur["finding_blanc"]) == len(payload["findings"])


def test_serialize_module_has_no_blanc_dependency():
    import web.serialize as s
    src = __import__("inspect").getsource(s)
    assert "BlancNarrator" not in src
    assert "import web.curated" not in src and "from web.curated" not in src


def test_serialized_dynamics_scorecard_is_perfect_for_demo_corpora():
    payload = serialize_dynamics()

    assert len(payload["rows"]) == 5
    assert payload["scorecard"]["precision"] == 1.0
    assert payload["scorecard"]["recall"] == 1.0
    assert payload["scorecard"]["specificity"] == 1.0
    assert payload["hard_negative"]["name"] == "high_conflict"


def test_signal_json_includes_provenance_fields():
    from web.curated import serialize_corpus
    data = serialize_corpus("contractor")
    sigs = [s for f in data["findings"] for s in f["signals"]]
    assert sigs, "contractor corpus should produce signals"
    for s in sigs:
        # additive provenance — existing keys still present
        assert {"layer", "seqs", "kind", "detail"} <= set(s)
        # new keys
        assert {"actor", "thread", "target", "anchor"} <= set(s)
        assert isinstance(s["actor"], str) and isinstance(s["thread"], str)
        assert s["anchor"] in s["seqs"]
        assert s["target"] is None or isinstance(s["target"], str)
