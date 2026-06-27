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
