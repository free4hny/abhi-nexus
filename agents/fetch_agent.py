# agents/fetch_agent.py
# ─────────────────────────────────────────────
# Agent 1 — Fetch Agent
#
# JOB       : fetch articles from RSS sources
# INPUT     : list of sources from config.py
# OUTPUT    : list of article dictionaries
#             (this is called the "context")
#
# This agent has NO knowledge of ranking,
# summarizing or email. It only fetches.
# That is what makes it an "agent" — it has
# one job and does it well.
# ─────────────────────────────────────────────

import feedparser
import requests
import hashlib
import time
import logging
from datetime import datetime, timezone
from bs4 import BeautifulSoup

from config import NEWS_SOURCES, ARTICLES_PER_SOURCE

# ── Logging setup ─────────────────────────────
# logging lets us see what the agent is doing
# without using print() everywhere.
# Think of it as a professional print statement
# that includes timestamp and severity level.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("FetchAgent")


# ── Helper functions ──────────────────────────
# These are small utility functions the agent
# uses internally. They are not agents themselves
# — they are just tools the agent uses.

def make_article_id(url: str) -> str:
    """
    Create a unique ID for each article using
    MD5 hash of its URL.

    WHY: two sources might cover the same story.
    Hashing the URL gives us a consistent ID
    we can use to deduplicate later.

    This is exactly how Meta deduplicates events
    in their data pipelines.
    """
    return hashlib.md5(url.encode()).hexdigest()[:12]


def clean_text(raw_html: str) -> str:
    """
    Strip HTML tags from article summaries.

    RSS feeds often include HTML in their
    summary fields. We want plain text only.
    BeautifulSoup parses the HTML and extracts
    just the text content.
    """
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ").strip()
    # collapse multiple spaces into one
    import re; text = re.sub(r"[\u200b-\u200f\ufeff\u200c\u200d]", "", text); return " ".join(text.split())[:500]


def parse_date(entry) -> str:
    """
    Extract published date from a feed entry
    and normalize it to ISO 8601 format in UTC.

    WHY normalize to UTC? Because sources are
    global. A post from India and a post from
    California need a common timezone to sort
    correctly. UTC is that standard.

    This is called "timestamp normalization" —
    a fundamental data engineering concept.
    """
    for field in ("published", "updated", "created"):
        value = getattr(entry, field, None)
        if value:
            try:
                from dateutil import parser as dateparser
                dt = dateparser.parse(value)
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass
    # fallback to current time if no date found
    return datetime.now(timezone.utc).isoformat()


def extract_image(entry) -> str:
    """
    Try to find a thumbnail image for the article.
    RSS feeds store images in different places —
    we check all common locations.
    """
    # check media:thumbnail tag
    media = getattr(entry, "media_thumbnail", None)
    if media and isinstance(media, list):
        return media[0].get("url", "")

    # check enclosures (podcast/image attachments)
    for enc in getattr(entry, "enclosures", []):
        if "image" in enc.get("type", ""):
            return enc.get("url", "")

    # check inside the HTML summary
    summary = getattr(entry, "summary", "")
    if summary:
        soup = BeautifulSoup(summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]

    return ""


# ── Core agent function ───────────────────────

def fetch_from_source(source: dict) -> list[dict]:
    """
    Fetch articles from a single RSS source.

    INPUT  : one source dictionary from config.py
    OUTPUT : list of article dictionaries

    Each article dictionary is the CONTEXT UNIT
    that flows through our entire pipeline.
    Every field we add here is available to
    every downstream agent.
    """
    articles = []

    try:
        log.info(f"Fetching → {source['name']}")
        feed = feedparser.parse(source["url"])

        # feedparser.parse never raises exceptions —
        # it returns an empty feed if something fails.
        # We check the entries list instead.
        if not feed.entries:
            log.warning(f"No entries found for {source['name']}")
            return []

        for entry in feed.entries[:ARTICLES_PER_SOURCE]:
            url   = getattr(entry, "link", "")
            title = getattr(entry, "title", "").strip()

            # skip articles with no title or URL
            # — they are useless to downstream agents
            if not title or not url:
                continue

            # build the article context dictionary
            # this is the core data unit of our pipeline
            article = {
                # identity
                "id":           make_article_id(url),
                "url":          url,

                # content
                "title":        title,
                "summary":      clean_text(
                                    getattr(entry, "summary", "") or
                                    getattr(entry, "description", "")
                                ),
                "image_url":    extract_image(entry),

                # metadata
                "source":       source["name"],
                "category":     source["category"],
                "published_at": parse_date(entry),

                # these fields will be filled by
                # downstream agents — we set defaults
                # here so the structure is consistent
                "score":        0,
                "rank":         0,
                "tags":         [],
                "ai_summary":   "",
                "is_hot":       False,
            }
            articles.append(article)

    except Exception as e:
        # IMPORTANT: we catch ALL exceptions here
        # and log them instead of crashing.
        # WHY: if one source fails, we still want
        # articles from the other 7 sources.
        # This is called "graceful degradation" —
        # a core principle in production systems.
        log.error(f"Failed to fetch {source['name']}: {e}")

    return articles


def fetch_all(sources: list[dict] = None) -> list[dict]:
    """
    Fetch articles from ALL sources.
    This is the main entry point for this agent.

    INPUT  : list of sources (defaults to config)
    OUTPUT : deduplicated list of all articles

    This function is what the master agent will call.
    """
    if sources is None:
        sources = NEWS_SOURCES

    log.info(f"Starting fetch from {len(sources)} sources...")
    all_articles = []

    for source in sources:
        articles = fetch_from_source(source)
        all_articles.extend(articles)

        # polite delay between requests
        # WHY: hammering servers too fast can get
        # your IP blocked. 0.5s is respectful.
        # At Meta scale this becomes rate limiting
        # and backpressure — same concept.
        time.sleep(0.5)

    # ── Deduplication ─────────────────────────
    # Two sources might link to the same article.
    # We use the article ID (MD5 of URL) to detect
    # and remove duplicates.
    seen_ids = set()
    unique_articles = []

    for article in all_articles:
        if article["id"] not in seen_ids:
            seen_ids.add(article["id"])
            unique_articles.append(article)

    log.info(
        f"Done. Fetched {len(all_articles)} total, "
        f"{len(unique_articles)} unique articles."
    )
    return unique_articles