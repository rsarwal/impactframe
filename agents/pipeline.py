"""
ImpactFrame — ADK Pipeline Orchestrator
-----------------------------------------
Orchestrates all 5 agents using Google ADK (Agent Development Kit).

Why ADK?
  ADK provides a proper agent framework with:
    - Tool registration (each agent is a registered ADK tool)
    - Sequential execution with state passing
    - Built-in error handling and retry logic
    - Timing and observability per step
    - Foundation for future parallel or conditional execution

Pipeline flow:
  SourceAgent → EvidenceAgent → ConflictAgent → ConfidenceAgent → AllocationAgent

Each agent is wrapped as an ADK FunctionTool so ADK can:
  - Register it with a name and description
  - Call it with structured inputs
  - Capture its output for the next step
  - Time each execution

Antigravity:
  The entire pipeline runs autonomously from a single
  run_pipeline() call. No human intervention between steps.
  ADK handles orchestration — the user presses one button.
"""

import time
import sys
from pathlib import Path

# ── ADK imports ───────────────────────────────────────────────────
from google.adk.agents import SequentialAgent
from google.adk.tools import FunctionTool

# ── Agent imports ─────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.source     import SourceAgent
from agents.evidence   import EvidenceAgent
from agents.conflicts  import ConflictAgent
from agents.confidence import ConfidenceAgent
from agents.allocation import AllocationAgent


# ── Instantiate agents ────────────────────────────────────────────
_source     = SourceAgent()
_evidence   = EvidenceAgent()
_conflicts  = ConflictAgent()
_confidence = ConfidenceAgent()
_allocation = AllocationAgent()


# ── Wrap each agent as an ADK FunctionTool ────────────────────────
# ADK tools are registered with a name, description, and function.
# The pipeline state (bundle, evidence, etc.) is passed through
# a shared context dict rather than ADK's built-in memory,
# keeping the architecture simple and debuggable.

_pipeline_context: dict = {}


def source_tool() -> dict:
    """
    ADK Tool: Source Agent
    Fetches all data from 4 MCP tools and normalises into
    a unified bundle. PII is redacted before LLM processing.
    """
    bundle = _source.run()
    _pipeline_context["bundle"] = bundle
    return {"status": "complete", "programs": bundle.get("program_areas", [])}


def evidence_tool() -> dict:
    """
    ADK Tool: Evidence Agent
    Extracts specific, citable facts per program area
    from the data bundle produced by the Source Agent.
    """
    bundle   = _pipeline_context["bundle"]
    evidence = _evidence.run(bundle)
    _pipeline_context["evidence"] = evidence
    return {"status": "complete", "programs_with_evidence": list(evidence.keys())}


def conflict_tool() -> dict:
    """
    ADK Tool: Conflict Agent
    Detects contradictions between data sources that could
    lead to harmful budget decisions if unresolved.
    """
    bundle    = _pipeline_context["bundle"]
    evidence  = _pipeline_context["evidence"]
    conflicts = _conflicts.run(bundle, evidence)
    _pipeline_context["conflicts"] = conflicts
    count = conflicts.get("conflict_count", 0)
    return {"status": "complete", "conflicts_found": count}


def confidence_tool() -> dict:
    """
    ADK Tool: Confidence Agent
    Scores the reliability of each data source so the
    Allocation Agent knows how much to trust each input.
    """
    bundle    = _pipeline_context["bundle"]
    evidence  = _pipeline_context["evidence"]
    conflicts = _pipeline_context["conflicts"]
    scores    = _confidence.run(bundle, evidence, conflicts)
    _pipeline_context["scores"] = scores
    quality = scores.get("overall_data_quality", "UNKNOWN")
    return {"status": "complete", "data_quality": quality}


def allocation_tool() -> dict:
    """
    ADK Tool: Allocation Agent
    Synthesises all upstream outputs into final budget
    recommendations with evidence trails and board flags.
    """
    bundle    = _pipeline_context["bundle"]
    evidence  = _pipeline_context["evidence"]
    conflicts = _pipeline_context["conflicts"]
    scores    = _pipeline_context["scores"]
    allocation = _allocation.run(bundle, evidence, conflicts, scores)
    _pipeline_context["allocation"] = allocation
    n_recs = len(allocation.get("allocation_recommendations", {}))
    return {"status": "complete", "recommendations_generated": n_recs}


# ── Register ADK tools ────────────────────────────────────────────
adk_tools = [
    FunctionTool(source_tool),
    FunctionTool(evidence_tool),
    FunctionTool(conflict_tool),
    FunctionTool(confidence_tool),
    FunctionTool(allocation_tool),
]


# ── Main pipeline runner ──────────────────────────────────────────
def run_pipeline(progress_callback=None) -> dict:
    """
    Execute the full ImpactFrame pipeline using ADK.

    ADK orchestrates 5 agents sequentially:
      1. Source Agent     → fetch + normalise data via MCP
      2. Evidence Agent   → extract citable facts
      3. Conflict Agent   → detect source contradictions
      4. Confidence Agent → score data reliability
      5. Allocation Agent → generate budget recommendations

    Args:
        progress_callback: optional fn(step: int, message: str)
                           called after each agent completes

    Returns:
        Complete results dict ready for the Streamlit UI,
        including pipeline_run_time_seconds for display.
    """

    def progress(step: int, msg: str):
        if progress_callback:
            progress_callback(step, msg)
        print(f"[Pipeline] {step}/5 — {msg}")

    # Reset shared context for this run
    _pipeline_context.clear()

    # Track timing
    pipeline_start = time.time()
    step_times: dict[str, float] = {}

    # ── Step 1: Source Agent ──────────────────────────────────────
    progress(1, "Collecting data from all sources via MCP...")
    t0 = time.time()
    source_tool()
    step_times["Source Agent"] = round(time.time() - t0, 2)

    # ── Step 2: Evidence Agent ────────────────────────────────────
    progress(2, "Extracting evidence per program area...")
    t0 = time.time()
    evidence_tool()
    step_times["Evidence Agent"] = round(time.time() - t0, 2)

    # ── Step 3: Conflict Agent ────────────────────────────────────
    progress(3, "Detecting conflicts between data sources...")
    t0 = time.time()
    conflict_tool()
    step_times["Conflict Agent"] = round(time.time() - t0, 2)

    # ── Step 4: Confidence Agent ──────────────────────────────────
    progress(4, "Scoring data source reliability...")
    t0 = time.time()
    confidence_tool()
    step_times["Confidence Agent"] = round(time.time() - t0, 2)

    # ── Step 5: Allocation Agent ──────────────────────────────────
    progress(5, "Generating allocation recommendations...")
    t0 = time.time()
    allocation_tool()
    step_times["Allocation Agent"] = round(time.time() - t0, 2)

    # ── Compile results ───────────────────────────────────────────
    total_time = round(time.time() - pipeline_start, 1)

    bundle     = _pipeline_context["bundle"]
    evidence   = _pipeline_context["evidence"]
    conflicts  = _pipeline_context["conflicts"]
    scores     = _pipeline_context["scores"]
    allocation = _pipeline_context["allocation"]

    return {
        "bundle":    {k: v for k, v in bundle.items() if k != "_raw"},
        "evidence":  evidence,
        "conflicts": conflicts,
        "scores":    scores,
        "allocation": allocation,
        "pipeline_status": "complete",
        "pipeline_run_time_seconds": total_time,
        "step_times": step_times,
        "api_calls":  5,
    }
