"""
LLM Analysis Service
Provides AI-powered analysis of EVE Online combat data using OpenAI.
"""

import os
import json
import redis
from openai import OpenAI
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from ~/.env
load_dotenv(dotenv_path=os.path.expanduser("~/.env"))

# Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("[WARNING] OPENAI_API_KEY not found in environment")

# OpenAI client
openai_client = OpenAI(api_key=api_key) if api_key else None

# Cache TTL: 1 hour
ANALYSIS_CACHE_TTL = 3600

# Model
LLM_MODEL = "gpt-5-mini"


def generate_alliance_wars_analysis(wars_data: Dict) -> Dict:
    """
    Generate LLM analysis of Alliance Wars data.

    Args:
        wars_data: The alliance wars report data

    Returns:
        Dict with 'summary' (text) and 'insights' (list of bullet points)
    """
    cache_key = "report:alliance_wars_analysis:1h"

    # Check cache first
    cached = redis_client.get(cache_key)
    if cached:
        print("[CACHE HIT] Returning cached alliance wars analysis")
        return json.loads(cached)

    print("[CACHE MISS] Generating new alliance wars analysis via LLM...")

    if not openai_client:
        return {
            "summary": "Analysis unavailable - OpenAI API key not configured.",
            "insights": [],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "error": "OPENAI_API_KEY not set"
        }

    # Build context for LLM
    context = _build_analysis_context(wars_data)

    # Generate analysis
    prompt = f"""You are an EVE Online military intelligence analyst. Analyze the following 24-hour alliance warfare data and provide:

1. A concise situation summary (2-3 paragraphs) describing the current state of nullsec warfare
2. 5-7 key strategic insights as bullet points

Focus on:
- Which coalitions/alliances are winning or losing
- Notable shifts in power dynamics
- Economic impact (ISK destroyed)
- Strategic implications for pilots and corporations

Data:
{context}

Respond in JSON format:
{{
    "summary": "Your 2-3 paragraph analysis here...",
    "insights": [
        "First key insight...",
        "Second key insight...",
        ...
    ],
    "generated_at": "{datetime.utcnow().isoformat()}Z"
}}"""

    try:
        response = openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert EVE Online military analyst. Provide concise, data-driven analysis. Always respond in valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=4000,
            response_format={"type": "json_object"}
        )

        result_text = response.choices[0].message.content

        if not result_text:
            # Check if there's a refusal or other issue
            finish_reason = response.choices[0].finish_reason
            print(f"[DEBUG] Finish reason: {finish_reason}")
            if hasattr(response.choices[0].message, 'refusal') and response.choices[0].message.refusal:
                print(f"[DEBUG] Refusal: {response.choices[0].message.refusal}")
            return {
                "summary": "Analysis unavailable - LLM returned empty response.",
                "insights": [],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": f"Empty response, finish_reason: {finish_reason}"
            }

        result = json.loads(result_text)

        # Ensure required fields
        if "summary" not in result:
            result["summary"] = "Analysis unavailable."
        if "insights" not in result:
            result["insights"] = []
        if "generated_at" not in result:
            result["generated_at"] = datetime.utcnow().isoformat() + "Z"

        # Cache the result
        redis_client.setex(cache_key, ANALYSIS_CACHE_TTL, json.dumps(result))
        print(f"[CACHE] Cached alliance wars analysis for {ANALYSIS_CACHE_TTL}s")

        return result

    except Exception as e:
        print(f"[ERROR] LLM analysis failed: {e}")
        return {
            "summary": "Analysis temporarily unavailable due to a technical issue.",
            "insights": [],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }


def _build_analysis_context(wars_data: Dict) -> str:
    """Build a condensed context string for the LLM."""
    lines = []

    # Global stats
    g = wars_data.get("global", {})
    lines.append(f"=== GLOBAL SUMMARY (24h) ===")
    lines.append(f"Active Conflicts: {g.get('active_conflicts', 0)}")
    lines.append(f"Alliances Involved: {g.get('total_alliances_involved', 0)}")
    lines.append(f"Total Kills: {g.get('total_kills', 0):,}")
    lines.append(f"Total ISK Destroyed: {g.get('total_isk_destroyed', 0) / 1_000_000_000:.2f}B ISK")
    lines.append("")

    # Coalitions
    coalitions = wars_data.get("coalitions", [])
    if coalitions:
        lines.append(f"=== POWER BLOCS ({len(coalitions)} detected) ===")
        for c in coalitions[:6]:  # Top 6
            lines.append(f"- {c.get('name', 'Unknown')} ({c.get('member_count', 0)} alliances)")
            lines.append(f"  Kills: {c.get('total_kills', 0):,} | Losses: {c.get('total_losses', 0):,}")
            lines.append(f"  ISK Destroyed: {c.get('isk_destroyed', 0) / 1_000_000_000:.2f}B | ISK Lost: {c.get('isk_lost', 0) / 1_000_000_000:.2f}B")
            lines.append(f"  Efficiency: {c.get('efficiency', 0):.1f}%")
        lines.append("")

    # Active conflicts
    conflicts = wars_data.get("conflicts", [])
    if conflicts:
        lines.append(f"=== ACTIVE CONFLICTS ({len(conflicts)}) ===")
        for c in conflicts[:5]:  # Top 5
            lines.append(f"- {c.get('alliance_1_name', '?')} vs {c.get('alliance_2_name', '?')}")
            lines.append(f"  Region: {', '.join(c.get('primary_regions', ['Unknown']))}")
            lines.append(f"  {c.get('alliance_1_name', '?')}: {c.get('alliance_1_kills', 0)} kills, {c.get('alliance_1_efficiency', 0):.1f}% efficiency")
            lines.append(f"  {c.get('alliance_2_name', '?')}: {c.get('alliance_2_kills', 0)} kills, {c.get('alliance_2_efficiency', 0):.1f}% efficiency")
            if c.get('winner'):
                lines.append(f"  Current Winner: {c.get('winner')}")
        lines.append("")

    # Unaffiliated
    unaffiliated = wars_data.get("unaffiliated_alliances", [])
    if unaffiliated:
        lines.append(f"=== INDEPENDENT OPERATORS ({len(unaffiliated)}) ===")
        for a in unaffiliated[:5]:
            lines.append(f"- {a.get('name', '?')}: {a.get('kills', 0)} kills")

    return "\n".join(lines)


def invalidate_analysis_cache():
    """Manually invalidate the analysis cache."""
    redis_client.delete("report:alliance_wars_analysis:1h")
    print("[CACHE] Alliance wars analysis cache invalidated")
