import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_web_shell_is_blanc_only():
    html = read("web/site/index.html")
    app = read("web/site/app.js")
    server = read("web/server.py")

    assert "data-voice" not in html
    assert 'voice: "blanc"' in app
    assert 'voice: str = "blanc"' in server
    assert 'payload.get("voice", "blanc")' in server


def test_web_shell_has_cipher_console_and_reviewer_controls():
    html = read("web/site/index.html")
    app = read("web/site/app.js")

    assert 'class="demo-frame"' in html
    assert 'id="slide-stage"' in html
    assert 'id="review-window"' in html
    assert 'id="previous-finding"' in html
    assert 'id="next-finding"' in html
    assert 'id="copy-active-cipher"' in html
    assert "buildSlides" in app
    assert 'type: "message"' in app
    assert "Convergence lecture cipher" in app


def test_web_shell_is_single_frame_presentation():
    html = read("web/site/index.html")
    css = read("web/site/style.css")

    assert "fragment -> purpose -> behavior -> pattern -> campaign -> phase" in html
    assert "bottom-up lecture slideshow" in html
    assert "overflow: hidden" in css
    assert ".slide-stage" in css
    assert ".lecture-slide" in css


def test_web_shell_locks_chat_until_review_slide():
    app = read("web/site/app.js")
    css = read("web/site/style.css")

    assert 'slide.type === "review"' in app
    assert "chat-form.is-available" in css
    assert "chat-answer.is-available" in css


def test_message_slides_have_tabs_and_hover_fragment_binding():
    app = read("web/site/app.js")
    css = read("web/site/style.css")

    assert 'data-message-tab="message"' in app
    assert 'data-message-tab="signals"' in app
    assert "bindMessageSlideInteractions" in app
    assert "setActiveFragment" in app
    assert "signalPanelMarkup" in app
    assert ".message-tabs" in css
    assert ".signal-board" in css


def test_message_slide_formats_records_by_sender_and_date():
    app = read("web/site/app.js")
    css = read("web/site/style.css")

    assert "formatMessageRecord(messages)" in app
    assert "formatMessageDate(message.timestamp)" in app
    assert "`${sender}:\\n${lines.join(\"\\n\\n\")}`" in app
    assert '`${month.padStart(2, "0")}/${day.padStart(2, "0")}`' in app
    assert "white-space: pre-wrap" in css


def test_message_slide_has_linked_translation_and_method_outcome():
    app = read("web/site/app.js")
    css = read("web/site/style.css")

    assert "translationMarkup(fragments, finding)" in app
    assert "translationSegmentsForFinding(finding, fragments)" in app
    assert "translationForFragment(fragment)" in app
    assert "translation-part" in app
    assert "Not only refusing the weekend" in app
    assert "making you wrong" in app
    assert "for counting on" in app
    assert "is-sentence-path" not in app
    assert "sentence-lead" not in app
    assert ".message-card > p mark" in css
    assert "outcomeMethodForFinding" in app
    assert "Deny earlier record" in app
    assert ".message-translation" in css
    assert ".outcome-strip p" in css


def test_single_message_findings_do_not_duplicate_fragment_slide():
    app = read("web/site/app.js")

    assert "while (firstTwo.length < 2" not in app
    assert "messages.slice(0, 2)" in app


def test_behavior_slide_uses_human_pattern_language():
    app = read("web/site/app.js")
    css = read("web/site/style.css")

    assert "behaviorPatternForFinding(finding)" in app
    assert "behaviorStepsForFinding(finding)" in app
    assert "behaviorLabelForSignal(signal)" in app
    assert "behaviorSourcesForSignal(signal, finding, usedSeqs)" in app
    assert "const usedSeqs = new Set()" in app
    assert "usedSeqs.add(source.seq)" in app
    assert "Permission becomes denial" in app
    assert "Preference wears a borrowed badge" in app
    assert "Clean record, dirty channel" in app
    assert ".behavior-summary" in css
    assert ".behavior-flow" in css
    assert ".behavior-node" in css
    assert ".behavior-arrow" in css
    assert ".behavior-source" in css


def test_pattern_slide_has_behavior_hierarchy_without_record_duplication():
    app = read("web/site/app.js")
    css = read("web/site/style.css")

    assert "PATTERN_MIN_UNIQUE_RECORDS = 4" in app
    assert "qualifiesAsPattern(pattern)" in app
    assert "patternBehaviorsForPattern(pattern)" in app
    assert "patternBehaviorLabel(pattern, finding, message)" in app
    assert "Reliance gets created" in app
    assert "Permission gets recorded" in app
    assert "Authority shifts the terms" in app
    assert "Terms get narrowed" in app
    assert "Reliance gets denied" in app
    assert "Record gets reattached" in app
    assert "patternTitle(pattern)" in app
    assert "patternSummary(pattern)" in app
    assert "Not a pattern yet" in app
    assert "A pattern needs more than three unique chronological uses" in app
    assert "overlapCount(b.seqs, seqs)" in app
    assert ".pattern-ladder" in css
    assert ".pattern-behavior" in css


def test_contractor_sanitize_record_pattern_has_more_than_three_records():
    data = json.loads(read("web/site/data/contractor.json"))
    pattern = next(item for item in data["patterns"] if item["name"] == "sanitize-record")

    assert len(set(pattern["seqs"])) >= 4
    assert pattern["seqs"] == [3, 5, 10, 11]


def test_coparenting_sanitize_record_pattern_has_more_than_three_records():
    data = json.loads(read("web/site/data/coparenting.json"))
    pattern = next(item for item in data["patterns"] if item["name"] == "sanitize-record")

    assert len(set(pattern["seqs"])) >= 4
    assert pattern["seqs"] == [1, 4, 10, 11]


def test_blanc_narrator_closing_is_not_plain_language_mode_copy():
    narration = read("convergence/narration.py")

    assert "The shape of it is unmistakable" in narration
    assert "The shape of it is plain" not in narration


def test_lecture_deck_appends_dynamics_and_scorecard_slides():
    # §03 + §04: the deck must end with the corpus-independent discriminator
    # and scorecard slides, dispatched like every other slide type.
    app = read("web/site/app.js")

    assert '{ type: "dynamics" }' in app
    assert '{ type: "scorecard" }' in app
    assert 'slide.type === "dynamics"' in app
    assert 'slide.type === "scorecard"' in app
    assert "dynamicsSlideMarkup" in app
    assert "scorecardSlideMarkup" in app


def test_dynamics_slide_renders_five_corpus_discriminator_rows():
    # §03 Dynamics discriminator: the loaded state.dynamics must actually be
    # read and rendered as the 5-corpus table, flagging the coercive row.
    app = read("web/site/app.js")
    css = read("web/site/style.css")

    assert "state.dynamics.rows" in app
    assert "row.message_count" in app
    assert "row.stage_hits" in app
    assert "row.complete_envelopes" in app
    assert "row.coercive" in app
    assert ".dynamics-table" in css
    assert ".dynamics-row.is-coercive" in css


def test_scorecard_slide_renders_eval_metrics_and_hard_negative():
    # §04 Scorecard: precision / recall / F1 / specificity + the hard-negative
    # call-out must be read from state.dynamics and rendered.
    app = read("web/site/app.js")
    css = read("web/site/style.css")

    assert "state.dynamics.scorecard" in app
    assert "scorecard.precision" in app
    assert "scorecard.recall" in app
    assert "scorecard.f1" in app
    assert "scorecard.specificity" in app
    assert "state.dynamics.hard_negative" in app
    assert ".scorecard-grid" in css
    assert ".hard-negative" in css
