"""
LLM Analysis Service
Provides AI-powered analysis of EVE Online combat data using OpenAI.
"""

import os
import json
import redis
import psycopg2
from openai import OpenAI
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from ~/.env
load_dotenv(dotenv_path=os.path.expanduser("~/.env"))

# Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Database connection settings
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "eve_sde",
    "user": "eve",
    "password": "EvE_Pr0ject_2024"
}

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("[WARNING] OPENAI_API_KEY not found in environment")

# OpenAI client
openai_client = OpenAI(api_key=api_key) if api_key else None

# Cache TTL: 1 hour
ANALYSIS_CACHE_TTL = 3600

# History settings
HISTORY_KEY = "report:alliance_wars_analysis:history"
HISTORY_MAX_ENTRIES = 3  # Keep last 3 snapshots
HISTORY_TTL = 86400  # 24 hours

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

    # Get historical data for trend analysis
    history = _get_history()
    history_context = _build_history_context(history)

    # Extract metrics for saving later
    current_metrics = _extract_key_metrics(wars_data)

    # Generate analysis
    trend_instruction = ""
    if history:
        trend_instruction = """
Additionally, compare with previous snapshots and identify:
- Trends: Which coalitions are improving or declining?
- Changes: What significant shifts occurred since the last analysis?
- Momentum: Who has the momentum right now?

Include a "trends" field with 2-3 trend observations."""

    prompt = f"""You are an EVE Online military intelligence analyst. Analyze the following 24-hour alliance warfare data and provide:

1. A concise situation summary (2-3 paragraphs) describing the current state of nullsec warfare
2. 5-7 key strategic insights as bullet points
{trend_instruction}

Focus on:
- Which coalitions/alliances are winning or losing
- Notable shifts in power dynamics
- Economic impact (ISK destroyed)
- Strategic implications for pilots and corporations

Current Data:
{context}
{history_context}

Respond in JSON format:
{{
    "summary": "Your 2-3 paragraph analysis here...",
    "insights": [
        "First key insight...",
        "Second key insight...",
        ...
    ],
    "trends": ["Trend observation 1...", "Trend observation 2..."],
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
        if "trends" not in result:
            result["trends"] = []
        if "generated_at" not in result:
            result["generated_at"] = datetime.utcnow().isoformat() + "Z"

        # Save to history for future trend analysis (Redis - short term)
        _save_to_history(current_metrics, result.get("insights", []))

        # Save to database for long-term history (PostgreSQL)
        _save_analysis_to_db(result, current_metrics)

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


def _extract_key_metrics(wars_data: Dict) -> Dict:
    """Extract key metrics from wars data for historical comparison."""
    g = wars_data.get("global", {})
    coalitions = wars_data.get("coalitions", [])

    # Extract top coalition metrics
    coalition_metrics = []
    for c in coalitions[:6]:
        coalition_metrics.append({
            "name": c.get("name", "Unknown"),
            "kills": c.get("total_kills", 0),
            "losses": c.get("total_losses", 0),
            "isk_destroyed": round(c.get("isk_destroyed", 0) / 1_000_000_000, 2),
            "isk_lost": round(c.get("isk_lost", 0) / 1_000_000_000, 2),
            "efficiency": round(c.get("efficiency", 0), 1)
        })

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "global": {
            "total_kills": g.get("total_kills", 0),
            "total_isk_destroyed": round(g.get("total_isk_destroyed", 0) / 1_000_000_000, 2),
            "active_conflicts": g.get("active_conflicts", 0)
        },
        "coalitions": coalition_metrics
    }


def _save_to_history(metrics: Dict, insights: list):
    """Save current metrics and insights to history."""
    history_entry = {
        "metrics": metrics,
        "insights": insights[:5]  # Keep top 5 insights
    }

    # Get existing history
    existing = redis_client.get(HISTORY_KEY)
    history = json.loads(existing) if existing else []

    # Add new entry at the beginning
    history.insert(0, history_entry)

    # Keep only last N entries
    history = history[:HISTORY_MAX_ENTRIES]

    # Save back
    redis_client.setex(HISTORY_KEY, HISTORY_TTL, json.dumps(history))
    print(f"[HISTORY] Saved snapshot, {len(history)} entries in history")


def _get_history() -> list:
    """Get historical analysis data."""
    existing = redis_client.get(HISTORY_KEY)
    return json.loads(existing) if existing else []


def _build_history_context(history: list) -> str:
    """Build context string from historical data."""
    if not history:
        return ""

    lines = ["\n=== HISTORICAL DATA (Previous Snapshots) ==="]

    for i, entry in enumerate(history):
        metrics = entry.get("metrics", {})
        insights = entry.get("insights", [])
        timestamp = metrics.get("timestamp", "Unknown")

        lines.append(f"\n--- Snapshot {i+1} ({timestamp}) ---")

        # Global metrics
        g = metrics.get("global", {})
        lines.append(f"Global: {g.get('total_kills', 0):,} kills, {g.get('total_isk_destroyed', 0):.2f}B ISK")

        # Coalition metrics
        for c in metrics.get("coalitions", [])[:4]:
            lines.append(f"  {c.get('name')}: {c.get('efficiency', 0)}% eff, {c.get('isk_destroyed', 0):.1f}B destroyed")

        # Previous insights
        if insights:
            lines.append("Key insights at that time:")
            for insight in insights[:3]:
                # Truncate long insights
                short = insight[:150] + "..." if len(insight) > 150 else insight
                lines.append(f"  - {short}")

    return "\n".join(lines)


def _save_analysis_to_db(result: Dict, metrics: Dict, analysis_type: str = "alliance_wars"):
    """Persist analysis to PostgreSQL for long-term history."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO llm_analyses (analysis_type, summary, insights, trends, metrics, model, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            analysis_type,
            result.get("summary", ""),
            json.dumps(result.get("insights", [])),
            json.dumps(result.get("trends", [])),
            json.dumps(metrics),
            LLM_MODEL,
            result.get("generated_at", datetime.utcnow().isoformat() + "Z")
        ))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[DB] Saved analysis to database")
    except Exception as e:
        print(f"[DB ERROR] Failed to save analysis: {e}")


def get_analysis_history(analysis_type: str = "alliance_wars", limit: int = 24) -> List[Dict]:
    """Retrieve historical analyses from database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, summary, insights, trends, metrics, model, generated_at
            FROM llm_analyses
            WHERE analysis_type = %s
            ORDER BY generated_at DESC
            LIMIT %s
        """, (analysis_type, limit))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [{
            "id": row[0],
            "summary": row[1],
            "insights": row[2] if isinstance(row[2], list) else json.loads(row[2]) if row[2] else [],
            "trends": row[3] if isinstance(row[3], list) else json.loads(row[3]) if row[3] else [],
            "metrics": row[4] if isinstance(row[4], dict) else json.loads(row[4]) if row[4] else {},
            "model": row[5],
            "generated_at": row[6].isoformat() if row[6] else None
        } for row in rows]
    except Exception as e:
        print(f"[DB ERROR] Failed to retrieve history: {e}")
        return []
