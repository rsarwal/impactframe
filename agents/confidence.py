"""
ImpactFrame — Agent 4: Confidence Agent
-----------------------------------------
Responsibility: Score the reliability of each data source
so the Allocation Agent knows how much to trust each input.

Why this agent exists:
  Not all data is equally trustworthy.

  A clinic budget spreadsheet with an audit trail is
  very different from a 20-person community survey.
  Both matter — but they should carry different weight
  in a budget decision.

  The Confidence Agent grades each source:
    A = Very reliable — auditable, objective, consistent
    B = Reliable — good methodology, some limitations
    C = Moderate — directionally useful, verify key claims
    D = Low reliability — significant gaps or contradictions

  It also scores each program's overall evidence base:
    STRONG   = multiple sources agree, good data quality
    MODERATE = mixed quality, some gaps
    WEAK     = limited data, heavy reliance on one source

  This tells the Allocation Agent: "Trust the budget numbers
  fully. Be cautious with the survey. The Mental Health
  evidence is weak because sources conflict."

ADK Role: Fourth agent. Takes bundle, evidence, and conflicts.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import _llm, _parse_json


class ConfidenceAgent:
    """
    Scores reliability of each data source and each
    program's overall evidence base.

    Returns a scores dict with:
      - source_confidence:       grade + rationale per data source
      - program_confidence:      strength + uncertainty per program
      - overall_data_quality:    GOOD / FAIR / POOR
      - recommendation_reliability: plain English assessment
    """

    NAME   = "Confidence Agent"
    SYSTEM = """You are a data quality assessor for a public health organisation.
Score the reliability of data sources conservatively.
Flag uncertainty clearly — it is better to understate confidence
than to give false certainty to budget decision-makers.
Respond with valid JSON only."""

    def run(self, bundle: dict, evidence: dict, conflicts: dict) -> dict:
        print(f"[{self.NAME}] Scoring data source reliability...")

        user = f"""
Score the reliability of each data source and each program's evidence base.

Return JSON:
{{
  "source_confidence": {{
    "<source_name>": {{
      "score":       0.0,
      "grade":       "A",
      "rationale":   "why this grade was assigned",
      "limitations": ["specific limitation 1", "limitation 2"]
    }}
  }},
  "program_confidence": {{
    "<program_area>": {{
      "overall_score":    0.0,
      "grade":            "A",
      "evidence_strength": "STRONG / MODERATE / WEAK",
      "key_uncertainty":  "the main thing we don't know",
      "conflict_impact":  "HIGH / MEDIUM / LOW / NONE"
    }}
  }},
  "overall_data_quality":      "GOOD / FAIR / POOR",
  "recommendation_reliability": "plain English statement about how much to trust the recommendations"
}}

Grading guide:
  A = Auditable, objective, internally consistent
  B = Good methodology with minor limitations
  C = Directionally useful but verify key claims
  D = Significant gaps, contradictions, or very small sample

Sources to grade (use these exact names):
  get_health_data, get_budget_constraints,
  get_survey_results, get_program_effectiveness

Consider how conflicts affect confidence:
  A source that appears in many HIGH severity conflicts
  should receive a lower grade.

CONFLICTS FOUND:
{json.dumps(conflicts, indent=2)[:3000]}

PROGRAM AREAS:
{list(evidence.keys())}

EVIDENCE BASE SUMMARY:
{json.dumps({k: {t: len(v) for t, v in ev.items()} for k, ev in evidence.items()}, indent=2)}
"""
        scores = _parse_json(_llm(self.SYSTEM, user))
        quality = scores.get("overall_data_quality", "UNKNOWN")
        print(f"[{self.NAME}] ✓ Overall data quality: {quality}")
        return scores
