"""Layer 6 demonstrated end-to-end on a third corpus pair (two channels).

The agnosticism proof, extended: the *identical* run_engine runs on a two-channel
corpus with no code changes. A favorable claim in the formal channel is impeached
by the same sender's admission in the casual channel (L6) and corroborated by
domains converging on the same anchor (L4) -> elevated; a bare borrow-authority
claim with nothing behind it stays low. Synthetic data only.
"""
from pathlib import Path

from convergence.corpus import load_corpus
from convergence.engine import run_engine

DATA = Path(__file__).parent.parent / "data"


def _channels():
    formal = load_corpus(DATA / "channels_formal.json")
    casual = load_corpus(DATA / "channels_casual.json")
    return formal, casual


def test_cross_channel_divergence_elevated_with_corroboration():
    formal, casual = _channels()
    res = run_engine(formal, cross_channel=casual)
    elevated = [f for f in res.findings if f.confidence == "elevated"]
    assert any("L6" in f.layers for f in elevated)
    f = next(f for f in elevated if "L6" in f.layers)
    assert "L4" in f.layers  # the cross-channel claim is corroborated, not lone


def test_lone_borrow_authority_stays_low_on_channels():
    formal, casual = _channels()
    res = run_engine(formal, cross_channel=casual)
    low = [f for f in res.findings if f.confidence == "low"]
    assert any(f.layers == ("L1",) for f in low)  # self-disqualification holds


def test_same_engine_yields_elevated_on_channels_too():
    formal, casual = _channels()
    res = run_engine(formal, cross_channel=casual)
    assert any(f.confidence == "elevated" for f in res.findings)
