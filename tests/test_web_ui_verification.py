import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_verification_doc_screenshots_exist():
    doc = read("web/VERIFICATION.md")
    for shot in ["docs/verification/s03-dynamics-discriminator.png", "docs/verification/s04-scorecard.png"]:
        assert (ROOT / shot).is_file(), f"missing committed screenshot {shot}"
        assert shot.split("/")[-1] in doc


def test_verification_doc_cites_real_tests():
    doc = read("web/VERIFICATION.md")
    ui = read("tests/test_web_ui_contract.py")
    cited = set(re.findall(r"test_[a-z0-9_]+", doc))
    for name in (
        "test_scorecard_slide_renders_eval_metrics_and_hard_negative",
        "test_dynamics_slide_renders_five_corpus_discriminator_rows",
        "test_web_shell_locks_chat_until_review_slide",
        "test_behavior_slide_uses_human_pattern_language",
    ):
        assert name in cited, f"{name} not cited in VERIFICATION.md"
        assert f"def {name}" in ui, f"{name} no longer exists in the suite"


def test_verification_doc_slide_types_match_app():
    doc = read("web/VERIFICATION.md")
    app = read("web/site/app.js")
    for slide_type in ["message", "behavior", "pattern", "campaign", "phase", "review", "dynamics", "scorecard"]:
        assert f'"{slide_type}"' in app, f"{slide_type} is not dispatched in app.js"
        assert slide_type in doc, f"{slide_type} not documented in VERIFICATION.md"
