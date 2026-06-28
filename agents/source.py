"""
ImpactFrame — Agent 1: Source Agent
-------------------------------------
Responsibility: Fetch all data from MCP tools and normalise
into one clean, consistent bundle for downstream agents.

Why this agent exists:
  Raw data arrives in different formats from 4 different sources.
  Staff utilisation is in one CSV. Budget is in another.
  The effectiveness report is plain text. Survey responses use
  different program names than the budget file.

  The Source Agent reads everything, standardises naming,
  fixes number formats, and produces one unified JSON bundle
  that all other agents can trust.

ADK Role: First agent in the sequential pipeline.
          No inputs required — pulls everything via MCP.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import _llm, _parse_json
from mcp_server.client import mcp


class SourceAgent:
    """
    Fetches all 4 data sources via MCP and normalises them
    into a unified bundle dict.

    MCP tools called:
      - get_health_data()           → population health + staff
      - get_survey_results()        → community survey responses
      - get_budget_constraints()    → current budget allocations
      - get_program_effectiveness() → outcomes and ROI report
    """

    NAME   = "Source Agent"
    SYSTEM = """You are a data specialist for a community health clinic.
Your job is to read raw health program data from multiple sources
and produce one clean, normalised JSON summary.
Respond with valid JSON only. No prose, no markdown fences."""

    def run(self) -> dict:
        print(f"[{self.NAME}] Fetching data via MCP...")

        # ── Fetch all 4 sources through MCP ──────────────────────
        health  = mcp.get_health_data()
        survey  = mcp.get_survey_results()
        budget  = mcp.get_budget_constraints()
        effect  = mcp.get_program_effectiveness()

        print(f"[{self.NAME}] ✓ All 4 MCP tools called — PII redacted")

        # ── Ask Gemini to normalise into unified bundle ───────────
        user = f"""
Normalise this clinic data into one clean JSON summary.

Required structure:
{{
  "program_areas": ["Diabetes Management", "Hypertension Control", "Maternal Health", "Mental Health"],
  "population_summary": {{
    "<program>": {{
      "affected_population": 0,
      "prevalence_rate": 0.0,
      "er_visits": 0,
      "mortality_rate": 0.0
    }}
  }},
  "budget_summary": {{
    "<program>": {{
      "current_budget": 0,
      "shortfall": 0,
      "grant_funding": 0
    }}
  }},
  "staff_summary": {{
    "<program>": {{
      "fte_available": 0.0,
      "avg_utilization_pct": 0.0,
      "burnout_flags": []
    }}
  }},
  "survey_summary": {{
    "<program>": {{
      "mention_count": 0,
      "top_barriers": [],
      "satisfaction_avg": 0.0
    }}
  }},
  "effectiveness_summary": {{
    "<program>": {{
      "roi_ratio": 0.0,
      "meets_targets": true,
      "key_finding": ""
    }}
  }}
}}

HEALTH DATA:   {json.dumps(health)[:4000]}
SURVEY DATA:   {json.dumps(survey)[:2000]}
BUDGET DATA:   {json.dumps(budget)[:2000]}
EFFECTIVENESS: {json.dumps(effect)[:3000]}
"""
        bundle = _parse_json(_llm(self.SYSTEM, user))

        # Keep raw data attached for downstream agents
        # but stripped before sending to LLM (saves tokens)
        bundle["_raw"] = {
            "health":       health,
            "survey":       survey,
            "budget":       budget,
            "effectiveness": effect,
        }

        print(f"[{self.NAME}] ✓ Data normalised into unified bundle")
        return bundle
