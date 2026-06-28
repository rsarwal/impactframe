"""
ImpactFrame — Agent 3: Conflict Agent
---------------------------------------
Responsibility: Find contradictions between data sources
and flag them for human review before budget decisions are made.

Why this agent exists:
  This is the most important agent in the pipeline.

  Without conflict detection, a decision-maker might see
  Mental Health's ROI of 0.9x and cut the budget —
  not realising that population data shows 445 ER visits,
  56% overcapacity, and both counselors at critical burnout.

  Those two sources tell completely opposite stories.
  The Conflict Agent catches this and says:
  "Stop. A human needs to look at this before you decide."

  A conflict is detected when:
    - Community survey priority differs from ROI or outcome data
    - Staff are over capacity but budget shows no shortfall
    - High community need but low program investment
    - Satisfaction scores contradict clinical outcomes
    - One source says increase, another says cut

ADK Role: Third agent. Takes bundle + evidence from previous agents.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import _llm, _parse_json


class ConflictAgent:
    """
    Compares evidence across data sources and identifies
    contradictions that require human review.

    Returns a conflicts dict with:
      - conflicts:              list of conflict objects
      - conflict_count:         total number found
      - programs_with_conflicts: which programs are affected
    """

    NAME   = "Conflict Agent"
    SYSTEM = """You are an evidence auditor for a public health organisation.
Your job is to find places where data sources disagree with each other.
Be specific — cite the exact sources and what each one claims.
These conflicts will be shown to decision-makers who need to investigate.
Respond with valid JSON only."""

    def run(self, bundle: dict, evidence: dict) -> dict:
        print(f"[{self.NAME}] Detecting conflicts between sources...")

        summary = {k: v for k, v in bundle.items() if k != "_raw"}

        user = f"""
Find conflicts between data sources for this community health clinic.

A conflict exists when two sources tell different stories about the same program.
Examples:
  - Survey says a program is the top community priority,
    but effectiveness data shows low ROI
  - Staff utilisation shows 105% (over capacity),
    but budget data shows adequate funding
  - High ER visit rate suggests urgent need,
    but current investment is the lowest of all programs
  - Clinical outcomes are strong,
    but patient satisfaction scores are very low

For each conflict found, return:
{{
  "conflicts": [
    {{
      "conflict_id":               "C001",
      "program_area":              "program name",
      "description":               "plain English explanation of the contradiction",
      "source_a":                  "name of first source",
      "source_a_claim":            "what source A says",
      "source_b":                  "name of second source",
      "source_b_claim":            "what source B says",
      "severity":                  "HIGH / MEDIUM / LOW",
      "recommended_human_action":  "what a decision-maker should investigate"
    }}
  ],
  "conflict_count":          0,
  "programs_with_conflicts": []
}}

Severity guide:
  HIGH   = conflict could lead to a harmful budget decision if unresolved
  MEDIUM = conflict is important but less likely to cause immediate harm
  LOW    = minor inconsistency worth noting

EVIDENCE:
{json.dumps(evidence, indent=2)[:5000]}

BUNDLE SUMMARY:
{json.dumps(summary, indent=2)[:4000]}
"""
        conflicts = _parse_json(_llm(self.SYSTEM, user))
        count = conflicts.get("conflict_count", len(conflicts.get("conflicts", [])))
        print(f"[{self.NAME}] ✓ Found {count} conflicts")
        return conflicts
