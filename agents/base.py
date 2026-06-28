"""
ImpactFrame — Agent Base Module
--------------------------------
Shared utilities used by all 5 agents:
  - _llm()        : calls Gemini with system + user prompt
  - _parse_json() : robustly extracts JSON from LLM response

Why a separate base module?
  So we don't repeat the same 30 lines in every agent file.
  All agents import from here — one place to change the model
  or update the JSON parser.
"""

import os
import json
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

# ── Gemini client ─────────────────────────────────────────────────
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL  = "models/gemini-flash-lite-latest"


def _llm(system: str, user: str) -> str:
    """
    Call Gemini with a system instruction and user prompt.
    Returns the raw text response.
    """
    response = client.models.generate_content(
        model=MODEL,
        contents=user,
        config=genai.types.GenerateContentConfig(
            system_instruction=system,
        ),
    )
    return response.text


def _parse_json(text: str):
    """
    Robustly extract JSON from an LLM response.
    Handles markdown fences, extra prose, and partial matches.
    Raises ValueError if no valid JSON can be found.
    """
    # 1. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. Find first JSON block
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response:\n{text[:400]}")
