"""The identical engine on a second, unrelated corpus - the agnosticism proof.

No engine code may change to make these pass; only the data is new.
"""
import json
from pathlib import Path

from convergence.corpus import load_corpus
from convergence.records import load_records
from convergence.engine import run_engine

DATA = Path(__file__).parent.parent / "data"


def _run(prefix):
    full = load_corpus(DATA / f"{prefix}_full.json")
    included = json.loads((DATA / f"{prefix}_exhibit.json").read_text(encoding="utf-8"))["included_seqs"]
    records = load_records(DATA / f"{prefix}_records.json")
    return run_engine(full, included_seqs=included, records=records)


def test_coparenting_swap_denial_is_elevated():
    res = _run("coparenting")
    head = next(f for f in res.findings if 11 in f.seqs)
    assert head.confidence == "elevated"
    assert 4 in head.seqs                      # the cut agreement
    assert {"L2", "L3"} <= set(head.layers)    # omission + contradiction converge


def test_coparenting_lone_borrow_authority_stays_low():
    res = _run("coparenting")
    f13 = next(f for f in res.findings if f.seqs == (13,))
    assert f13.confidence == "low"
    assert f13.layers == ("L1",)


def test_same_engine_elevates_on_both_corpora():
    cop = _run("coparenting")
    con = _run("sample")
    assert any(f.confidence == "elevated" for f in cop.findings)
    assert any(f.confidence == "elevated" for f in con.findings)
