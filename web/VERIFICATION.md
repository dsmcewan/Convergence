# Convergence Web Demo — UI Verification

Produced evidence that the demo's UI is not merely asserted. Each section below
records what was checked in a **live browser** (Chrome DevTools, against the local
server at `http://127.0.0.1:8765/`) with the **actual resolved selectors,
computed styles, and counts**, the **deterministic tests** that guard it, and a
committed **screenshot** where visual.

This file is guarded by `tests/test_web_ui_verification.py` (the referenced
screenshots and test files must exist).

## What the UI actually is

A single-frame **bottom-up lecture deck** (not five static sections). Per finding,
the deck advances `message → behavior → pattern → campaign → phase → review`, then
closes with the corpus-independent `dynamics → scorecard`. The review window holds
the grounded Blanc chat, unlocked only on the review slide.

Live DOM — corpus tabs: `Contractor record`, `Coparenting record`,
`Two-channel record`. Slide deck order verified:
`message, message, behavior, pattern, campaign, phase, review, dynamics, scorecard`.

## Section-by-section evidence

### §01 Findings — message + behavior slides
- **Live DOM:** message slides render 1079 chars (fragments + signals + record);
  behavior slide renders 506 chars (`Permission becomes denial`, the L-layer
  behavior flow). Both non-empty across the deck.
- **Tests:** `test_message_slides_have_tabs_and_hover_fragment_binding`,
  `test_message_slide_formats_records_by_sender_and_date`,
  `test_message_slide_has_linked_translation_and_method_outcome`,
  `test_single_message_findings_do_not_duplicate_fragment_slide`,
  `test_behavior_slide_uses_human_pattern_language`; engine: `tests/test_engine.py` (7).

### §02 Patterns & Campaigns — pattern + campaign + phase slides
- **Live DOM:** pattern slide renders 981 chars (`Sanitize the record`, four
  chronological records); campaign slide renders the honest empty state
  (`no sustained campaign in this slice`); phase slide renders the named shape
  (`contradiction converged across domains`).
- **Tests:** `test_pattern_slide_has_behavior_hierarchy_without_record_duplication`,
  `test_contractor_sanitize_record_pattern_has_more_than_three_records`,
  `test_coparenting_sanitize_record_pattern_has_more_than_three_records`;
  composition: `tests/test_composition.py` (15).

### §03 Dynamics discriminator — dynamics slide
- **Live DOM:** `.dynamics-table tbody tr` count = **5**; `.dynamics-row.is-coercive`
  present; the coercive envelope cell computed color = **`rgb(105, 231, 255)`**
  (= the `--cyan` token `#69e7ff`) — proving "cyan = earned result" actually renders.
- **Screenshot:** `../docs/verification/s03-dynamics-discriminator.png`
- **Tests:** `test_dynamics_slide_renders_five_corpus_discriminator_rows`,
  `test_lecture_deck_appends_dynamics_and_scorecard_slides`; corpora:
  `tests/test_dynamics_corpora.py` (7).

### §04 Scorecard — scorecard slide
- **Live DOM:** `.scorecard-metric` = `PRECISION 1.00`, `RECALL 1.00`, `F1 1.00`,
  `SPECIFICITY 1.00`; `.hard-negative` = "high_conflict fired 57 hostile stage-hits
  but 0 false envelopes."
- **Screenshot:** `../docs/verification/s04-scorecard.png`
- **Tests:** `test_scorecard_slide_renders_eval_metrics_and_hard_negative`;
  eval: `tests/test_evaluation.py` (6).

### §05 Blanc chat + review — review slide
- **Live DOM:** on the review slide `#chat-form` carries `is-available`; `#question`
  textarea present; model selector options = `claude, openai, grok, gemini, agy`.
  Chat is **locked** on every non-review slide (the gate).
- **Tests:** `test_web_shell_locks_chat_until_review_slide`,
  `test_web_shell_is_blanc_only`, `test_web_shell_has_cipher_console_and_reviewer_controls`;
  narration/conversation: `tests/test_narration.py` (15), `tests/test_conversation.py` (5),
  `tests/test_web_server.py` (2).

### Shell + styling
- **Live DOM:** `--cyan` design token resolves to `#69e7ff`; reserved for elevated /
  earned results (confirmed via the coercive envelope computed color above).
- **Tests:** `test_web_shell_is_single_frame_presentation`; serialize/build:
  `tests/test_web_serialize.py` (3), `tests/test_web_build.py` (1).

## Coverage

`173` deterministic tests pass (`python -m pytest tests/ -q`). The UI contract is
guarded by the 16 tests in `tests/test_web_ui_contract.py`, mapped to sections
above; the engine/composition/eval/narration suites guard the data each section
renders. Live-browser DOM checks (this file) cover all slide types, not just §03/§04.
