from pathlib import Path

from convergence.records import Record, load_records

DATA = Path(__file__).parent.parent / "data" / "sample_records.json"


def test_loads_sample_records():
    recs = load_records(DATA)
    assert all(isinstance(r, Record) for r in recs)
    assert any(r.predicate == "agreed_to_extra_hours" and r.value is True and r.source_seq == 3 for r in recs)  # noqa: E501
