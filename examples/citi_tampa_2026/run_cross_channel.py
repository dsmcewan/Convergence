"""Reproduce the selected cross-channel Citi public communications comparison."""
import json
from pathlib import Path

from convergence.cross_channel_discourse import compare_public_discourse

ROOT = Path(__file__).resolve().parent
sample = json.loads(
    (ROOT / "public_discourse_discovery_20261112.json").read_text(encoding="utf-8")
)
print(json.dumps(compare_public_discourse(sample["units"]), indent=2, sort_keys=True))
