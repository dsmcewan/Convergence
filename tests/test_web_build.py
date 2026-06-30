import json

from web.build import build


def test_build_writes_static_json(tmp_path):
    written = build(tmp_path)
    names = {p.name for p in written}

    assert {"index.json", "contractor.json", "coparenting.json", "channels.json", "dynamics.json"} <= names  # noqa: E501
    for path in written:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)

    contractor = json.loads((tmp_path / "contractor.json").read_text(encoding="utf-8"))
    assert contractor["corpus"]["message_count"] > 0
    assert contractor["findings"]

