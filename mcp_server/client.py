"""
ImpactFrame MCP Client
----------------------
Calls MCP server tools directly.
All data passes through the security redactor before
being returned to agents — ensuring PII never reaches the LLM.
"""

import csv
import json
from pathlib import Path

# Security layer — redacts PII before data goes to agents
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from security.redactor import redact_dataset, log_redaction_event

DATA_DIR = Path(__file__).parent.parent / "data"


def _read_csv(filename):
    rows = []
    with open(DATA_DIR / filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(dict(row))
    return rows


def _read_text(filename):
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return f.read()


class MCPClient:
    """
    Exposes 4 MCP tools as Python methods.
    Each method:
      1. Reads raw data from disk
      2. Passes through PII redactor (security layer)
      3. Returns clean, redacted data to agents
    """

    def get_health_data(self) -> dict:
        raw = {
            "source": "get_health_data",
            "population_health":  _read_csv("population_health.csv"),
            "staff_availability": _read_csv("staff_availability.csv"),
        }
        redacted = redact_dataset(raw)
        log_redaction_event(
            "get_health_data",
            len(raw["population_health"]) + len(raw["staff_availability"])
        )
        return redacted

    def get_survey_results(self) -> dict:
        survey = _read_csv("community_survey.csv")
        raw = {
            "source": "get_survey_results",
            "survey_responses": survey,
            "total_responses":  len(survey),
        }
        redacted = redact_dataset(raw)
        log_redaction_event("get_survey_results", len(survey))
        return redacted

    def get_budget_constraints(self) -> dict:
        budget = _read_csv("budget_current.csv")
        raw = {
            "source": "get_budget_constraints",
            "budget_data": budget,
        }
        redacted = redact_dataset(raw)
        log_redaction_event("get_budget_constraints", len(budget))
        return redacted

    def get_program_effectiveness(self) -> dict:
        raw = {
            "source": "get_program_effectiveness",
            "report_content": _read_text("program_effectiveness.txt"),
        }
        redacted = redact_dataset(raw)
        log_redaction_event("get_program_effectiveness", 1)
        return redacted


mcp = MCPClient()
