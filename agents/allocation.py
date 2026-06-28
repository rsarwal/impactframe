"""
ImpactFrame — Agent 5: Allocation Agent
-----------------------------------------
Responsibility: Synthesise all upstream outputs into final
budget allocation recommendations with full reasoning.

Why this agent exists:
  This is the decision-support output — what a clinic director
  or board actually uses to make funding decisions.

  The Allocation Agent receives:
    - The data bundle (what the numbers say)
    - The evidence (specific citable facts)
    - The conflicts (where sources disagree)
    - The confidence scores (how much to trust each source)

  It weighs all of this and produces:
    - Recommended budget per program (dollar amount + %)
    - Direction: increase, decrease, or maintain
    - Primary rationale with evidence citations
    - Confidence score for each recommendation
    - Human review flag where conflicts remain unresolved
    - Implementation priorities (what to do first)
    - Items for board decision (what needs leadership sign-off)

  Critically: it does NOT make decisions for humans.
  It makes the evidence visible so humans can decide well.

ADK Role: Fifth and final agent. Takes all previous outputs.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import _llm, _parse_json


class AllocationAgent:
    """
    Produces final budget allocation recommendations.

    Returns an allocation dict with:
      - total_budget
      - allocation_recommendations per program
      - allocation_summary (executive summary)
      - key_tradeoffs
      - implementation_priorities
      - flags_for_board
    """

    NAME   = "Allocation Agent"
    SYSTEM = """You are a senior public health resource allocation advisor.
You have reviewed all available evidence about this clinic's programs.
Produce clear, evidence-based budget recommendations.
Be practical. Flag where human judgment is still required.
Do not use jargon. Write as if explaining to a clinic director.
Respond with valid JSON only."""

    def run(
        self,
        bundle: dict,
        evidence: dict,
        conflicts: dict,
        scores: dict,
        total_budget: int = 1422000,
    ) -> dict:
        print(f"[{self.NAME}] Generating allocation recommendations...")

        summary = {k: v for k, v in bundle.items() if k != "_raw"}

        user = f"""
Produce budget allocation recommendations for a community health clinic.
Total annual budget to allocate: ${total_budget:,}

Programs to allocate across (ALL 6 must appear in output, none can be omitted):
  1. Diabetes Management    (current budget: from budget data)
  2. Hypertension Control   (current budget: from budget data)
  3. Maternal Health        (current budget: from budget data)
  4. Mental Health          (current budget: from budget data)
  5. Community Outreach     (current budget: from budget data)
  6. Administration         (current budget: from budget data)

IMPORTANT: Every program must have a non-zero recommended_amount and current_amount
based on the budget data provided. Do not set any value to 0 unless the budget
data explicitly shows $0 for that program.

For each program, produce a recommendation with this structure:
{{
  "total_budget": {total_budget},
  "allocation_recommendations": {{
    "<program name>": {{
      "recommended_amount":     0,
      "recommended_percentage": 0.0,
      "current_amount":         0,
      "change_direction":       "INCREASE / DECREASE / MAINTAIN",
      "change_amount":          0,
      "primary_rationale":      "2-3 sentence plain English reason",
      "evidence_used":          ["source: specific fact used"],
      "confidence":             0.0,
      "human_review_required":  false,
      "human_review_reason":    null
    }}
  }},
  "allocation_summary":    "3-4 sentence executive summary of all decisions",
  "key_tradeoffs":         ["tradeoff 1", "tradeoff 2"],
  "implementation_priorities": [
    {{
      "priority": 1,
      "action":   "specific action to take",
      "program":  "program name",
      "timeline": "e.g. Within 30 days"
    }}
  ],
  "flags_for_board": [
    "item requiring board or leadership decision"
  ]
}}

Writing guidance:
  - primary_rationale should sound like a senior analyst wrote it,
    not like AI generated it
  - Avoid words like: leverage, utilise, robust, comprehensive
  - Be specific about numbers and evidence
  - human_review_required = true whenever a HIGH conflict
    affects this program and is unresolved

BUDGET DATA:
{json.dumps(summary.get("budget_summary", {}), indent=2)}

EFFECTIVENESS DATA:
{json.dumps(summary.get("effectiveness_summary", {}), indent=2)}

CONFLICTS (unresolved):
{json.dumps(conflicts.get("conflicts", []), indent=2)[:2000]}

CONFIDENCE SCORES:
{json.dumps(scores.get("program_confidence", {}), indent=2)}
"""
        allocation = _parse_json(_llm(self.SYSTEM, user))
        n_recs = len(allocation.get("allocation_recommendations", {}))
        print(f"[{self.NAME}] ✓ Recommendations generated for {n_recs} programs")
        return allocation
