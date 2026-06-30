"""Regression corpora: the former blind holdout, now KNOWN (its misses drove the
recall fix). reg_coercive is a textbook coercive episode that the pre-fix engine
missed; it must now COMPLETE. The two negatives must stay non-coercive (specificity
regression guard). These are ASSERTED (unlike the blind holdout, which is reported).
"""
from pathlib import Path

from convergence.corpus import load_corpus
from convergence.evaluation import REGRESSION_LABELS, classify_coercive, evaluate_tiered

DATA = Path(__file__).parent.parent / "data"
REG = DATA / "regression"


def test_regression_labels():
    assert REGRESSION_LABELS == {
        "reg_coercive.json": True,
        "reg_cooperative.json": False,
        "reg_hostile.json": False,
        "reg_travel_coercive.json": True,
        "reg_dental_cooperative.json": False,
        "reg_camp_hostile.json": False,
    }


def test_reg_coercive_now_completes():
    # the recall-fix target: behaviorally coercive, missed pre-fix, must fire now
    assert classify_coercive(load_corpus(REG / "reg_coercive.json")) is True


def test_reg_negatives_stay_non_coercive():
    assert classify_coercive(load_corpus(REG / "reg_cooperative.json")) is False
    assert classify_coercive(load_corpus(REG / "reg_hostile.json")) is False


def test_reg_travel_coercive_now_completes():
    # the gap-#2 fix target: a travel-consent coercive episode missed pre-fix
    assert classify_coercive(load_corpus(REG / "reg_travel_coercive.json")) is True


def test_new_reg_negatives_stay_non_coercive():
    assert classify_coercive(load_corpus(REG / "reg_dental_cooperative.json")) is False
    # the bilateral-hostile corpus is the key specificity guard for refusal-vocab broadening
    assert classify_coercive(load_corpus(REG / "reg_camp_hostile.json")) is False


def test_tiered_eval_has_four_tiers():
    t = evaluate_tiered(DATA)
    assert t.core is not None and t.adversarial is not None
    assert t.regression is not None and t.holdout is not None
    # regression tier scores perfectly (2 TP + 4 TN) once T1+T2 are in
    assert (t.regression.tp, t.regression.fp, t.regression.fn, t.regression.tn) == (2, 0, 0, 4)
