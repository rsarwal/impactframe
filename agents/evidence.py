"""
ImpactFrame — Agent 2: Evidence Agent
---------------------------------------
Responsibility: Extract specific, citable facts from the
data bundle — one set of evidence per program area.

Why this agent exists:
  The bundle from the Source Agent is a summary.
  The Evidence Agent digs deeper — pulling the specific
  numbers and findings that justify budget decisions.

  Each evidence item is tagged with:
    - The fact itself
    - Its value (the number or finding)
    - Which data source it came from
    - What type of evidence it is

  This creates an audit trail: every recommendation
  downstream can be traced to specific evidence.

ADK Role: Second agent. Takes bundle from Source Agent.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import _llm, _parse_json


class EvidenceAgent:
    """
    Extracts structured evidence items from the data bundle.

    Returns a dict keyed by program area, each containing:
      - need_evidence:        who needs this service and how urgently
      - performance_evidence: is the program actually working
      - resource_evidence:    what capacity exists to deliver it
    """

    NAME   = "Evidence Agent"
    SYSTEM = """You are a public health analyst reviewing clinic program data.
Extract specific, citable evidence items from the data.
Each item must name its source so recommendations can be traced.
Respond with valid JSON only."""

    def run(self, bundle: dict) -> dict:
        print(f"[{self.NAME}] Extracting evidence per program...")

        # Strip raw data — not needed here, saves tokens
        summary = {k: v for k, v in bundle.items() if k != "_raw"}

        user = f"""
Extract evidence for each program area from this clinic data.

Return JSON with this structure:
{{
  "<program_area>": {{
    "need_evidence": [
      {{
        "fact":   "description of the finding",
        "value":  "the specific number or stat",
        "source": "which dataset this came from",
        "type":   "need"
      }}
    ],
    "performance_evidence": [
      {{
        "fact":   "description",
        "value":  "number or finding",
        "source": "dataset name",
        "type":   "outcome"
      }}
    ],
    "resource_evidence": [
      {{
        "fact":   "description",
        "value":  "number or finding",
        "source": "dataset name",
        "type":   "capacity"
      }}
    ]
  }}
}}

Evidence types to use: need, outcome, financial, community, capacity

DATA BUNDLE:
{json.dumps(summary, indent=2)[:8000]}
"""
        evidence = _parse_json(_llm(self.SYSTEM, user))
        print(f"[{self.NAME}] ✓ Evidence extracted for {len(evidence)} programs")
        return evidence
