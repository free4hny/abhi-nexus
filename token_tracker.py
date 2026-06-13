"""
token_tracker.py
─────────────────────────────────────────────
Tracks every OpenAI API call — tokens used,
cost, model, timestamp. Saves to data/tokens.json
Readable from the admin panel in real time.
"""

import json
import os
from datetime import datetime, timezone

TOKENS_FILE = "data/tokens.json"

# OpenAI pricing (per 1M tokens) as of 2026
PRICING = {
    "gpt-4o-mini": {
        "prompt":     0.15,   # $0.15 per 1M prompt tokens
        "completion": 0.60,   # $0.60 per 1M completion tokens
    },
    "tts-1": {
        "per_char":   0.000015,  # $0.015 per 1000 chars
    }
}

def _load() -> dict:
    os.makedirs("data", exist_ok=True)
    try:
        with open(TOKENS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"calls": [], "totals": {
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "total_tokens":      0,
            "tts_chars":         0,
            "total_cost_usd":    0.0,
            "call_count":        0,
        }}

def _save(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def log_llm_call(model: str, prompt_tokens: int,
                  completion_tokens: int, purpose: str = ""):
    """Log a GPT API call and update running totals."""
    data = _load()

    pricing  = PRICING.get(model, {"prompt": 0, "completion": 0})
    cost     = (
        (prompt_tokens     / 1_000_000) * pricing["prompt"] +
        (completion_tokens / 1_000_000) * pricing["completion"]
    )

    call = {
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "model":             model,
        "purpose":           purpose,
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens":      prompt_tokens + completion_tokens,
        "cost_usd":          round(cost, 6),
    }

    data["calls"].append(call)

    # keep only last 200 calls
    data["calls"] = data["calls"][-200:]

    # update totals
    t = data["totals"]
    t["prompt_tokens"]     += prompt_tokens
    t["completion_tokens"] += completion_tokens
    t["total_tokens"]      += prompt_tokens + completion_tokens
    t["total_cost_usd"]     = round(t["total_cost_usd"] + cost, 6)
    t["call_count"]        += 1

    _save(data)

def log_tts_call(char_count: int, lang: str = "en"):
    """Log a TTS API call."""
    data  = _load()
    cost  = char_count * PRICING["tts-1"]["per_char"]

    call = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model":     "tts-1",
        "purpose":   f"TTS narration ({lang})",
        "chars":     char_count,
        "cost_usd":  round(cost, 6),
    }

    data["calls"].append(call)
    data["calls"] = data["calls"][-200:]

    t = data["totals"]
    t["tts_chars"]      += char_count
    t["total_cost_usd"]  = round(t["total_cost_usd"] + cost, 6)
    t["call_count"]     += 1

    _save(data)

def get_stats() -> dict:
    """Return full token usage stats."""
    return _load()

def get_today_cost() -> float:
    """Return total cost for today only."""
    data  = _load()
    today = datetime.now(timezone.utc).date().isoformat()
    return round(sum(
        c.get("cost_usd", 0)
        for c in data["calls"]
        if c.get("timestamp", "").startswith(today)
    ), 6)

def get_monthly_cost() -> float:
    """Return total cost for current month."""
    data  = _load()
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return round(sum(
        c.get("cost_usd", 0)
        for c in data["calls"]
        if c.get("timestamp", "").startswith(month)
    ), 6)
