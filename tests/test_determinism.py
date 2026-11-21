"""Determinism that can actually fail.

`f(x) == f(x)` inside one process cannot see two things that matter here: output that depends on
the order the messages arrive in, and output that depends on string-hash order (which changes
between processes). So these tests perturb the input order on every bundled corpus, and run the
whole pipeline in separate processes under different PYTHONHASHSEED values.
"""
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

from convergence.coercion_grammar import match_grammar
from convergence.composition import find_campaigns, find_patterns
from convergence.corpus import Message, load_corpus
from convergence.engine import run_engine
from convergence.narration import narrate

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
_FIELDS = set(Message.__dataclass_fields__)


def message_corpora() -> list[Path]:
    """Every bundled file that is a list of Message records (not exhibits or records)."""
    found = []
    for path in sorted(DATA.rglob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if (isinstance(raw, list) and raw and isinstance(raw[0], dict)
                and set(raw[0]) == _FIELDS):
            found.append(path)
    return found


def outputs(msgs: list[Message]) -> dict[str, str]:
    result = run_engine(msgs)
    return {
        "findings": repr(result.findings),
        "signals": repr(result.all_signals),
        "patterns": repr(find_patterns(result)),
        "campaigns": repr(find_campaigns(result, msgs)),
        "narration": narrate(result),
        "grammar": repr(match_grammar(msgs)),
    }


def full_analysis(name: str, order=None) -> str:
    """The exhibit, records and cross-channel layers (2, 3, 6) need inputs beyond the messages."""
    from convergence.records import load_records
    from web.serialize import CHANNELS, CORPORA
    if name in CORPORA:
        full_f, exhibit_f, records_f = CORPORA[name]
        msgs = load_corpus(DATA / full_f)
        exhibit = json.loads((DATA / exhibit_f).read_text(encoding="utf-8"))
        records = load_records(DATA / records_f)
        extra = {"included_seqs": set(exhibit["included_seqs"]), "records": records}
    else:
        primary_f, cross_f = CHANNELS[name]
        msgs = load_corpus(DATA / primary_f)
        extra = {"cross_channel": load_corpus(DATA / cross_f)}
    if order is not None:
        msgs = order(msgs)
        if "cross_channel" in extra:
            extra["cross_channel"] = order(extra["cross_channel"])
    result = run_engine(msgs, **extra)
    return repr((result.findings, result.all_signals))


def case_review_outputs() -> str:
    """The case-review modules on the example case: many events, tags and statements per set."""
    from convergence.attention_trajectory import analyze_attention
    from convergence.causal_audit import audit_causal_chain
    from convergence.corporate_review import DEFAULT_CUES, merge_cues, review
    from convergence.framing_comparison import compare_framing
    from convergence.hashtag_network import analyze_post_network
    example = ROOT / "examples" / "citi_tampa_2026"

    def load(name):
        return json.loads((example / name).read_text(encoding="utf-8"))

    statements = load("statements.json")
    cues = merge_cues(DEFAULT_CUES, load("cues.json"))
    rhetoric = review(statements, cues=cues)
    causal = audit_causal_chain(load("incident_record.json"))
    attention = load("attention_units.json")
    posts = [{"id": f"p{i}", "author": f"A{i % 5}",
              "published_at": f"2026-11-11T{9 + i % 9:02d}:00:00", "source": f"s{i}",
              "text": f"#t{i % 4} #t{(i + 1) % 4} #t{(i + 2) % 4} #brand",
              "type": "original", "evidence": "verified_public"} for i in range(12)]
    posts += [{"id": f"m{i}", "author": f"M{i}", "published_at": f"2026-11-11T{15 + i % 3}:00:00",
               "source": f"s{i}", "text": "x", "type": "reaction", "parent_post_id": f"g{i % 4}",
               "evidence": "verified_public"} for i in range(8)]
    return repr((rhetoric, causal, compare_framing(statements, rhetoric, causal),
                 analyze_attention(attention["units"], attention["actions"]),
                 analyze_post_network(posts, common_tags={"brand"})))


def digest_everything() -> str:
    """One hash over every output family for every corpus, plus the web demo payloads."""
    from web.curated import serialize_corpus
    from web.serialize import corpus_names, serialize_dynamics, serialize_index
    h = hashlib.sha256()
    for path in message_corpora():
        for key, value in outputs(load_corpus(path)).items():
            h.update(f"{path.name}:{key}:{value}".encode())
    for name in ("contractor", "coparenting", "channels"):
        h.update(f"{name}:{full_analysis(name)}".encode())
    h.update(case_review_outputs().encode())
    web = {"index": serialize_index(), "dynamics": serialize_dynamics(),
           **{n: serialize_corpus(n) for n in corpus_names()}}
    h.update(json.dumps(web, sort_keys=False).encode())
    return h.hexdigest()


def test_the_probe_sees_the_bundled_corpora():
    names = {p.name for p in message_corpora()}
    # If discovery silently found nothing, every check below would pass vacuously.
    assert len(names) >= 25
    known = {"sample_full.json", "dyn_coercive.json", "hold_hostile.json", "reg_coercive.json"}
    assert known <= names


@pytest.mark.parametrize("path", message_corpora(), ids=lambda p: p.name)
def test_output_does_not_depend_on_the_order_messages_arrive_in(path):
    msgs = load_corpus(path)
    expected = outputs(msgs)
    rng = random.Random(7)
    orders = [list(reversed(msgs))]
    for _ in range(3):
        shuffled = list(msgs)
        rng.shuffle(shuffled)
        orders.append(shuffled)
    for order in orders:
        got = outputs(order)
        assert {k: v for k, v in got.items() if v != expected[k]} == {}, path.name


@pytest.mark.parametrize("name", ["contractor", "coparenting", "channels"])
def test_the_exhibit_records_and_cross_channel_layers_do_not_depend_on_order(name):
    expected = full_analysis(name)
    assert "within_thread_omission" in expected or name == "channels"
    assert "claim_contradicted" in expected or name != "contractor"
    assert "cross_channel_divergence" in expected or name != "channels"
    rng = random.Random(11)

    def shuffled(msgs):
        out = list(msgs)
        rng.shuffle(out)
        return out

    for order in (lambda m: list(reversed(m)), shuffled, shuffled):
        assert full_analysis(name, order) == expected


def test_output_does_not_depend_on_the_hash_seed():
    """Separate processes, because string hashing is randomised per process."""
    code = (f"import runpy; "
            f"print(runpy.run_path({str(Path(__file__))!r})['digest_everything']())")
    digests = {}
    for seed in ("0", "1", "2", "4242"):
        env = {"PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT),
               "PYTHONDONTWRITEBYTECODE": "1", "PATH": ""}
        proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True,
                              text=True, env=env)
        assert proc.returncode == 0, proc.stderr[-800:]
        digests[seed] = proc.stdout.strip()
    assert len(set(digests.values())) == 1, digests
    assert all(len(d) == 64 for d in digests.values())
