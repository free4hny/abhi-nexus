# master_agent.py
# ─────────────────────────────────────────────
# Master Agent — the coordinator
#
# This is the brain of the multi-agent system.
# It does NOT do any actual work itself.
# Its only job is to:
#   1. coordinate which agents run
#   2. pass context between them
#   3. handle failures gracefully
#   4. track and report state
#
# Think of it as a project manager —
# it delegates to specialists and makes sure
# everything comes together correctly.
# ─────────────────────────────────────────────

import json
import os
import logging
from datetime import datetime, timezone

from agents.fetch_agent import fetch_all
from agents.rank_agent  import rank_all

log = logging.getLogger("MasterAgent")


class MasterAgent:
    """
    The master agent coordinates all sub-agents.

    WHY a class and not just a function?
    Because the master agent needs to maintain
    STATE across multiple steps. A class lets us
    store that state on self — clean and explicit.

    A function cannot hold state between calls
    without ugly global variables.
    """

    def __init__(self):
        # State is the master agent's memory.
        # It tracks everything that is happening
        # so we can monitor, debug, and recover.
        self.state = {
            "status":         "idle",
            "current_step":   None,
            "articles_count": 0,
            "errors":         [],
            "started_at":     None,
            "completed_at":   None,
        }

        # Context is the data that flows between
        # agents. It starts empty and gets enriched
        # by each agent that runs.
        self.context = []

    # ── State management ───────────────────────

    def _set_status(self, status: str, step: str = None):
        """
        Update the master agent's status.
        Always goes through this method — never
        set self.state directly — so we always
        log status changes automatically.
        """
        self.state["status"]       = status
        self.state["current_step"] = step
        if step:
            log.info(f"Status: {status.upper()} — {step}")
        else:
            log.info(f"Status: {status.upper()}")

    def _record_error(self, step: str, error: Exception):
        """
        Record an error without crashing.
        The master agent logs errors and continues
        where possible — same as how Dataswarm
        handles operator failures at Meta.
        """
        error_record = {
            "step":    step,
            "error":   str(error),
            "time":    datetime.now(timezone.utc).isoformat(),
        }
        self.state["errors"].append(error_record)
        log.error(f"Error in {step}: {error}")

    # ── Agent coordination ─────────────────────

    def _run_fetch(self) -> bool:
        """
        Step 1: run the fetch agent.

        Returns True if successful, False if failed.
        The master agent uses this return value
        to decide whether to continue or abort.
        """
        self._set_status("running", "fetch")
        try:
            # call the fetch agent
            # it returns the raw context
            articles = fetch_all()

            # validation — did we get anything?
            # if not, there is no point continuing
            if not articles:
                log.warning("Fetch returned 0 articles — aborting pipeline")
                self._record_error("fetch", Exception("0 articles returned"))
                return False

            # store context for next agent
            self.context = articles
            self.state["articles_count"] = len(articles)
            log.info(f"Fetch complete — {len(articles)} articles in context")
            return True

        except Exception as e:
            self._record_error("fetch", e)
            return False

    def _run_rank(self) -> bool:
        """
        Step 2: run the rank agent.

        Receives context from fetch agent,
        returns enriched context with scores.
        """
        self._set_status("running", "rank")
        try:
            # pass current context to rank agent
            # it enriches each article with:
            # score, rank, tags, is_hot
            ranked_articles = rank_all(self.context)

            # validation
            if not ranked_articles:
                self._record_error("rank", Exception("Rank returned empty"))
                return False

            # update context with ranked articles
            self.context = ranked_articles
            log.info(f"Rank complete — top article: {self.context[0]['title'][:50]}")
            return True

        except Exception as e:
            self._record_error("rank", e)
            # IMPORTANT: rank failure is not fatal
            # we can still serve unranked articles
            # this is graceful degradation
            log.warning("Rank failed — continuing with unranked articles")
            return True     # return True to continue pipeline

    def _save_context(self):
        """
        Save the final enriched context to disk.

        WHY save to disk?
        - The Streamlit UI reads from this file
        - If the server restarts, data is not lost
        - Other processes can read the data
        This is called "persistence" — a core
        data engineering concept.
        """
        os.makedirs("data", exist_ok=True)
        output = {
            "articles":   self.context,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "run_state":  self.state,
        }
        with open("data/ranked_articles.json", "w") as f:
            json.dump(output, f, indent=2, default=str)
        log.info("Context saved to data/ranked_articles.json")

    # ── Main run loop ──────────────────────────

    def run(self) -> dict:
        """
        The main coordination loop.

        This is the method the outside world calls.
        It runs all agents in sequence, passing
        context between them, and returns the
        final state so the caller knows what happened.

        RETURN VALUE: the final state dictionary
        so the caller can check success/failure.
        """
        log.info("="*40)
        log.info("Master Agent starting run")
        log.info("="*40)

        self.state["started_at"] = datetime.now(timezone.utc).isoformat()
        self.state["errors"]     = []   # reset errors for new run
        self.context             = []   # reset context for new run

        # ── Step 1: Fetch ──────────────────────
        success = self._run_fetch()
        if not success:
            # fetch failure IS fatal — no articles
            # means nothing else can run
            self._set_status("error")
            self.state["completed_at"] = datetime.now(timezone.utc).isoformat()
            return self.state

        # ── Step 2: Rank ───────────────────────
        self._run_rank()
        # note: we do not check success here
        # because rank failure is non-fatal

        # ── Save context ───────────────────────
        self._save_context()

        # ── Done ───────────────────────────────
        self._set_status("done")
        self.state["completed_at"] = datetime.now(timezone.utc).isoformat()

        log.info("="*40)
        log.info(f"Run complete — {self.state['articles_count']} articles processed")
        if self.state["errors"]:
            log.warning(f"{len(self.state['errors'])} error(s) recorded")
        log.info("="*40)

        return self.state