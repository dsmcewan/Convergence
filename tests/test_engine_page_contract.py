from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(p: str) -> str:
    return (ROOT / p).read_text(encoding="utf-8")


def test_engine_page_exists_and_is_plain():
    html = read("web/site/engine.html")
    js = read("web/site/engine.js")
    # plain, generic view: a corpus picker, a findings container, loads engine.js
    assert 'id="corpus-select"' in html
    assert 'id="findings"' in html
    assert "engine.js" in html
    # it is NOT the Blanc lecture: no slideshow, no Blanc voice, no chat
    assert "slide-stage" not in html
    assert "Blanc" not in html and "blanc" not in js
    assert "chat-form" not in html
    # engine.js renders the generic core fields
    assert "data/index.json" in js
    assert "findings" in js and "confidence" in js and "layers" in js


def test_lecture_links_to_engine_page():
    assert "engine.html" in read("web/site/index.html")


def test_engine_js_ignores_curated_section():
    js = read("web/site/engine.js")
    assert "curated" not in js  # the plain view must not read the curated section


def test_engine_page_links_own_stylesheet():
    html = read("web/site/engine.html")
    # engine console must link its own stylesheet, not the lecture's style.css
    assert "engine.css" in html


def test_engine_js_has_badge_and_convergence_trace():
    js = read("web/site/engine.js")
    # confidence badge is rendered for every finding
    assert "badge" in js
    # convergence trace is generated from signal data for elevated findings
    assert "trace" in js
