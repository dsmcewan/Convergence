"""Layer 4 - detect where independent domains converge on one anchor."""
from convergence.corpus import Message
from convergence.layers.domain_convergence import find_convergences


def _msg(seq, domain, body):
    return Message(seq=seq, thread="T", sender="x", timestamp="t", domain=domain, body=body)


def test_anchor_spanning_two_domains_detected():
    msgs = [_msg(1, "scope", "please log the extra hours"), _msg(2, "payment", "the invoice has extra hours")]
    res = find_convergences(msgs)
    assert any(c.domains == ("payment", "scope") and {1, 2} <= set(c.seqs) for c in res)


def test_single_domain_no_convergence():
    msgs = [_msg(1, "scope", "extra hours here"), _msg(2, "scope", "more extra hours")]
    assert find_convergences(msgs) == []


def test_stopwords_do_not_anchor():
    msgs = [_msg(1, "scope", "the cat"), _msg(2, "payment", "the dog")]
    assert find_convergences(msgs) == []


def test_min_domains_param_respected():
    msgs = [_msg(1, "scope", "extra hours"), _msg(2, "payment", "extra hours")]
    assert find_convergences(msgs, min_domains=3) == []


def test_results_sorted():
    msgs = [_msg(1, "scope", "extra hours change order"), _msg(2, "payment", "extra hours change order")]
    res = find_convergences(msgs)
    assert res == sorted(res, key=lambda c: (c.domains, c.anchor))


def test_case_variant_domains_collapse():
    # "schedule" appears in two messages whose domains differ only by case ->
    # one canonical domain -> NOT a convergence (needs >= 2 distinct domains).
    msgs = [_msg(1, "MEDICAL", "schedule the appointment"),
            _msg(2, "medical", "schedule the followup")]
    assert find_convergences(msgs) == []


def test_distinct_domains_still_converge():
    msgs = [_msg(1, "payment", "the schedule slipped"),
            _msg(2, "scope", "the schedule changed")]
    convs = find_convergences(msgs)
    assert any(c.anchor == "schedule" for c in convs)


def test_short_word_bigrams_are_dropped():
    # "she s" (from a split contraction) must not become an anchor.
    msgs = [_msg(1, "payment", "she s here"), _msg(2, "scope", "she s there")]
    assert all(c.anchor != "she s" for c in find_convergences(msgs))


def test_generic_function_words_do_not_anchor():
    # High-frequency function words ride across every domain trivially; they are
    # noise, not convergence. (Surfaced on real corpora, where "would",
    # "they", "been" outranked substantive anchors by raw domain count.)
    for w in ("would", "they", "been", "from", "which", "after", "still", "again",
              "every", "doing", "having", "could", "many"):
        msgs = [_msg(1, "payment", f"{w} matter"), _msg(2, "scope", f"{w} record")]
        assert all(c.anchor != w for c in find_convergences(msgs)), w


def test_substantive_anchors_survive_stopword_expansion():
    # Topical anchors must NOT be swept up by the function-word cull.
    for w in ("schedule", "weekend", "exchange", "invoice", "pediatrician"):
        msgs = [_msg(1, "payment", f"the {w} slipped"), _msg(2, "scope", f"the {w} changed")]
        assert any(c.anchor == w for c in find_convergences(msgs)), w
