"""Thread-locality is an architectural property of run_engine's elevation. The
within-thread-only layers - L1 (pattern), L2 (omission), L5 (register) - never
assemble a finding across threads by themselves, because elevation groups signals by
SEQ OVERLAP and each seq belongs to exactly one thread. A finding MAY still span
threads, but only via a *bridging* layer that by its nature references another
context: L3 (a claim contradicted by a record/message elsewhere), L4 (a token
converging across domains/threads), or L6 (cross-channel). The flagship contractor
finding legitimately spans threads T1/T2 via L3 + L4. This test locks that property so
a future change cannot let a within-thread-only layer silently span threads.

Measured 2026-06-30 against the real load_analysis pipeline (records + included_seqs
enabled, so L2/L3 fire as in production): 0 violations.
"""
from web.serialize import corpus_names, load_analysis

_WITHIN_ONLY = {"L1", "L2", "L5"}   # pattern, omission, register
_BRIDGING = {"L3", "L4", "L6"}      # contradiction, domain-convergence, cross-channel


def _threads(seqs, by_seq):
    return {by_seq[s] for s in seqs if s in by_seq}


def test_within_thread_only_layers_never_span_threads():
    for name in corpus_names():
        messages, result, _ = load_analysis(name)
        by_seq = {m.seq: m.thread for m in messages}
        for f in result.findings:
            for s in f.signals:
                if s.layer in _WITHIN_ONLY:
                    th = _threads(s.seqs, by_seq)
                    assert len(th) <= 1, (
                        f"{name}: {s.layer} signal spans threads {sorted(th)} "
                        f"(seqs {list(s.seqs)})"
                    )


def test_cross_thread_findings_require_a_bridging_layer():
    saw_cross_thread = False
    for name in corpus_names():
        messages, result, _ = load_analysis(name)
        by_seq = {m.seq: m.thread for m in messages}
        for f in result.findings:
            if len(_threads(f.seqs, by_seq)) > 1:
                saw_cross_thread = True
                assert set(f.layers) & _BRIDGING, (
                    f"{name}: finding spans threads with no bridging layer "
                    f"(layers {list(f.layers)}, seqs {list(f.seqs)})"
                )
    assert saw_cross_thread, "expected at least one cross-thread finding to exist"
