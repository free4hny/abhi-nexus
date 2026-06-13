# # agents/rank_agent.py
# # ─────────────────────────────────────────────
# # Agent 2 — Rank Agent
# #
# # JOB    : score and rank articles by importance
# # INPUT  : list of articles from fetch agent
# # OUTPUT : same list with score, rank, tags filled
# #
# # Phase 2 : this is a STUB — it returns articles
# #           unchanged so the master agent has
# #           something to call and test with.
# #
# # Phase 3 : we replace the stub with real
# #           GPT-4o-mini ranking logic.
# # ─────────────────────────────────────────────

# import logging

# log = logging.getLogger("RankAgent")


# def rank_all(articles: list[dict]) -> list[dict]:
#     """
#     Rank articles by importance score.

#     RIGHT NOW: stub — assigns a placeholder
#     score of 50 to every article so the pipeline
#     can flow end to end.

#     Phase 3 will replace this with real GPT-4o-mini
#     scoring that gives each article a proper 1-100
#     score based on importance, novelty and impact.
#     """
#     log.info(f"Ranking {len(articles)} articles (stub)")

#     for i, article in enumerate(articles):
#         # placeholder score — every article gets 50
#         # Phase 3 replaces this with real AI scoring
#         article["score"]  = 50
#         article["rank"]   = i + 1
#         article["tags"]   = []
#         article["is_hot"] = i < 5   # top 5 are "hot"

#     log.info(f"Ranking complete. {len(articles)} articles ranked.")
#     return articles




# agents/rank_agent.py
# ─────────────────────────────────────────────
# Agent 2 — Rank Agent (Phase 3 — real AI)
#
# JOB    : score and rank articles by importance
# INPUT  : list of articles from fetch agent
# OUTPUT : same list with score, rank, tags,
#          ai_summary, is_hot filled
#
# HOW    : sends articles to GPT-4o-mini in
#          batches of 10. asks it to score each
#          article 1-100 and return structured
#          JSON we can parse and store.
# ─────────────────────────────────────────────

import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("RankAgent")

# how many articles to send per API call
# 10 is the sweet spot — not too many tokens,
# not too many API calls
BATCH_SIZE = 10

# the system prompt is the agent's brain —
# it tells GPT-4o-mini exactly what job it has,
# what the scoring rules are, and what format
# to return results in.
# this is the most important part of the agent.
SYSTEM_PROMPT = """
You are a senior tech journalist and editor at a
major technology publication.

Your job is to read article titles and summaries,
then score each one by importance to a tech-savvy
reader who cares about AI, engineering, security,
and the future of technology.

SCORING RULES:
  90-100 : world-changing news. major AI breakthroughs,
            critical security vulnerabilities, landmark
            product launches that change industries.
  70-89  : very important. significant product releases,
            important research papers, major company news.
  50-69  : interesting. useful tools, good tutorials,
            notable industry developments.
  30-49  : minor. incremental updates, opinion pieces,
            routine announcements.
  1-29   : low value. clickbait, very niche content,
            outdated information.

OUTPUT FORMAT:
Return a JSON array. One object per article.
Each object must have exactly these fields:
  - index        : the article number I gave you (integer)
  - score        : your importance score 1-100 (integer)
  - tags         : list of 3-5 keyword tags (array of strings)
  - ai_summary   : 2-3 sentence plain English summary.
                   no jargon. a smart 15-year-old should
                   understand it. (string)
  - hindi_summary: same summary in simple Hindi. use simple
                   Hindi words. tech terms like AI, software,
                   security can stay in English. make it
                   conversational like you are explaining to
                   a friend. (string)
  - reason       : one sentence explaining your score (string)

RULES:
  - return ONLY the JSON array. no explanation before or after.
  - no markdown code blocks. raw JSON only.
  - every article in the input must appear in the output.
  - ai_summary must be original — do not copy the original text.
  - hindi_summary must be simple — avoid formal Sanskrit words.
"""


# ── Helper functions ───────────────────────────

def _build_user_message(batch: list[dict], offset: int) -> str:
    """
    Build the user message for one batch of articles.

    We number each article starting from 1 so GPT
    can reference them clearly in its response.
    The offset handles batches after the first one
    so numbering is consistent across batches.

    Example output:
    Article 1:
    Title: OpenAI releases GPT-5
    Summary: OpenAI today announced...

    Article 2:
    Title: AWS launches new service
    Summary: Amazon Web Services...
    """
    lines = []
    for i, article in enumerate(batch):
        number = offset + i + 1
        lines.append(f"Article {number}:")
        lines.append(f"Title: {article['title']}")

        # send up to 300 chars of summary
        # more than that wastes tokens without
        # adding meaningful information
        summary = article.get("summary", "")[:300]
        if summary:
            lines.append(f"Summary: {summary}")
        lines.append("")   # blank line between articles

    return "\n".join(lines)


def _parse_response(response_text: str, batch: list[dict],
                    offset: int) -> dict:
    """
    Parse GPT's JSON response into a lookup dictionary.

    INPUT  : raw text from GPT (should be JSON)
    OUTPUT : dict mapping article index to ranking data
             {1: {score: 87, tags: [...], ...}, 2: {...}}

    We wrap this in try/except because GPT occasionally
    returns malformed JSON. If parsing fails we return
    an empty dict and the calling code uses fallback values.
    This is defensive programming — never trust external
    API responses blindly.
    """
    try:
        # sometimes GPT wraps response in ```json ... ```
        # even when told not to. strip that if present.
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # remove first line (```json) and last line (```)
            text = "\n".join(lines[1:-1])

        rankings = json.loads(text)

        # convert list to dict keyed by index
        # so we can look up by article number instantly
        return {r["index"]: r for r in rankings}

    except (json.JSONDecodeError, KeyError) as e:
        log.error(f"Failed to parse GPT response: {e}")
        log.error(f"Raw response was: {response_text[:200]}")
        return {}


def _apply_rankings(batch: list[dict], rank_map: dict,
                    offset: int) -> list[dict]:
    for i, article in enumerate(batch):
        number = offset + i + 1
        ranking = rank_map.get(number, {})

        if ranking:
            article["score"]         = int(ranking.get("score", 30))
            article["tags"]          = ranking.get("tags", [])
            article["ai_summary"]    = ranking.get("ai_summary",
                                           article.get("summary", ""))
            article["hindi_summary"] = ranking.get("hindi_summary", "")
            article["reason"]        = ranking.get("reason", "")
        else:
            log.warning(f"No ranking for article {number} — using fallback")
            article["score"]         = 30
            article["tags"]          = []
            article["ai_summary"]    = article.get("summary", "")
            article["hindi_summary"] = ""
            article["reason"]        = "Could not rank"

    return batch


# ── Core agent function ────────────────────────

def rank_all(articles: list[dict]) -> list[dict]:
    """
    Rank all articles using GPT-4o-mini.

    This is the main entry point — what the
    master agent calls.

    FLOW:
    1. split articles into batches of 10
    2. for each batch:
       a. build user message
       b. call GPT-4o-mini
       c. parse JSON response
       d. apply rankings to articles
    3. sort all articles by score descending
    4. assign final rank numbers
    5. mark top 5 as is_hot
    6. return enriched articles
    """
    if not articles:
        log.warning("No articles to rank")
        return articles

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    log.info(f"Ranking {len(articles)} articles "
             f"in batches of {BATCH_SIZE}...")

    # process in batches
    for batch_start in range(0, len(articles), BATCH_SIZE):
        batch = articles[batch_start:batch_start + BATCH_SIZE]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE

        log.info(f"Processing batch {batch_num}/{total_batches} "
                 f"({len(batch)} articles)...")

        try:
            # ── Call GPT-4o-mini ───────────────
            response = client.chat.completions.create(
                model="gpt-4o-mini",

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": _build_user_message(batch, batch_start)
                    }
                ],

                # temperature controls randomness
                # 0.3 = mostly consistent scores
                # 0.0 = fully deterministic
                # 1.0 = very random
                # we want consistent scoring so we use 0.3
                temperature=0.3,

                # max tokens limits response length
                # 1500 is enough for 10 articles in JSON
                max_tokens=6000,
            )

            # extract the text response
            response_text = response.choices[0].message.content

            # ── Parse response ─────────────────
            rank_map = _parse_response(
                response_text, batch, batch_start
            )

            # ── Apply to articles ──────────────
            _apply_rankings(batch, rank_map, batch_start)

            # log token usage so we can track cost
            usage = response.usage
            log.info(
                f"Batch {batch_num} done — "
                f"tokens used: {usage.total_tokens} "
                f"(prompt: {usage.prompt_tokens}, "
                f"completion: {usage.completion_tokens})"
            )

        except Exception as e:
            # if one batch fails, log and continue
            # other batches can still succeed
            log.error(f"Batch {batch_num} failed: {e}")
            # apply fallback scores to this batch
            for article in batch:
                article["score"]      = 30
                article["tags"]       = []
                article["ai_summary"] = article.get("summary", "")

    # ── Sort by score descending ───────────────
    # highest score = most important = rank 1
    articles.sort(key=lambda x: x["score"], reverse=True)

    # ── Assign final rank numbers ──────────────
    for i, article in enumerate(articles):
        article["rank"]   = i + 1
        article["is_hot"] = i < 5   # top 5 are hot

    log.info(
        f"Ranking complete. "
        f"Top article: '{articles[0]['title'][:50]}' "
        f"(score: {articles[0]['score']})"
    )
    return articles