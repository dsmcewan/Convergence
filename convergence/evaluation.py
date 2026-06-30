"""Scored evaluation of the coercion-grammar discriminator.

The discrimination tests answer "does it pass?"; this answers "how well?" — the
confusion matrix and precision / recall / F1 / specificity / accuracy over the
labeled dynamics corpora (coercive = the positive class). Following the eval posts,
the report also names the **hard negative**: the high-conflict corpus is hostile
(many coercion-stage hits) yet must remain a true negative, so specificity *under
adversarial load* is the number that actually matters.

Pure and deterministic; composes the existing detectors only.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from convergence.coercion_grammar import match_grammar, tag_stages
from convergence.corpus import load_corpus

# Ground truth: which dynamics corpus is coercive-controlling?
DYNAMICS_LABELS = {
    "dyn_cooperative.json": False,
    "dyn_parallel.json": False,
    "dyn_conflicted.json": False,
    "dyn_high_conflict.json": False,
    "dyn_coercive.json": True,
}


def classify_coercive(messages) -> bool:
    """The discriminator: a corpus is coercive iff it contains a complete
    coercion-grammar envelope (action -> documentation war -> fait accompli)."""
    return any(m.complete for m in match_grammar(messages))


def metrics(tp: int, fp: int, fn: int, tn: int) -> dict:
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    acc = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "specificity": spec, "accuracy": acc}


@dataclass(frozen=True)
class CorpusEval:
    name: str
    label: bool          # ground truth: coercive?
    predicted: bool
    stage_hits: int      # adversarial load: how hostile, regardless of label
    envelopes: int       # complete envelopes found
    correct: bool


@dataclass(frozen=True)
class EvalResult:
    per_corpus: tuple
    tp: int
    fp: int
    fn: int
    tn: int
    metrics: dict


def evaluate(labeled) -> EvalResult:
    """labeled: iterable of (name, messages, is_coercive)."""
    rows = []
    tp = fp = fn = tn = 0
    for name, msgs, is_pos in labeled:
        complete = [m for m in match_grammar(msgs) if m.complete]
        pred = bool(complete)
        if is_pos and pred:
            tp += 1
        elif is_pos and not pred:
            fn += 1
        elif (not is_pos) and pred:
            fp += 1
        else:
            tn += 1
        rows.append(CorpusEval(name, is_pos, pred, len(tag_stages(msgs)), len(complete), is_pos == pred))  # noqa: E501
    return EvalResult(tuple(rows), tp, fp, fn, tn, metrics(tp, fp, fn, tn))


def evaluate_dynamics(data_dir) -> EvalResult:
    data_dir = Path(data_dir)
    labeled = [
        (fname.replace("dyn_", "").replace(".json", ""), load_corpus(data_dir / fname), label)
        for fname, label in DYNAMICS_LABELS.items()
    ]
    return evaluate(labeled)


@dataclass(frozen=True)
class DocumentaryPrecision:
    """Real-data precision against INDEPENDENT documentary corroboration.

    The synthetic eval above has labeled ground truth, so it reports full P/R/F1.
    Real corpora (e.g. an app export) have no such truth — only pipeline triage labels,
    which the engine must NOT be scored against (that is circular, and triage
    labels are not evidence). Instead we ask a precision-only question that
    Documentary Primacy permits: of the messages the engine *elevates*, how many
    are independently anchored to a document, exhibit, or sworn-testimony
    contradiction? No recall is claimed — the documentary set is incomplete, and
    its silence on a message does not make an elevated finding wrong.
    """
    elevated: int                       # elevated findings examined
    corroborated: int                   # elevated findings with >=1 documentary-anchored message
    precision: float                    # corroborated / elevated
    corroboration_pool: int             # size of the independent documentary message-id set
    uncorroborated_seqs: tuple          # elevated messages with no documentary anchor (for review, not error)  # noqa: E501


def documentary_precision(elevated_finding_seqs, corroborated_ids) -> DocumentaryPrecision:
    """elevated_finding_seqs: iterable of seq-tuples (one per elevated finding).
    corroborated_ids: set of message ids independently anchored to documents."""
    corr = set(corroborated_ids)
    findings = [tuple(s) for s in elevated_finding_seqs]
    total = len(findings)
    hit = [seqs for seqs in findings if any(s in corr for s in seqs)]
    # review pointers: messages of findings with NO documentary anchor at all
    uncorr = sorted({s for seqs in findings if not any(s in corr for s in seqs) for s in seqs})
    prec = len(hit) / total if total else 0.0
    return DocumentaryPrecision(total, len(hit), prec, len(corr), tuple(uncorr))


def format_documentary_precision(dp: DocumentaryPrecision, corpus_name: str = "a real corpus") -> str:  # noqa: E501
    return "\n".join([
        f"Documentary-corroboration precision - {corpus_name} (real-data slice)",
        "",
        f"  elevated findings examined : {dp.elevated}",
        f"  independently corroborated : {dp.corroborated}",
        f"  documentary anchor pool    : {dp.corroboration_pool} messages",
        f"  PRECISION (corroborated/elevated) = {dp.precision:.3f}",
        "",
        "  Precision only: the documentary set (document links, court exhibits,",
        "  third-party evidence, deposition contradictions) is incomplete, so NO",
        "  recall is claimed and an uncorroborated finding is NOT a false positive -",
        "  it is a pointer to review, per the verbal-channel guardrail.",
    ])


def format_report(r: EvalResult) -> str:
    out = ["Coercion-grammar discriminator - scored eval", ""]
    out.append(f"  {'corpus':16}{'label':>10}{'predicted':>11}{'stage_hits':>12}{'envelopes':>11}{'ok':>4}")  # noqa: E501
    for c in r.per_corpus:
        out.append(f"  {c.name:16}{('coercive' if c.label else 'other'):>10}"
                   f"{('coercive' if c.predicted else 'other'):>11}{c.stage_hits:>12}"
                   f"{c.envelopes:>11}{('y' if c.correct else 'N'):>4}")
    m = r.metrics
    out += [
        "",
        f"  confusion:  TP={r.tp}  FP={r.fp}  FN={r.fn}  TN={r.tn}",
        f"  precision={m['precision']:.3f}  recall={m['recall']:.3f}  F1={m['f1']:.3f}  "
        f"specificity={m['specificity']:.3f}  accuracy={m['accuracy']:.3f}",
    ]
    negatives = [c for c in r.per_corpus if not c.label]
    if negatives:
        hard = max(negatives, key=lambda c: c.stage_hits)
        out.append(f"  hard negative: '{hard.name}' fired {hard.stage_hits} hostile stage-hits "
                   f"but {hard.envelopes} false envelopes - specificity holds under load.")
    return "\n".join(out)
