"""Loaders for message corpora: JSON, SQLite exports and documentary ids.

The SQLite loader is how real data reaches the engine, and it was the least-tested code in the
package. These tests build small throwaway databases, so every branch (missing columns, null
fields, empty messages, unsafe names, the row limit) is exercised without any private data.
"""
import json
import sqlite3

import pytest

from convergence.corpus import (
    Message,
    _parse_ids,
    load_corpus,
    load_documentary_ids,
    load_sqlite_corpus,
)

COLUMNS = ("ID INTEGER, date_time TEXT, sent_by TEXT, subject TEXT, ofw_message_text TEXT, "
           "primary_domain TEXT, behavior_cluster TEXT")


def make_db(tmp_path, rows, table="ofw_messages", columns=COLUMNS):
    path = tmp_path / "export.db"
    con = sqlite3.connect(path)
    con.execute(f'CREATE TABLE "{table}" ({columns})')
    marks = ",".join("?" * len(rows[0])) if rows else ""
    for row in rows:
        con.execute(f'INSERT INTO "{table}" VALUES ({marks})', row)
    con.commit()
    con.close()
    return path


ROWS = [
    (3, "2025-03-03T10:00", "Bea", "Billing", "third message", "payment", None),
    (1, "2025-03-03T09:00", "Al", "Scope", "first message", "", "cluster-x"),
    (2, "2025-03-03T09:30", None, None, "second message", None, None),
    (4, None, "Cy", "Scope", "   ", "scope", None),       # whitespace only: dropped
    (5, "2025-03-04T08:00", "Al", "Scope", None, "scope", None),  # no text: dropped
]


def test_load_corpus_sorts_by_seq_whatever_order_the_file_has(tmp_path):
    rows = [{"seq": s, "thread": "t", "sender": "x", "timestamp": "ts", "domain": "d",
             "body": f"m{s}"} for s in (3, 1, 2)]
    path = tmp_path / "c.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    msgs = load_corpus(path)
    assert [m.seq for m in msgs] == [1, 2, 3]
    assert all(isinstance(m, Message) for m in msgs)


def test_sqlite_rows_become_messages_ordered_by_id_with_defaults_for_missing_fields(tmp_path):
    msgs = load_sqlite_corpus(make_db(tmp_path, ROWS))
    assert [m.seq for m in msgs] == [1, 2, 3]  # rows 4 and 5 have no usable text
    first, second, third = msgs
    assert (first.sender, first.thread, first.timestamp, first.body) == (
        "Al", "Scope", "2025-03-03T09:00", "first message")
    # No sender, subject or date: the stated defaults, not None or an error.
    assert (second.sender, second.thread, second.timestamp) == (
        "unknown", "thread", "2025-03-03T09:30")
    assert third.thread == "Billing"


def test_the_domain_is_the_first_non_empty_of_primary_domain_then_cluster_else_general(tmp_path):
    first, second, third = load_sqlite_corpus(make_db(tmp_path, ROWS))
    assert first.domain == "cluster-x"   # primary_domain is "" so the cluster is used
    assert second.domain == "GENERAL"    # both null
    assert third.domain == "payment"     # primary_domain wins when present


def test_a_table_without_domain_columns_gets_the_general_domain(tmp_path):
    cols = "ID INTEGER, date_time TEXT, sent_by TEXT, subject TEXT, ofw_message_text TEXT"
    db = make_db(tmp_path, [(1, "t", "Al", "S", "hello")], columns=cols)
    assert [m.domain for m in load_sqlite_corpus(db)] == ["GENERAL"]


def test_the_row_limit_keeps_the_lowest_ids(tmp_path):
    db = make_db(tmp_path, ROWS)
    assert [m.seq for m in load_sqlite_corpus(db, limit=2)] == [1, 2]
    assert [m.seq for m in load_sqlite_corpus(db, limit=0)] == []


def test_another_table_name_can_be_loaded(tmp_path):
    db = make_db(tmp_path, [(7, "t", "Al", "S", "hello", None, None)], table="msgs")
    assert [m.seq for m in load_sqlite_corpus(db, table="msgs")] == [7]


def test_missing_required_columns_are_named_in_the_error(tmp_path):
    db = make_db(tmp_path, [(1, "hello")], columns="ID INTEGER, ofw_message_text TEXT")
    with pytest.raises(ValueError, match=r"missing columns: \['date_time', 'sent_by', 'subject'\]"):
        load_sqlite_corpus(db)


def test_a_missing_file_is_an_error_and_is_not_created(tmp_path):
    ghost = tmp_path / "nope.db"
    with pytest.raises(FileNotFoundError, match="SQLite database not found"):
        load_sqlite_corpus(ghost)
    assert not ghost.exists()


@pytest.mark.parametrize("name", ['x"; DROP TABLE ofw_messages; --', "a b", "t-1", ""])
def test_an_unsafe_table_name_is_refused_before_any_query(tmp_path, name):
    db = make_db(tmp_path, ROWS)
    with pytest.raises(ValueError, match="unsafe table name"):
        load_sqlite_corpus(db, table=name)
    assert len(load_sqlite_corpus(db)) == 3  # and the data is untouched


def test_the_database_is_opened_read_only(tmp_path):
    db = make_db(tmp_path, ROWS)
    before = db.read_bytes()
    load_sqlite_corpus(db)
    assert db.read_bytes() == before


# ---- documentary ids ---------------------------------------------------------------------------


@pytest.mark.parametrize("value, expected", [
    (None, set()),
    (5, {5}),
    ("1, 2;3 4", {1, 2, 3, 4}),
    ("12,x,7", {12, 7}),
    ("-1, 2.5, abc", set()),
    ("", set()),
    ("  9  ", {9}),
])
def test_parse_ids_takes_whole_non_negative_integers_from_any_separator(value, expected):
    assert _parse_ids(value) == expected


def evidence_db(tmp_path):
    path = tmp_path / "evidence.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE exhibits (message_ids TEXT, note TEXT)")
    con.execute("CREATE TABLE links (msg_id INTEGER)")
    con.executemany("INSERT INTO exhibits VALUES (?, ?)",
                    [("1, 2;3", "a"), (None, "b"), ("x, 40", "c")])
    con.executemany("INSERT INTO links VALUES (?)", [(5,), (None,)])
    con.commit()
    con.close()
    return path


def test_documentary_ids_are_collected_from_each_source_that_exists(tmp_path):
    ids = load_documentary_ids(evidence_db(tmp_path),
                               [("exhibits", "message_ids"), ("links", "msg_id")])
    assert ids == {1, 2, 3, 40, 5}


def test_a_source_with_no_such_table_or_column_is_skipped_not_an_error(tmp_path):
    db = evidence_db(tmp_path)
    assert load_documentary_ids(db, [("nope", "message_ids"), ("exhibits", "nope")]) == set()
    assert load_documentary_ids(db, [("nope", "x"), ("links", "msg_id")]) == {5}
    assert load_documentary_ids(db, []) == set()


def test_unsafe_source_names_and_a_missing_file_are_refused(tmp_path):
    db = evidence_db(tmp_path)
    with pytest.raises(ValueError, match="unsafe table name"):
        load_documentary_ids(db, [("exhibits; DROP", "message_ids")])
    with pytest.raises(ValueError, match="unsafe column name"):
        load_documentary_ids(db, [("exhibits", "message_ids; DROP")])
    with pytest.raises(FileNotFoundError, match="SQLite database not found"):
        load_documentary_ids(tmp_path / "nope.db", [("exhibits", "message_ids")])


def test_a_message_is_an_immutable_record():
    import dataclasses
    msg = Message(seq=1, thread="t", sender="s", timestamp="ts", domain="d", body="b")
    with pytest.raises(dataclasses.FrozenInstanceError):
        msg.body = "changed"  # type: ignore[misc]
