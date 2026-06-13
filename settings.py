# settings.py
# ─────────────────────────────────────────────
# Persistent settings store
#
# Reads and writes settings to data/settings.json
# This is how admin changes from the UI survive
# server restarts — settings live on disk not
# in memory.
# ─────────────────────────────────────────────

import json
import os
import logging

log = logging.getLogger("Settings")
SETTINGS_FILE = "data/settings.json"

DEFAULTS = {
    # scheduler
    "scheduler_enabled":       True,
    "refresh_interval_minutes": 120,
    "email_time":              "21:00",   # 9 PM
    "email_enabled":           True,

    # email
    "email_recipients":        [],
    "email_sender":            "",

    # meta
    "last_email_sent":         None,
    "next_run_at":             None,
}


def load() -> dict:
    """Load settings from disk. Returns defaults if file missing."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    try:
        with open(SETTINGS_FILE) as f:
            saved = json.load(f)
        # merge with defaults so new keys always exist
        merged = {**DEFAULTS, **saved}
        return merged
    except (FileNotFoundError, json.JSONDecodeError):
        save(DEFAULTS)
        return DEFAULTS.copy()


def save(settings: dict):
    """Save settings to disk."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2, default=str)
    log.info("Settings saved")


def update(key: str, value) -> dict:
    """Update a single setting and save."""
    settings = load()
    settings[key] = value
    save(settings)
    return settings