"""
Abhi-Nexus MCP Server
=====================
Exposes your pipeline as MCP tools so any MCP client
(Cursor, Open WebUI, your own agent) can call it.

Add this file to your z:/abhi-nexus/ root folder.

Install: pip install fastmcp
Run:     python mcp_server.py
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

# ── Path setup ────────────────────────────────────────────────────────────────
# Adjust this if you run the server from a different working directory
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# Add project root to path so we can import your existing modules
sys.path.insert(0, str(BASE_DIR))

# ── MCP server instance ───────────────────────────────────────────────────────
mcp = FastMCP(host="0.0.0.0", port=7070, 
    name="Abhi-Nexus",
    instructions="""
    You are connected to Abhi-Nexus — a multi-agent autonomous news pipeline.
    It fetches articles from 20+ RSS feeds, ranks them using AI, generates
    audio summaries, and delivers a daily email digest.

    Available tools:
    - trigger_pipeline: Run the full pipeline manually
    - get_articles: Fetch ranked articles with filters
    - get_pipeline_status: Check if pipeline is healthy
    - get_settings: View current pipeline settings
    - update_setting: Change a specific setting
    - get_raw_articles: See unranked raw articles
    - get_top_articles: Shortcut for top N articles
    """,
)


# ── Helper ────────────────────────────────────────────────────────────────────
def _read_json(filename: str) -> dict | list:
    """Safely read a JSON file from the data directory."""
    path = DATA_DIR / filename
    if not path.exists():
        return {"error": f"{filename} not found. Has the pipeline run yet?"}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(filename: str, data: dict | list) -> None:
    """Safely write a JSON file to the data directory."""
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── TOOL 1: Trigger the full pipeline ────────────────────────────────────────
@mcp.tool()
def trigger_pipeline() -> dict:
    """
    Manually trigger the full Abhi-Nexus pipeline.
    Runs: Fetch → Rank → TTS → Email delivery.
    Use this when you want fresh articles outside the scheduled 8:15 AM run.
    """
    try:
        from master_agent import MasterAgent
        agent = MasterAgent()
        result = agent.run_pipeline()
        return {
            "status": "success",
            "message": "Pipeline completed successfully",
            "result": str(result),
            "triggered_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Pipeline failed: {str(e)}",
            "triggered_at": datetime.now().isoformat(),
        }


# ── TOOL 2: Get ranked articles ───────────────────────────────────────────────
@mcp.tool()
def get_articles(
    limit: int = 10,
    category: str = "",
    min_score: int = 0,
) -> dict:
    """
    Fetch ranked articles from the last pipeline run.

    Args:
        limit:     How many articles to return (default 10, max 50)
        category:  Filter by category e.g. "AI", "Python", "Security" (optional)
        min_score: Only return articles with score >= this value (default 0)

    Returns ranked articles sorted by score, highest first.
    """
    data = _read_json("ranked_articles.json")

    if "error" in data:
        return data

    articles = data if isinstance(data, list) else data.get("articles", [])

    # Apply filters
    if category:
        articles = [
            a for a in articles
            if category.lower() in str(a.get("category", "")).lower()
            or category.lower() in str(a.get("tags", "")).lower()
            or category.lower() in str(a.get("title", "")).lower()
        ]

    if min_score > 0:
        articles = [a for a in articles if a.get("score", 0) >= min_score]

    # Sort by score descending
    articles = sorted(articles, key=lambda x: x.get("score", 0), reverse=True)

    # Apply limit
    limit = min(limit, 50)
    articles = articles[:limit]

    return {
        "total_returned": len(articles),
        "filters_applied": {
            "category": category or "none",
            "min_score": min_score,
            "limit": limit,
        },
        "articles": articles,
    }


# ── TOOL 3: Get top N articles (quick shortcut) ───────────────────────────────
@mcp.tool()
def get_top_articles(n: int = 3) -> dict:
    """
    Quick shortcut — get the top N highest-scored articles.
    Perfect for: 'give me top 3 articles and do deep research on them'.

    Args:
        n: Number of top articles to return (default 3)
    """
    return get_articles(limit=n, min_score=50)


# ── TOOL 4: Pipeline status ───────────────────────────────────────────────────
@mcp.tool()
def get_pipeline_status() -> dict:
    """
    Check the current health and status of the Abhi-Nexus pipeline.
    Shows last run time, article counts, and any errors.
    """
    ranked = _read_json("ranked_articles.json")
    raw    = _read_json("raw_articles.json")

    ranked_count = len(ranked) if isinstance(ranked, list) else 0
    raw_count    = len(raw)    if isinstance(raw, list)    else 0

    # Try to get last modified time of ranked_articles.json
    ranked_path = DATA_DIR / "ranked_articles.json"
    last_run = "Never"
    if ranked_path.exists():
        ts = ranked_path.stat().st_mtime
        last_run = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "pipeline": "Abhi-Nexus",
        "status": "healthy" if ranked_count > 0 else "no_data",
        "last_run": last_run,
        "raw_articles_count": raw_count,
        "ranked_articles_count": ranked_count,
        "data_directory": str(DATA_DIR),
        "checked_at": datetime.now().isoformat(),
    }


# ── TOOL 5: Get settings ──────────────────────────────────────────────────────
@mcp.tool()
def get_settings() -> dict:
    """
    View current Abhi-Nexus pipeline settings.
    Shows RSS sources, schedule, email config, scoring weights etc.
    """
    settings = _read_json("settings.json")
    if "error" in settings:
        return settings

    # Mask sensitive values before returning
    safe = json.loads(json.dumps(settings))  # deep copy
    if "email" in safe:
        if "password" in safe["email"]:
            safe["email"]["password"] = "***hidden***"
        if "smtp_password" in safe["email"]:
            safe["email"]["smtp_password"] = "***hidden***"

    return safe


# ── TOOL 6: Update a setting ──────────────────────────────────────────────────
@mcp.tool()
def update_setting(key: str, value: str) -> dict:
    """
    Update a specific pipeline setting without restarting.
    Changes are picked up on the next scheduled run automatically.

    Args:
        key:   The setting key to update e.g. "schedule_time", "email_limit"
        value: The new value as a string

    Examples:
        update_setting("schedule_time", "09:00")
        update_setting("max_articles_per_run", "30")
    """
    settings = _read_json("settings.json")
    if "error" in settings:
        return settings

    # Block sensitive keys from being updated via MCP
    blocked = {"email", "password", "smtp_password", "api_key", "secret"}
    if any(b in key.lower() for b in blocked):
        return {
            "status": "blocked",
            "message": f"Cannot update '{key}' via MCP for security reasons.",
        }

    old_value = settings.get(key, "not_set")
    settings[key] = value
    _write_json("settings.json", settings)

    return {
        "status": "success",
        "key": key,
        "old_value": str(old_value),
        "new_value": value,
        "updated_at": datetime.now().isoformat(),
        "note": "Change will apply on next pipeline run.",
    }


# ── TOOL 7: Get raw articles ──────────────────────────────────────────────────
@mcp.tool()
def get_raw_articles(limit: int = 10) -> dict:
    """
    Fetch raw (unranked) articles straight from RSS feeds.
    These are Bronze layer articles — before AI scoring.
    Useful for debugging or seeing what was fetched before ranking.

    Args:
        limit: How many raw articles to return (default 10)
    """
    data = _read_json("raw_articles.json")

    if "error" in data:
        return data

    articles = data if isinstance(data, list) else []
    return {
        "total_raw": len(articles),
        "showing": min(limit, len(articles)),
        "articles": articles[:limit],
    }


# ── RESOURCE: ranked_articles.json as a readable resource ────────────────────
@mcp.resource("abhinexus://articles/ranked")
def ranked_articles_resource() -> str:
    """
    Direct read access to ranked_articles.json.
    MCP clients can read this as a document, not just call it as a tool.
    """
    data = _read_json("ranked_articles.json")
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.resource("abhinexus://status")
def status_resource() -> str:
    """Pipeline status as a readable resource."""
    return json.dumps(get_pipeline_status(), indent=2)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting Abhi-Nexus MCP Server...")
    print(f"Data directory: {DATA_DIR}")
    print("Tools exposed: trigger_pipeline, get_articles, get_top_articles,")
    print("               get_pipeline_status, get_settings, update_setting,")
    print("               get_raw_articles")
    print()
    mcp.run(transport="sse")