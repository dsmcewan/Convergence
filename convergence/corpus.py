"""Corpus model + loader for the convergence engine.

A corpus is an ordered list of Messages. The engine is corpus-agnostic: it
never assumes anything about the domain, the parties, or the subject matter.
Swap the data file in /data and every layer still runs. That is the whole
point: the engine is *built from* message structure, not *tailored to* any
one conversation.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Message:
    seq: int          # monotonic position in the complete record
    thread: str       # conversation / subject id
    sender: str
    timestamp: str
    domain: str       # topical domain (scope, payment, timeline, ...)
    body: str


def load_corpus(path: str | Path) -> list[Message]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return sorted((Message(**m) for m in raw), key=lambda m: m.seq)


def load_sqlite_corpus(path: str | Path, table: str = "ofw_messages", limit: int | None = None) -> list[Message]:
    """Load messages from a SQLite database (bring your own export).

    The loader maps an OFW-style message table (default `ofw_messages`, with
    `ID/date_time/sent_by/subject/ofw_message_text` and optional domain columns)
    into the engine's small Message model. Message `seq` stays as the row ID so
    findings can be traced back to the database. Point `table` at your own schema.
    """
    db_path = Path(path)
    if not db_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")
    if not table.replace("_", "").isalnum():
        raise ValueError(f"unsafe table name: {table}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cols = {row["name"] for row in conn.execute(f'pragma table_info("{table}")')}
        required = {"ID", "date_time", "sent_by", "subject", "ofw_message_text"}
        missing = required - cols
        if missing:
            raise ValueError(f"table {table!r} is missing columns: {sorted(missing)}")

        domain_parts = [f'nullif({name}, "")' for name in ("primary_domain", "behavior_cluster") if name in cols]
        domain_expr = "coalesce(" + ", ".join(domain_parts) + ")" if domain_parts else None
        select_domain = f", {domain_expr} as domain_value" if domain_expr else ", NULL as domain_value"
        sql = (
            f'SELECT ID, date_time, sent_by, subject, ofw_message_text{select_domain} '
            f'FROM "{table}" '
            "WHERE ofw_message_text IS NOT NULL AND trim(ofw_message_text) != '' "
            "ORDER BY ID"
        )
        if limit is not None:
            sql += " LIMIT ?"
            rows = conn.execute(sql, (limit,)).fetchall()
        else:
            rows = conn.execute(sql).fetchall()
    finally:
        conn.close()

    messages = [
        Message(
            seq=int(row["ID"]),
            thread=str(row["subject"] or "thread"),
            sender=str(row["sent_by"] or "unknown"),
            timestamp=str(row["date_time"] or ""),
            domain=str(row["domain_value"] or "GENERAL"),
            body=str(row["ofw_message_text"] or ""),
        )
        for row in rows
    ]
    return sorted(messages, key=lambda m: m.seq)


def _parse_ids(value) -> set[int]:
    """Pull integer message ids from an int or a comma/space-separated string."""
    if value is None:
        return set()
    out: set[int] = set()
    for tok in str(value).replace(";", ",").replace(" ", ",").split(","):
        tok = tok.strip()
        if tok.isdigit():
            out.add(int(tok))
    return out


def load_documentary_ids(path: str | Path, sources) -> set[int]:
    """Set of message ids independently anchored to documentary evidence.

    `sources` is an iterable of (table, message-id column) pairs — your own
    evidence surfaces (links to documents, exhibits, etc.). Used for the
    documentary-precision slice (see `evaluation.documentary_precision`): score
    the engine's elevated findings against *independent* anchors, never against
    triage labels in the message table itself. Defensive: each source is skipped
    unless both its table and column exist, so it tolerates schema variation.
    """
    db_path = Path(path)
    if not db_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    ids: set[int] = set()
    try:
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for table, col in sources:
            if table not in tables:
                continue
            cols = {r["name"] for r in conn.execute(f'pragma table_info("{table}")')}
            if col not in cols:
                continue
            for row in conn.execute(f'SELECT "{col}" AS v FROM "{table}"'):
                ids |= _parse_ids(row["v"])
    finally:
        conn.close()
    return ids
