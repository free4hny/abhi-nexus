"""
api_server.py
─────────────────────────────────────────────
FastAPI server + APScheduler.

Scheduler reads settings from data/settings.json
on every tick — so UI changes take effect
immediately without restarting the server.
"""

import logging
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron         import CronTrigger
from apscheduler.triggers.interval     import IntervalTrigger

from api.routes   import router
import settings   as settings_store
from master_agent import MasterAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("Server")

# ── FastAPI app ────────────────────────────────
app = FastAPI(
    title="Abhi-Nexus API",
    description="Multi-agent news intelligence system",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "name":    "Abhi-Nexus API",
        "version": "2.0.0",
        "docs":    "/docs",
    }


# ── Shared state ───────────────────────────────
_master    = MasterAgent()
_lock      = threading.Lock()
_scheduler = BackgroundScheduler(timezone="America/New_York")


# ── Scheduled jobs ─────────────────────────────

def _run_pipeline_job():
    """Runs the pipeline on schedule."""
    cfg = settings_store.load()
    if not cfg.get("scheduler_enabled", True):
        log.info("Scheduler disabled — skipping")
        return
    if not _lock.acquire(blocking=False):
        log.warning("Pipeline already running — skipping")
        return
    try:
        log.info("⏰ Scheduled pipeline run starting...")
        _master.run()
        log.info("⏰ Scheduled pipeline run complete")
    finally:
        _lock.release()


def _send_email_job():
    """Sends the daily email digest on schedule."""
    cfg = settings_store.load()
    if not cfg.get("email_enabled", True):
        log.info("Email disabled — skipping")
        return
    recipients = cfg.get("email_recipients", [])
    if not recipients:
        log.warning("No email recipients configured")
        return
    from agents.email_agent import send_digest
    ok, msg = send_digest(recipients)
    log.info(f"Email job: {msg}")


def _reschedule(cfg: dict):
    """
    Update scheduler jobs based on current settings.
    Called when admin saves settings from the UI.
    Changes take effect immediately — no restart needed.
    """
    for job_id in ["pipeline_refresh", "email_digest"]:
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)

    interval = cfg.get("refresh_interval_minutes", 120)
    _scheduler.add_job(
        _run_pipeline_job,
        IntervalTrigger(minutes=interval),
        id="pipeline_refresh",
        max_instances=1,
        replace_existing=True,
    )
    log.info(f"Pipeline scheduled every {interval} minutes")

    email_time   = cfg.get("email_time", "21:00")
    hour, minute = map(int, email_time.split(":"))
    _scheduler.add_job(
        _send_email_job,
        CronTrigger(
            hour=hour, minute=minute,
            timezone="America/New_York"
        ),
        id="email_digest",
        max_instances=1,
        replace_existing=True,
    )
    log.info(f"Email digest scheduled at {email_time} EST")


# expose to routes via app.state
app.state.reschedule    = _reschedule
app.state.master        = _master
app.state.pipeline_lock = _lock
app.state.scheduler     = _scheduler


# ── Lifecycle ──────────────────────────────────

@app.on_event("startup")
def startup():
    cfg = settings_store.load()
    _scheduler.start()
    _reschedule(cfg)
    log.info("✅ Server started — scheduler running")


@app.on_event("shutdown")
def shutdown():
    _scheduler.shutdown()
    log.info("Scheduler stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
