
from web.server import answer_chat


def test_answer_chat_uses_stubbed_model_without_network():
    prompts = []

    def complete(prompt):
        prompts.append(prompt)
        return "stubbed answer"

    answer = answer_chat("contractor", "What is elevated?", complete=complete)

    assert answer == "stubbed answer"
    assert prompts
    assert "FINDINGS:" in prompts[0]
    assert "QUESTION: What is elevated?" in prompts[0]


def test_config_from_env_defaults_to_localhost(monkeypatch):
    from web.server import _config_from_env
    monkeypatch.delenv("CONVERGENCE_HOST", raising=False)
    monkeypatch.delenv("CONVERGENCE_PORT", raising=False)
    assert _config_from_env() == ("127.0.0.1", 8765)   # safe by default


def test_config_from_env_honors_overrides(monkeypatch):
    from web.server import _config_from_env
    monkeypatch.setenv("CONVERGENCE_HOST", "0.0.0.0")
    monkeypatch.setenv("CONVERGENCE_PORT", "9000")
    assert _config_from_env() == ("0.0.0.0", 9000)


def _hdr(api_key=None):
    import email.message
    m = email.message.Message()
    if api_key is not None:
        m["X-API-Key"] = api_key
    return m


def test_chat_open_when_no_api_key_configured(monkeypatch):
    from web.server import _chat_authorized
    monkeypatch.delenv("CONVERGENCE_API_KEY", raising=False)
    assert _chat_authorized(_hdr()) is True            # localhost dev: open


def test_chat_requires_matching_key_when_configured(monkeypatch):
    from web.server import _chat_authorized
    monkeypatch.setenv("CONVERGENCE_API_KEY", "s3cret")
    assert _chat_authorized(_hdr()) is False           # missing
    assert _chat_authorized(_hdr("wrong")) is False    # mismatch
    assert _chat_authorized(_hdr("s3cret")) is True    # match


def test_answer_chat_rejects_unknown_corpus():
    try:
        answer_chat("unknown", "What happened?", complete=lambda prompt: "no")
    except KeyError as exc:
        assert "unknown corpus" in str(exc)
    else:
        raise AssertionError("unknown corpus should fail")


import pytest


def _clh(value):
    import email.message
    m = email.message.Message()
    if value is not None:
        m["content-length"] = value
    return m


def test_validate_chat_request_accepts_valid_and_defaults():
    from web.server import validate_chat_request
    assert validate_chat_request({"corpus": "contractor", "question": "why?"}) == (
        "contractor", "why?", "blanc", "claude")
    assert validate_chat_request(
        {"corpus": "contractor", "question": "q", "voice": "plain", "model": "openai"}
    ) == ("contractor", "q", "plain", "openai")


def test_validate_chat_request_rejects_bad_fields():
    from web.server import ChatError, validate_chat_request
    bad_payloads = [
        {},                                                         # missing corpus
        {"corpus": "nope", "question": "q"},                        # unknown corpus
        {"corpus": "contractor", "question": "   "},                # blank question
        {"corpus": "contractor", "question": "x" * 4001},           # over-long
        {"corpus": "contractor", "question": "q", "voice": "x"},    # bad voice
        {"corpus": "contractor", "question": "q", "model": "x"},    # bad model
        "not-a-dict",                                               # wrong type
    ]
    for payload in bad_payloads:
        with pytest.raises(ChatError) as exc:
            validate_chat_request(payload)
        assert exc.value.status == 400


def test_parse_content_length_enforces_cap():
    from web.server import MAX_BODY_BYTES, ChatError, parse_content_length
    assert parse_content_length(_clh("10")) == 10
    for header, status in [(_clh(None), 400), (_clh("abc"), 400),
                           (_clh(str(MAX_BODY_BYTES + 1)), 413)]:
        with pytest.raises(ChatError) as exc:
            parse_content_length(header)
        assert exc.value.status == status

