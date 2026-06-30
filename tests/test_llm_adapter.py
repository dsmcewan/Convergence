"""The optional LLM adapters fail clearly without a key (no SDK/network needed)."""
import pytest

from convergence.adapters.anthropic_llm import make_anthropic_complete
from convergence.adapters.gemini_llm import make_gemini_complete
from convergence.adapters.grok_llm import make_grok_complete


def test_anthropic_no_key_raises_clear_error():
    with pytest.raises(RuntimeError):
        make_anthropic_complete(api_key=None, _env={})


def test_gemini_no_key_raises_clear_error():
    # _dotenv_paths=[] disables the .env fallback so the test is independent of disk
    with pytest.raises(RuntimeError):
        make_gemini_complete(api_key=None, _env={}, _dotenv_paths=[])


def test_gemini_reads_key_from_dotenv(tmp_path):
    from convergence.adapters import gemini_llm
    envfile = tmp_path / ".env"
    envfile.write_text('GEMINI_API_KEY="from-dotenv-xyz"\n', encoding="utf-8")
    # no SDK in the test env -> it gets past the key check and fails on import instead,
    # which proves the key WAS found (a missing key would raise the "not set" error first)
    try:
        gemini_llm.make_gemini_complete(api_key=None, _env={}, _dotenv_paths=[envfile])
    except RuntimeError as e:
        assert "not set" not in str(e)   # key was found; failure (if any) is SDK/import, not key


def test_gemini_cli_missing_raises_clear_error():
    from convergence.adapters.gemini_cli_llm import make_gemini_cli_complete
    with pytest.raises(RuntimeError):
        make_gemini_cli_complete(_which=lambda name: None)  # CLI not found


def test_gemini_cli_returns_callable_when_present():
    from convergence.adapters.gemini_cli_llm import make_gemini_cli_complete
    complete = make_gemini_cli_complete(_which=lambda name: "/usr/bin/gemini")
    assert callable(complete)


def test_antigravity_cli_missing_raises_clear_error():
    from convergence.adapters.antigravity_cli_llm import make_antigravity_cli_complete
    with pytest.raises(RuntimeError):
        make_antigravity_cli_complete(_which=lambda name: None)  # CLI not found


def test_antigravity_cli_returns_callable_when_present():
    from convergence.adapters.antigravity_cli_llm import make_antigravity_cli_complete
    complete = make_antigravity_cli_complete(_which=lambda name: "C:\\agy\\agy.exe")
    assert callable(complete)


def test_antigravity_strip_removes_handshake_and_ansi():
    # the answer must survive; the terminal handshake/control bytes must not
    from convergence.adapters.antigravity_cli_llm import _strip
    raw = "\x1b[1t\x1b[c\x1b[?1004h\x1b[?9001halpha bravo charlie\r\n"
    assert _strip(raw) == "alpha bravo charlie"


def test_openai_no_key_raises_clear_error():
    from convergence.adapters.openai_llm import make_openai_complete
    with pytest.raises(RuntimeError):
        make_openai_complete(api_key=None, _env={}, _dotenv_paths=[])


def test_openai_reads_key_from_dotenv(tmp_path):
    from convergence.adapters import openai_llm
    envfile = tmp_path / ".env"
    envfile.write_text('OPENAI_API_KEY="from-dotenv-xyz"\n', encoding="utf-8")
    # no SDK in the test env -> it gets past the key check and fails on import instead,
    # which proves the key WAS found (a missing key would raise the "not set" error first)
    try:
        openai_llm.make_openai_complete(api_key=None, _env={}, _dotenv_paths=[envfile])
    except RuntimeError as e:
        assert "not set" not in str(e)   # key was found; failure (if any) is SDK/import, not key


def test_grok_no_key_raises_clear_error():
    with pytest.raises(RuntimeError):
        make_grok_complete(api_key=None, _env={}, _dotenv_paths=[])


def test_grok_reads_key_from_dotenv(tmp_path):
    from convergence.adapters import grok_llm
    envfile = tmp_path / ".env"
    envfile.write_text('GROK_API_KEY="from-dotenv-xyz"\n', encoding="utf-8")
    try:
        grok_llm.make_grok_complete(api_key=None, _env={}, _dotenv_paths=[envfile])
    except RuntimeError as e:
        assert "not set" not in str(e)


def test_openai_api_error_degrades_to_clear_error():
    # An API-side failure (invalid model, rate limit, network) must surface as the
    # same clear RuntimeError as a missing key, so callers fall back to the
    # deterministic narrator instead of leaking a raw SDK traceback.
    from convergence.adapters.openai_llm import make_openai_complete

    class _BoomClient:
        class chat:
            class completions:
                @staticmethod
                def create(**_kwargs):
                    raise ValueError("model_not_found: gpt-nope")

    complete = make_openai_complete(api_key="test-key", _client=_BoomClient())
    with pytest.raises(RuntimeError):
        complete("hello")


def test_anthropic_api_error_degrades_to_clear_error():
    from convergence.adapters.anthropic_llm import make_anthropic_complete

    class _BoomClient:
        class messages:
            @staticmethod
            def create(**_kwargs):
                raise ValueError("model_not_found: claude-nope")

    complete = make_anthropic_complete(api_key="test-key", _client=_BoomClient())
    with pytest.raises(RuntimeError):
        complete("hello")


def test_anthropic_thinking_blocks_printed_and_text_returned(capsys):
    from convergence.adapters.anthropic_llm import make_anthropic_complete

    class _MockBlock:
        def __init__(self, type, text=None, thinking=None):
            self.type = type
            self.text = text
            self.thinking = thinking

    class _MockMessage:
        def __init__(self, content):
            self.content = content

    last_kwargs = {}

    class _MockClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                last_kwargs.update(kwargs)
                return _MockMessage([
                    _MockBlock("thinking", thinking="I should think about this..."),
                    _MockBlock("text", text="The final response.")
                ])

    # 1. Test with default model (claude-sonnet-4-6) -> adaptive thinking enabled
    complete = make_anthropic_complete(
        model="claude-sonnet-4-6", api_key="test-key", _client=_MockClient()
    )
    res = complete("hello")
    assert res == "The final response."
    assert last_kwargs["max_tokens"] == 8192
    assert last_kwargs["thinking"] == {"type": "adaptive"}
    assert last_kwargs["output_config"] == {"effort": "high"}

    captured = capsys.readouterr()
    assert "[Claude Thinking]" in captured.out
    assert "I should think about this..." in captured.out

    # 2. Test with legacy model -> thinking disabled
    last_kwargs.clear()
    complete_legacy = make_anthropic_complete(
        model="claude-3-5-sonnet-20241022", api_key="test-key", _client=_MockClient()
    )
    res_legacy = complete_legacy("hello")
    assert res_legacy == "The final response."
    assert last_kwargs["max_tokens"] == 700
    assert "thinking" not in last_kwargs
    assert "output_config" not in last_kwargs

    # 3. Test with Claude 3.7 model -> fixed budget thinking enabled
    last_kwargs.clear()
    complete_37 = make_anthropic_complete(
        model="claude-3-7-sonnet-20250219", api_key="test-key", _client=_MockClient()
    )
    res_37 = complete_37("hello")
    assert res_37 == "The final response."
    assert last_kwargs["max_tokens"] == 4096
    assert last_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 1024}
    assert "output_config" not in last_kwargs

