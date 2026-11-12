"""Run public communications and incident-control ledgers; core verdicts unchanged."""
import json
from pathlib import Path
from convergence.causal_audit import audit_causal_chain
from convergence.corporate_review import review

ROOT = Path(__file__).resolve().parent
statements = json.loads((ROOT / "statements.json").read_text(encoding="utf-8"))
incident = json.loads((ROOT / "incident_record.json").read_text(encoding="utf-8"))
print(json.dumps({"rhetoric": review(statements), "causal_record": audit_causal_chain(incident)},
                 indent=2, sort_keys=True))
