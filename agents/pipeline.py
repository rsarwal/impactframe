"""
ImpactFrame Agent Pipeline
"""

import os
import json
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from google import genai

sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.client import mcp

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = "models/gemini-flash-lite-latest"


def _llm(system: str, user: str) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=user,
        config=genai.types.GenerateContentConfig(
            system_instruction=system,
        ),
    )
    return response.text


def _parse_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON:\n{text[:400]}")


# ═══════════════════════════════════════════
# AGENT 1 — Ingestion Agent
# ═══════════════════════════════════════════

class IngestionAgent:

    SYSTEM = """You are a data ingestion specialist for a community health clinic.
Normalise raw health data into clean JSON. Respond with valid JSON only, no prose."""

    def run(self) -> dict:
        print("[Agent 1] Ingesting data via MCP...")

        health = mcp.get_health_data()
        survey = mcp.get_survey_results()
        budget = mcp.get_budget_constraints()
        effect = mcp.get_program_effectiveness()

        print("  ✓ All 4 MCP tools called successfully")

        user = f"""
Normalise this clinic data into a JSON summary with this structure:
{{
  "program_areas": ["Diabetes Management", "Hypertension Control", "Maternal Health", "Mental Health"],
  "population_summary": {{
    "<program>": {{"affected_population": 0, "prevalence_rate": 0.0, "er_visits": 0, "mortality_rate": 0.0}}
  }},
  "budget_summary": {{
    "<program>": {{"current_budget": 0, "shortfall": 0, "grant_funding": 0}}
  }},
  "staff_summary": {{
    "<program>": {{"fte_available": 0.0, "avg_utilization_pct": 0.0, "burnout_flags": []}}
  }},
  "survey_summary": {{
    "<program>": {{"mention_count": 0, "top_barriers": [], "satisfaction_avg": 0.0}}
  }},
  "effectiveness_summary": {{
    "<program>": {{"roi_ratio": 0.0, "meets_targets": true, "key_finding": ""}}
  }}
}}

HEALTH DATA: {json.dumps(health)[:4000]}
SURVEY DATA: {json.dumps(survey)[:2000]}
BUDGET DATA: {json.dumps(budget)[:2000]}
EFFECTIVENESS: {json.dumps(effect)[:3000]}
"""
        bundle = _parse_json(_llm(self.SYSTEM, user))
        bundle["_raw"] = {
            "health": health,
            "survey": survey,
            "budget": budget,
            "effectiveness": effect,
        }
        print("[Agent 1] ✓ Ingestion complete")
        return bundle


# ═══════════════════════════════════════════
# AGENT 2 — Evidence Extraction Agent
# ═══════════════════════════════════════════

class EvidenceExtractionAgent:

    SYSTEM = """You are a public health analyst extracting evidence from clinic data.
Each evidence item must cite its source. Respond with valid JSON only."""

    def run(self, bundle: dict) -> dict:
        print("[Agent 2] Extracting evidence...")

        summary = {k: v for k, v in bundle.items() if k != "_raw"}

        user = f"""
Extract evidence for each program area from this data bundle.

Return JSON:
{{
  "<program_area>": {{
    "need_evidence": [
      {{"fact": "string", "value": "string", "source": "string", "type": "need"}}
    ],
    "performance_evidence": [],
    "resource_evidence": []
  }}
}}

DATA: {json.dumps(summary, indent=2)[:8000]}
"""
        evidence = _parse_json(_llm(self.SYSTEM, user))
        print("[Agent 2] ✓ Evidence extracted")
        return evidence


# ═══════════════════════════════════════════
# AGENT 3 — Conflict Detection Agent
# ═══════════════════════════════════════════

class ConflictDetectionAgent:

    SYSTEM = """You are an evidence auditor for a public health organisation.
Find conflicts where sources disagree. Cite exact sources. Respond with valid JSON only."""

    def run(self, bundle: dict, evidence: dict) -> dict:
        print("[Agent 3] Detecting conflicts...")

        summary = {k: v for k, v in bundle.items() if k != "_raw"}

        user = f"""
Find conflicts between data sources for this clinic.

A conflict is when:
- Community survey priority differs from ROI data
- Staff over capacity but budget shows no shortfall
- High need but low investment
- Outcome metrics contradict satisfaction scores

Return JSON:
{{
  "conflicts": [
    {{
      "conflict_id": "C001",
      "program_area": "string",
      "description": "string",
      "source_a": "string",
      "source_a_claim": "string",
      "source_b": "string",
      "source_b_claim": "string",
      "severity": "HIGH",
      "recommended_human_action": "string"
    }}
  ],
  "conflict_count": 0,
  "programs_with_conflicts": []
}}

EVIDENCE: {json.dumps(evidence, indent=2)[:5000]}
BUNDLE: {json.dumps(summary, indent=2)[:4000]}
"""
        conflicts = _parse_json(_llm(self.SYSTEM, user))
        print(f"[Agent 3] ✓ Found {conflicts.get('conflict_count', '?')} conflicts")
        return conflicts


# ═══════════════════════════════════════════
# AGENT 4 — Confidence Scoring Agent
# ═══════════════════════════════════════════

class ConfidenceScoringAgent:

    SYSTEM = """You are a data quality assessor for public health.
Score confidence conservatively. Respond with valid JSON only."""

    def run(self, bundle: dict, evidence: dict, conflicts: dict) -> dict:
        print("[Agent 4] Scoring confidence...")

        user = f"""
Score confidence for each data source and program area.

Return JSON:
{{
  "source_confidence": {{
    "<source_name>": {{
      "score": 0.0,
      "grade": "A",
      "rationale": "string",
      "limitations": []
    }}
  }},
  "program_confidence": {{
    "<program_area>": {{
      "overall_score": 0.0,
      "grade": "A",
      "evidence_strength": "STRONG",
      "key_uncertainty": "string",
      "conflict_impact": "NONE"
    }}
  }},
  "overall_data_quality": "GOOD",
  "recommendation_reliability": "string"
}}

CONFLICTS: {json.dumps(conflicts, indent=2)[:3000]}
PROGRAMS: {list(evidence.keys())}
"""
        scores = _parse_json(_llm(self.SYSTEM, user))
        print("[Agent 4] ✓ Confidence scored")
        return scores


# ═══════════════════════════════════════════
# AGENT 5 — Allocation Agent
# ═══════════════════════════════════════════

class AllocationAgent:

    SYSTEM = """You are a senior public health resource allocation advisor.
Be data-driven and practical. Flag where human judgment is needed.
Respond with valid JSON only."""

    def run(self, bundle: dict, evidence: dict, conflicts: dict, scores: dict, total_budget: int = 1422000) -> dict:
        print("[Agent 5] Generating allocation recommendations...")

        summary = {k: v for k, v in bundle.items() if k != "_raw"}

        user = f"""
Produce a budget allocation recommendation for a community health clinic.
Total annual budget: ${total_budget:,}

Programs: Diabetes Management, Hypertension Control, Maternal Health,
Mental Health, Community Outreach, Administration

Return JSON:
{{
  "total_budget": {total_budget},
  "allocation_recommendations": {{
    "<program>": {{
      "recommended_amount": 0,
      "recommended_percentage": 0.0,
      "current_amount": 0,
      "change_direction": "INCREASE",
      "change_amount": 0,
      "primary_rationale": "string",
      "evidence_used": [],
      "confidence": 0.0,
      "human_review_required": false,
      "human_review_reason": null
    }}
  }},
  "allocation_summary": "string",
  "key_tradeoffs": [],
  "implementation_priorities": [
    {{"priority": 1, "action": "string", "program": "string", "timeline": "string"}}
  ],
  "flags_for_board": []
}}

BUDGET: {json.dumps(summary.get("budget_summary", {}), indent=2)}
EFFECTIVENESS: {json.dumps(summary.get("effectiveness_summary", {}), indent=2)}
CONFLICTS: {json.dumps(conflicts.get("conflicts", []), indent=2)[:2000]}
CONFIDENCE: {json.dumps(scores.get("program_confidence", {}), indent=2)}
"""
        allocation = _parse_json(_llm(self.SYSTEM, user))
        print("[Agent 5] ✓ Allocation complete")
        return allocation


# ═══════════════════════════════════════════
# PIPELINE RUNNER
# ═══════════════════════════════════════════

def run_pipeline(progress_callback=None) -> dict:

    def progress(step, msg):
        if progress_callback:
            progress_callback(step, msg)
        print(f"[Pipeline] {step}/5 — {msg}")

    progress(1, "Ingesting data via MCP server...")
    bundle = IngestionAgent().run()

    progress(2, "Extracting evidence per program area...")
    evidence = EvidenceExtractionAgent().run(bundle)

    progress(3, "Detecting conflicts between sources...")
    conflicts = ConflictDetectionAgent().run(bundle, evidence)

    progress(4, "Scoring source confidence...")
    scores = ConfidenceScoringAgent().run(bundle, evidence, conflicts)

    progress(5, "Generating allocation recommendations...")
    allocation = AllocationAgent().run(bundle, evidence, conflicts, scores)

    return {
        "bundle": {k: v for k, v in bundle.items() if k != "_raw"},
        "evidence": evidence,
        "conflicts": conflicts,
        "scores": scores,
        "allocation": allocation,
        "pipeline_status": "complete",
    }