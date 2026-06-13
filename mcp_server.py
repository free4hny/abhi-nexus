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



"""
Security Scanning Tools for Abhi-Nexus MCP Server
===================================================
Add these tools to your existing mcp_server.py file.

Also add to requirements.txt:
    pip-audit

And install inside Docker:
    docker exec abhi-nexus pip install pip-audit
"""

import json
import re
import subprocess
from pathlib import Path
from datetime import datetime


# ── TOOL 8: Scan for vulnerable dependencies ──────────────────────────────────
@mcp.tool()
def scan_vulnerabilities(target: str = "all") -> dict:
    """
    Scan Abhi-Nexus for security vulnerabilities.

    Args:
        target: What to scan:
                "dependencies" — check Python packages against CVE database
                "secrets"      — scan code for hardcoded API keys or passwords
                "all"          — run both scans (default)

    Returns a report of any vulnerabilities found.
    """
    results = {
        "scanned_at": datetime.now().isoformat(),
        "target": target,
        "dependency_scan": None,
        "secrets_scan": None,
        "summary": {}
    }

    if target in ("dependencies", "all"):
        results["dependency_scan"] = _scan_dependencies()

    if target in ("secrets", "all"):
        results["secrets_scan"] = _scan_secrets()

    # Build summary
    dep_vulns = len(results["dependency_scan"].get("vulnerabilities", [])) if results["dependency_scan"] else 0
    secret_hits = len(results["secrets_scan"].get("findings", [])) if results["secrets_scan"] else 0

    results["summary"] = {
        "vulnerable_packages": dep_vulns,
        "secret_exposures": secret_hits,
        "overall_status": "CRITICAL" if (dep_vulns + secret_hits) > 0 else "CLEAN",
        "recommendation": _get_recommendation(dep_vulns, secret_hits)
    }

    return results


def _scan_dependencies() -> dict:
    """Run pip-audit against installed packages."""
    try:
        result = subprocess.run(
            ["pip-audit", "--format", "json", "--progress-spinner", "off"],
            capture_output=True,
            text=True,
            timeout=120
        )

        # pip-audit returns exit code 1 if vulnerabilities found — that's fine
        output = result.stdout.strip()
        if not output:
            return {"status": "error", "message": "pip-audit returned no output", "vulnerabilities": []}

        data = json.loads(output)
        vulnerabilities = []

        for dep in data.get("dependencies", []):
            for vuln in dep.get("vulns", []):
                vulnerabilities.append({
                    "package": dep.get("name"),
                    "installed_version": dep.get("version"),
                    "vulnerability_id": vuln.get("id"),
                    "description": vuln.get("description", "")[:200],
                    "fix_versions": vuln.get("fix_versions", []),
                    "severity": _estimate_severity(vuln.get("id", ""))
                })

        return {
            "status": "complete",
            "packages_scanned": len(data.get("dependencies", [])),
            "vulnerable_count": len(vulnerabilities),
            "vulnerabilities": vulnerabilities
        }

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "pip-audit timed out after 120 seconds", "vulnerabilities": []}
    except FileNotFoundError:
        return {"status": "error", "message": "pip-audit not installed. Run: pip install pip-audit", "vulnerabilities": []}
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Could not parse pip-audit output: {e}", "vulnerabilities": []}
    except Exception as e:
        return {"status": "error", "message": str(e), "vulnerabilities": []}


def _scan_secrets() -> dict:
    """Scan Python files for hardcoded secrets."""
    # Patterns that look like hardcoded secrets
    secret_patterns = [
        (r'sk-[a-zA-Z0-9]{32,}', "OpenAI API key"),
        (r'sk-proj-[a-zA-Z0-9_\-]{32,}', "OpenAI project key"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub personal access token"),
        (r'xoxb-[0-9]+-[a-zA-Z0-9]+', "Slack bot token"),
        (r'AKIA[0-9A-Z]{16}', "AWS access key"),
        (r'password\s*=\s*["\'][^"\']{6,}["\']', "Hardcoded password"),
        (r'api_key\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded API key"),
        (r'secret\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded secret"),
        (r'Bearer\s+[a-zA-Z0-9_\-\.]{20,}', "Bearer token"),
    ]

    # Files to skip — these legitimately reference secret variable names
    skip_patterns = ["mcp_server.py", ".env", "__pycache__", ".git", "node_modules"]

    app_dir = BASE_DIR
    findings = []

    try:
        python_files = list(app_dir.rglob("*.py")) + list(app_dir.rglob("*.yml")) + list(app_dir.rglob("*.yaml"))

        for filepath in python_files:
            # Skip certain files
            if any(skip in str(filepath) for skip in skip_patterns):
                continue

            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                for line_num, line in enumerate(lines, 1):
                    # Skip lines that use environment variables — these are safe
                    if "os.environ" in line or "os.getenv" in line or "${" in line or ".env" in line.lower():
                        continue
                    # Skip comment lines
                    if line.strip().startswith("#"):
                        continue

                    for pattern, secret_type in secret_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append({
                                "file": str(filepath.relative_to(app_dir)),
                                "line": line_num,
                                "type": secret_type,
                                "severity": "HIGH",
                                "recommendation": "Move to .env file and load with python-dotenv"
                            })
                            break  # One finding per line

            except Exception:
                continue

        return {
            "status": "complete",
            "files_scanned": len(python_files),
            "findings_count": len(findings),
            "findings": findings
        }

    except Exception as e:
        return {"status": "error", "message": str(e), "findings": []}


def _estimate_severity(vuln_id: str) -> str:
    """Estimate severity from vulnerability ID prefix."""
    vuln_id = vuln_id.upper()
    if "CRITICAL" in vuln_id:
        return "CRITICAL"
    if vuln_id.startswith("CVE"):
        return "HIGH"  # Conservative — treat all CVEs as high
    if "PYSEC" in vuln_id:
        return "MEDIUM"
    return "UNKNOWN"


def _get_recommendation(dep_vulns: int, secret_hits: int) -> str:
    if dep_vulns == 0 and secret_hits == 0:
        return "No issues found. Keep dependencies updated regularly."
    parts = []
    if dep_vulns > 0:
        parts.append(f"Update {dep_vulns} vulnerable package(s) immediately.")
    if secret_hits > 0:
        parts.append(f"Move {secret_hits} hardcoded secret(s) to .env file.")
    return " ".join(parts)


# ── TOOL 9: Get upgrade recommendations ───────────────────────────────────────
@mcp.tool()
def get_upgrade_recommendations() -> dict:
    """
    Check all installed packages and recommend which ones to upgrade.
    Shows current version vs latest available version.
    Useful for keeping Abhi-Nexus dependencies fresh and secure.
    """
    try:
        result = subprocess.run(
            ["pip", "list", "--outdated", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return {"status": "error", "message": result.stderr}

        outdated = json.loads(result.stdout)

        # Flag security-critical packages
        security_critical = {"openai", "fastapi", "uvicorn", "pydantic", "cryptography",
                              "python-jose", "passlib", "bcrypt", "requests", "httpx"}

        packages = []
        for pkg in outdated:
            name = pkg.get("name", "").lower()
            packages.append({
                "package": pkg.get("name"),
                "current": pkg.get("version"),
                "latest": pkg.get("latest_version"),
                "priority": "HIGH — security critical" if name in security_critical else "NORMAL",
                "upgrade_command": f"pip install {pkg.get('name')}=={pkg.get('latest_version')}"
            })

        # Sort — security critical first
        packages.sort(key=lambda x: 0 if "HIGH" in x["priority"] else 1)

        return {
            "status": "complete",
            "total_outdated": len(packages),
            "security_critical_outdated": sum(1 for p in packages if "HIGH" in p["priority"]),
            "packages": packages,
            "checked_at": datetime.now().isoformat()
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Starting Abhi-Nexus MCP Server...")
    print(f"Data directory: {DATA_DIR}")
    print("Tools exposed: trigger_pipeline, get_articles, get_top_articles,")
    print("               get_pipeline_status, get_settings, update_setting,")
    print("               get_raw_articles")
    print()
    mcp.run(transport="sse")