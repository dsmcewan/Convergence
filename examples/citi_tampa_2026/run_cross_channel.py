"""Reproduce cross-channel discourse, question follow-through and linked Reddit replies."""
import json
from pathlib import Path

from convergence.attention_trajectory import analyze_attention
from convergence.cross_channel_discourse import compare_public_discourse
from convergence.question_followthrough import audit_followthrough

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


discovery = load("public_discourse_discovery_20261112.json")
questions = load("question_followthrough_20261112.json")
linked = load("reddit_linked_discussion_20261112.json")
result = {
    "cross_channel": compare_public_discourse(discovery["units"]),
    "public_question_followthrough": audit_followthrough(questions),
    "linked_forum_replies": analyze_attention(linked["units"]),
}
print(json.dumps(result, indent=2, sort_keys=True))
