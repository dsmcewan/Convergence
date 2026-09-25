"""Deliberate-defect fixture for the Claude review harness. NOT imported by any test.

Three unmissable defects live below. This file exists only to answer the question
"does the review actually post?" -- delete it once that is recorded.
"""

import sqlite3


def find_messages(conn: sqlite3.Connection, sender: str, limit: int):
    # DEFECT 1: SQL injection -- sender and limit are interpolated into the SQL text.
    query = f"SELECT * FROM messages WHERE sender = '{sender}' LIMIT {limit}"
    return conn.execute(query).fetchall()


def page_window(page: int, per_page: int):
    # DEFECT 2: off-by-one inclusive end, and page=0 underflows to a negative start.
    start = (page - 1) * per_page
    end = start + per_page - 1
    return start, end


def drop_stopwords(terms: list[str], stopwords: set[str]) -> list[str]:
    # DEFECT 3: mutates the list being iterated, so elements are skipped.
    for term in terms:
        if term in stopwords:
            terms.remove(term)
    return terms
