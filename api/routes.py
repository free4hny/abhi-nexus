"""
api/routes.py
─────────────────────────────────────────────
All API endpoints.
"""

import json
import os
import threading
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from openai import OpenAI

from api.auth   import (authenticate_user, create_token,
                         get_current_user, require_admin)
from api.models import (LoginRequest, TokenResponse,
                         ArticlesResponse, ArticleModel,
                         StatusResponse, MessageResponse,
                         RunPipelineRequest, TTSRequest)
import settings as settings_store

log        = logging.getLogger("Routes")
router     = APIRouter()
DATA_FILE  = "data/ranked_articles.json"

# shared pipeline state
from master_agent import MasterAgent
_master_agent  = MasterAgent()
_pipeline_lock = threading.Lock()


# ── Helper ─────────────────────────────────────

def _load_data() -> dict:
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"articles": [], "updated_at": None}


# ── Auth ───────────────────────────────────────

@router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401,
                            detail="Incorrect username or password")
    token = create_token(user["username"], user["role"])
    log.info(f"Login: {user['username']} ({user['role']})")
    return TokenResponse(
        access_token=token,
        role=user["role"],
        username=user["username"],
    )


# ── Articles ───────────────────────────────────

@router.get("/articles", response_model=ArticlesResponse)
def get_articles(
    category: str  = Query(None),
    limit:    int  = Query(50),
    current_user: dict = Depends(get_current_user),
):
    data     = _load_data()
    articles = data.get("articles", [])
    if category:
        articles = [
            a for a in articles
            if a.get("category", "").lower() == category.lower()
        ]
    return ArticlesResponse(
        articles=articles[:limit],
        total=len(articles),
        updated_at=data.get("updated_at"),
    )


@router.get("/articles/hot", response_model=list[ArticleModel])
def get_hot(current_user: dict = Depends(get_current_user)):
    data = _load_data()
    return [a for a in data.get("articles", [])
            if a.get("is_hot")][:5]


@router.get("/articles/categories")
def get_categories(current_user: dict = Depends(get_current_user)):
    data = _load_data()
    cats = sorted(set(
        a.get("category", "General")
        for a in data.get("articles", [])
    ))
    return {"categories": cats}



@router.get("/public/articles")
def get_public_articles():
    """
    Public endpoint — no auth required.
    Returns top 20 articles for public display.
    Read only. No admin functions exposed.
    """
    data     = _load_data()
    articles = data.get("articles", [])[:20]
    return {
        "articles":   articles,
        "updated_at": data.get("updated_at"),
        "total":      len(articles),
    }

# ── Status ─────────────────────────────────────

@router.get("/status", response_model=StatusResponse)
def get_status(current_user: dict = Depends(get_current_user)):
    return StatusResponse(**_master_agent.state)


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


# ── Pipeline ───────────────────────────────────

@router.post("/pipeline/run", response_model=MessageResponse)
def run_pipeline(
    request:      RunPipelineRequest = RunPipelineRequest(),
    current_user: dict = Depends(require_admin),
):
    if not _pipeline_lock.acquire(blocking=False):
        return MessageResponse(message="Pipeline already running",
                               status="running")

    def _run():
        try:
            _master_agent.run()
        finally:
            _pipeline_lock.release()

    thread = threading.Thread(target=_run)
    thread.daemon = True
    thread.start()
    log.info(f"Pipeline triggered by {current_user['username']}")
    return MessageResponse(message="Pipeline started",
                           status="running")


# ── TTS ────────────────────────────────────────

@router.post("/tts")
def generate_tts(
    request:      TTSRequest,
    current_user: dict = Depends(get_current_user),
):
    text = request.text.strip()[:1000]
    lang = request.lang

    if not text:
        raise HTTPException(status_code=400,
                            detail="No text provided")
    try:
        client = OpenAI()
        voice  = "shimmer" if lang == "hi" else "alloy"
        audio  = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="mp3",
            speed=0.95,
        )
        return Response(
            content=audio.read(),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache"},
        )
    except Exception as e:
        log.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Settings (admin only) ──────────────────────

@router.get("/settings")
def get_settings(current_user: dict = Depends(require_admin)):
    return settings_store.load()


@router.post("/settings")
def save_settings(
    req:          Request,
    body:         dict,
    current_user: dict = Depends(require_admin),
):
    cfg = settings_store.load()
    cfg.update(body)
    settings_store.save(cfg)

    # reschedule immediately — no restart needed
    reschedule = getattr(req.app.state, "reschedule", None)
    if reschedule:
        reschedule(cfg)

    log.info(f"Settings updated by {current_user['username']}")
    return {"message": "Settings saved", "settings": cfg}


# ── Email (admin only) ─────────────────────────

@router.post("/email/test")
def send_test_email(
    body:         dict,
    current_user: dict = Depends(require_admin),
):
    from agents.email_agent import send_digest

    recipients = body.get("recipients", [])
    if not recipients:
        cfg        = settings_store.load()
        recipients = cfg.get("email_recipients", [])

    if not recipients:
        raise HTTPException(status_code=400,
                            detail="No recipients configured")

    ok, msg = send_digest(recipients=recipients, test_mode=True)
    if ok:
        return {"message": msg, "success": True}
    raise HTTPException(status_code=500, detail=msg)


# ── Scheduler status (admin only) ──────────────

@router.get("/scheduler/status")
def scheduler_status(
    req:          Request,
    current_user: dict = Depends(require_admin),
):
    scheduler = getattr(req.app.state, "scheduler", None)
    if not scheduler:
        return {"jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id":       job.id,
            "next_run": str(job.next_run_time),
            "trigger":  str(job.trigger),
        })
    return {"jobs": jobs}


@router.post("/public/tts")
def public_tts(request: TTSRequest):
    """
    Public TTS — no auth required.
    Rate limited by OpenAI key cost only.
    """
    text = request.text.strip()[:500]  # shorter limit for public
    lang = request.lang
    if not text:
        raise HTTPException(status_code=400,
                            detail="No text provided")
    try:
        client = OpenAI()
        voice  = "shimmer" if lang == "hi" else "alloy"
        audio  = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            response_format="mp3",
            speed=0.95,
        )
        return Response(
            content=audio.read(),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
