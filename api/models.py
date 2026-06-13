"""
api/models.py
─────────────────────────────────────────────
Pydantic models — data shapes for all endpoints.
"""

from pydantic import BaseModel
from typing   import Optional


# ── Request models ─────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class RunPipelineRequest(BaseModel):
    send_email: bool = False


class TTSRequest(BaseModel):
    text: str
    lang: str = "en"


# ── Response models ────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    username:     str


class ArticleModel(BaseModel):
    id:             str
    title:          str
    url:            str
    source:         str
    category:       str
    published_at:   str
    summary:        Optional[str] = ""
    ai_summary:     Optional[str] = ""
    hindi_summary:  Optional[str] = ""
    score:          int = 0
    rank:           int = 0
    tags:           list[str] = []
    is_hot:         bool = False
    image_url:      Optional[str] = ""
    reason:         Optional[str] = ""


class ArticlesResponse(BaseModel):
    articles:   list[ArticleModel]
    total:      int
    updated_at: Optional[str] = None


class StatusResponse(BaseModel):
    status:         str
    articles_count: int
    started_at:     Optional[str] = None
    completed_at:   Optional[str] = None
    errors:         list[dict] = []
    current_step:   Optional[str] = None


class MessageResponse(BaseModel):
    message: str
    status:  Optional[str] = None
