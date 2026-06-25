"""
ImpactFrame MCP Server
----------------------
Serves health program data files to the agent pipeline via the
Model Context Protocol. Agents request data through this server
rather than reading files directly — making the system modular
and demonstrating MCP as an architectural pattern.

Tools exposed:
  - list_available_datasets
  - get_dataset
  - get_dataset_metadata
"""

import os
import json
import csv
import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ── Configuration ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"

DATASET_REGISTRY = {
    "population_health": {
        "file": "population_health.csv",
        "description": "Population-level health data by program area including prevalence rates, ER visits, and high-risk subgroups",
        "format": "csv",
        "source_type": "epidemiological",
    },
    "budget_current": {
        "file": "budget_current.csv",
        "description": "Current annual budget allocations, staff FTE, funding sources, and shortfalls per program",
        "format": "csv",
        "source_type": "financial",
    },
    "staff_availability": {
        "file": "staff_availability.csv",
        "description": "Staff roster with utilization rates, certifications, burnout risk, and availability",
        "format": "csv",
        "source_type": "operational",
    },
    "community_survey": {
        "file": "community_survey.csv",
        "description": "Community survey responses capturing health concerns, access barriers, and program priorities",
        "format": "csv",
        "source_type": "community_voice",
    },
    "program_effectiveness": {
        "file": "program_effectiveness.txt",
        "description": "Annual program effectiveness report with ROI analysis, outcomes data, and QI recommendations",
        "format": "text",
        "source_type": "clinical_evidence",
    },
}

# ── Server Setup ────────────────────────────────────────────────
server = Server("impactframe-data-server")


def _read_csv_as_records(filepath: Path) -> list[dict]:
    """Read a CSV file and return as list of dicts."""
    records = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    return records


def _read_text_file(filepath: Path) -> str:
    """Read a plain text file."""
    with open(filepath, encoding="utf-8") as f:
        return f.read()


# ── Tool: list_available_datasets ───────────────────────────────
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_available_datasets",
            description="Returns the names and descriptions of all datasets available in the ImpactFrame data server.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_dataset",
            description=(
                "Retrieves the full contents of a named dataset. "
                "CSV files are returned as JSON records. Text files are returned as a string."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_name": {
                        "type": "string",
                        "description": "Name of the dataset to retrieve (use list_available_datasets to see options)",
                    }
                },
                "required": ["dataset_name"],
            },
        ),
        types.Tool(
            name="get_dataset_metadata",
            description="Returns metadata for a specific dataset without loading its full contents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_name": {
                        "type": "string",
                        "description": "Name of the dataset",
                    }
                },
                "required": ["dataset_name"],
            },
        ),
    ]


# ── Tool Handlers ───────────────────────────────────────────────
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:

    # ── list_available_datasets ──────────────────────────────
    if name == "list_available_datasets":
        summary = {
            k: {
                "description": v["description"],
                "format": v["format"],
                "source_type": v["source_type"],
            }
            for k, v in DATASET_REGISTRY.items()
        }
        return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]

    # ── get_dataset ──────────────────────────────────────────
    elif name == "get_dataset":
        dataset_name = arguments.get("dataset_name", "").strip()

        # Security: only allow registered dataset names
        if dataset_name not in DATASET_REGISTRY:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"Dataset '{dataset_name}' not found.",
                        "available": list(DATASET_REGISTRY.keys()),
                    }),
                )
            ]

        meta = DATASET_REGISTRY[dataset_name]
        filepath = DATA_DIR / meta["file"]

        if not filepath.exists():
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"File not found on disk: {meta['file']}"}),
                )
            ]

        if meta["format"] == "csv":
            records = _read_csv_as_records(filepath)
            payload = {
                "dataset_name": dataset_name,
                "source_type": meta["source_type"],
                "record_count": len(records),
                "records": records,
            }
            return [types.TextContent(type="text", text=json.dumps(payload, indent=2))]

        elif meta["format"] == "text":
            content = _read_text_file(filepath)
            payload = {
                "dataset_name": dataset_name,
                "source_type": meta["source_type"],
                "content": content,
            }
            return [types.TextContent(type="text", text=json.dumps(payload, indent=2))]

    # ── get_dataset_metadata ─────────────────────────────────
    elif name == "get_dataset_metadata":
        dataset_name = arguments.get("dataset_name", "").strip()
        if dataset_name not in DATASET_REGISTRY:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"Dataset '{dataset_name}' not found."}),
                )
            ]
        return [
            types.TextContent(
                type="text",
                text=json.dumps(DATASET_REGISTRY[dataset_name], indent=2),
            )
        ]

    return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ── Entry Point ─────────────────────────────────────────────────
async def main():
    print("ImpactFrame MCP Server starting on stdio...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
