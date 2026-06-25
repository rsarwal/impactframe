"""
ImpactFrame MCP Client
----------------------
Calls MCP server tools directly (same process).
The MCP server tools are registered and callable without subprocess.
"""

import csv
import json
from pathlib import Path

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
    Exposes the 4 MCP tools as Python methods.
    Data is fetched from the same files the MCP server would serve —
    keeping the MCP architecture intact while avoiding subprocess issues.
    """

    def get_health_data(self) -> dict:
        return {
            "source": "get_health_data",
            "population_health": _read_csv("population_health.csv"),
            "staff_availability": _read_csv("staff_availability.csv"),
        }

    def get_survey_results(self) -> dict:
        survey = _read_csv("community_survey.csv")
        return {
            "source": "get_survey_results",
            "survey_responses": survey,
            "total_responses": len(survey),
        }

    def get_budget_constraints(self) -> dict:
        return {
            "source": "get_budget_constraints",
            "budget_data": _read_csv("budget_current.csv"),
        }

    def get_program_effectiveness(self) -> dict:
        return {
            "source": "get_program_effectiveness",
            "report_content": _read_text("program_effectiveness.txt"),
        }


mcp = MCPClient()