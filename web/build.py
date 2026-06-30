"""Build the static web demo data."""
from __future__ import annotations

import json
from pathlib import Path

from web.curated import serialize_corpus
from web.serialize import corpus_names, serialize_dynamics, serialize_index

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "site" / "data"


def build(out_dir: Path = OUT) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    payloads = {"index": serialize_index(), "dynamics": serialize_dynamics()}
    for name in corpus_names():
        payloads[name] = serialize_corpus(name)

    for name, payload in payloads.items():
        path = out_dir / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)

    return written


def main() -> None:
    for path in build():
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()

