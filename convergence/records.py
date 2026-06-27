"""External-records model + loader (Layer 3 input).

Records are deliberately NOT Messages. They represent verifiable facts from
third-party sources (a platform log, an attendance sheet, an invoice, an
agency finding) against which message *claims* are tested. A record carries a
`source_seq` pointing back at the message that establishes it, so a
contradiction can name where the truth actually lives.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Record:
    id: str
    subject: str
    predicate: str
    value: bool | str
    source_seq: int | None
    note: str


def load_records(path: str | Path) -> list[Record]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Record(**r) for r in raw]
