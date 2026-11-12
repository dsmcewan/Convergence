"""Run public communication, causal-control and framing-comparison ledgers."""
import json
from pathlib import Path

from convergence.attention_trajectory import analyze_attention
from convergence.causal_audit import audit_causal_chain
from convergence.corporate_review import review
from convergence.framing_comparison import compare_framing

ROOT = Path(__file__).resolve().parent
statements = json.loads((ROOT / "statements.json").read_text(encoding="utf-8"))
incident = json.loads((ROOT / "incident_record.json").read_text(encoding="utf-8"))
rhetoric = review(statements)
causal_record = audit_causal_chain(incident)
framing = compare_framing(statements, rhetoric, causal_record)
attention_input = json.loads((ROOT / "attention_units.json").read_text(encoding="utf-8"))
attention = analyze_attention(attention_input["units"], attention_input["actions"])
print(json.dumps({"rhetoric": rhetoric, "causal_record": causal_record,
                  "framing_comparison": framing, "attention_trajectory": attention},
                 indent=2, sort_keys=True))
