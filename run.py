#============== FIRST PHASE TESTS ==============

# # run.py
# # ─────────────────────────────────────────────
# # Phase 1 test runner
# #
# # This file is our test harness. We will update
# # it at the end of every phase to test the new
# # functionality we just built.
# #
# # Right now it tests only the fetch agent.
# # ─────────────────────────────────────────────

# import json
# import os
# from agents.fetch_agent import fetch_all

# def test_fetch_agent():
#     print("\n" + "="*50)
#     print("PHASE 1 TEST — Fetch Agent")
#     print("="*50 + "\n")

#     # ── Run the agent ──────────────────────────
#     print("Running fetch agent...")
#     articles = fetch_all()

#     # ── Basic checks ───────────────────────────
#     print(f"\n{'─'*50}")
#     print(f"Total articles fetched : {len(articles)}")
#     print(f"{'─'*50}")

#     if len(articles) == 0:
#         print("FAIL — no articles returned")
#         return

#     # ── Check structure of first article ───────
#     print("\nChecking article structure...")
#     first = articles[0]
#     required_fields = [
#         "id", "url", "title", "summary",
#         "source", "category", "published_at",
#         "score", "rank", "tags", "ai_summary", "is_hot"
#     ]
#     all_good = True
#     for field in required_fields:
#         if field in first:
#             print(f"  ✓ {field}")
#         else:
#             print(f"  ✗ {field} MISSING")
#             all_good = False

#     # ── Show first 3 articles ───────────────────
#     print(f"\n{'─'*50}")
#     print("First 3 articles:\n")
#     for i, article in enumerate(articles[:3], 1):
#         print(f"  [{i}] {article['title'][:70]}")
#         print(f"       Source   : {article['source']}")
#         print(f"       Category : {article['category']}")
#         print(f"       ID       : {article['id']}")
#         print(f"       Date     : {article['published_at'][:10]}")
#         print()

#     # ── Check deduplication worked ──────────────
#     ids = [a["id"] for a in articles]
#     unique_ids = set(ids)
#     print(f"{'─'*50}")
#     print(f"Dedup check : {len(ids)} total, {len(unique_ids)} unique")
#     if len(ids) == len(unique_ids):
#         print("✓ No duplicates found")
#     else:
#         print(f"✗ Found {len(ids) - len(unique_ids)} duplicates")

#     # ── Show breakdown by source ────────────────
#     print(f"\n{'─'*50}")
#     print("Articles per source:\n")
#     from collections import Counter
#     source_counts = Counter(a["source"] for a in articles)
#     for source, count in sorted(source_counts.items()):
#         bar = "█" * count
#         print(f"  {source:<25} {bar} ({count})")

#     # ── Save raw output to file ─────────────────
#     os.makedirs("data", exist_ok=True)
#     with open("data/raw_articles.json", "w") as f:
#         json.dump(articles, f, indent=2, default=str)
#     print(f"\n{'─'*50}")
#     print(f"✓ Saved to data/raw_articles.json")

#     # ── Final result ────────────────────────────
#     print(f"\n{'─'*50}")
#     if all_good and len(articles) > 0:
#         print("PHASE 1 RESULT — PASS")
#         print("Fetch agent is working correctly.")
#         print("Context is ready for Agent 2.")
#     else:
#         print("PHASE 1 RESULT — FAIL")
#         print("Fix the errors above before moving to Phase 2.")
#     print("="*50 + "\n")


# if __name__ == "__main__":
#     test_fetch_agent()

#============== SECOND PHASE TESTS ==============

# run.py
# ─────────────────────────────────────────────
# Phase 2 test runner — Master Agent
# ─────────────────────────────────────────────

# import json
# from master_agent import MasterAgent

# def test_master_agent():
#     print("\n" + "="*50)
#     print("PHASE 2 TEST — Master Agent")
#     print("="*50 + "\n")

#     # create and run the master agent
#     agent = MasterAgent()
#     state = agent.run()

#     # check final state
#     print(f"\n{'─'*50}")
#     print("Final state:\n")
#     print(f"  Status        : {state['status']}")
#     print(f"  Articles      : {state['articles_count']}")
#     print(f"  Started at    : {state['started_at']}")
#     print(f"  Completed at  : {state['completed_at']}")
#     print(f"  Errors        : {len(state['errors'])}")

#     if state["errors"]:
#         print("\n  Error details:")
#         for err in state["errors"]:
#             print(f"    [{err['step']}] {err['error']}")

#     # check context was enriched
#     print(f"\n{'─'*50}")
#     print("Checking context enrichment:\n")
#     first = agent.context[0] if agent.context else None
#     if first:
#         print(f"  Title    : {first['title'][:60]}")
#         print(f"  Score    : {first['score']}")
#         print(f"  Rank     : {first['rank']}")
#         print(f"  Is hot   : {first['is_hot']}")
#         print(f"  Tags     : {first['tags']}")

#     # check persistence worked
#     print(f"\n{'─'*50}")
#     try:
#         with open("data/ranked_articles.json") as f:
#             saved = json.load(f)
#         print(f"  ✓ data/ranked_articles.json exists")
#         print(f"  ✓ {len(saved['articles'])} articles saved")
#         print(f"  ✓ updated_at: {saved['updated_at']}")
#     except FileNotFoundError:
#         print("  ✗ data/ranked_articles.json not found")

#     # final result
#     print(f"\n{'─'*50}")
#     if state["status"] == "done":
#         print("PHASE 2 RESULT — PASS")
#         print("Master agent is coordinating correctly.")
#         print("Context flows between agents.")
#         print("Ready for Phase 3 — adding AI brain.")
#     else:
#         print("PHASE 2 RESULT — FAIL")
#         print(f"Status was: {state['status']}")
#     print("="*50 + "\n")


# if __name__ == "__main__":
#     test_master_agent()



#============== THIRD PHASE TESTS ==============

# run.py
# ─────────────────────────────────────────────
# Phase 3 test runner — AI Ranking
# ─────────────────────────────────────────────

import json
from master_agent import MasterAgent

def test_rank_agent():
    print("\n" + "="*50)
    print("PHASE 3 TEST — AI Rank Agent")
    print("="*50 + "\n")

    agent = MasterAgent()
    state = agent.run()

    print(f"\n{'─'*50}")
    print("Pipeline state:\n")
    print(f"  Status   : {state['status']}")
    print(f"  Articles : {state['articles_count']}")
    print(f"  Errors   : {len(state['errors'])}")

    if state["errors"]:
        for err in state["errors"]:
            print(f"  [{err['step']}] {err['error']}")

    # show top 5 hot articles with real scores
    print(f"\n{'─'*50}")
    print("Top 5 articles by AI score:\n")
    hot = [a for a in agent.context if a.get("is_hot")]
    for article in hot:
        print(f"  #{article['rank']} [{article['score']}/100] "
              f"{article['title'][:55]}")
        print(f"     Tags    : {', '.join(article['tags'])}")
        print(f"     Summary : {article['ai_summary'][:100]}...")
        print(f"     Reason  : {article.get('reason','')[:80]}")
        print()

    # verify scores are different — not all 50
    print(f"{'─'*50}")
    scores = [a["score"] for a in agent.context]
    unique_scores = set(scores)
    print(f"Score variety check:")
    print(f"  Unique scores  : {len(unique_scores)}")
    print(f"  Highest score  : {max(scores)}")
    print(f"  Lowest score   : {min(scores)}")
    print(f"  Average score  : {sum(scores)//len(scores)}")

    if len(unique_scores) > 5:
        print("  ✓ Scores are varied — AI ranking is working")
    else:
        print("  ✗ Scores look too uniform — check GPT response")

    # final result
    print(f"\n{'─'*50}")
    if state["status"] == "done" and len(unique_scores) > 5:
        print("PHASE 3 RESULT — PASS")
        print("AI brain is working.")
        print("Articles have real importance scores.")
        print("Context is fully enriched.")
        print("Ready for Phase 4 — FastAPI backend.")
    else:
        print("PHASE 3 RESULT — NEEDS ATTENTION")
    print("="*50 + "\n")


if __name__ == "__main__":
    test_rank_agent()