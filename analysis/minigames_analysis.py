"""
minigames_analysis.py
---------------------
Utility helpers for querying and analysing performance *per mini-game*.

Usage pattern (example):

    from minigames_analysis import (
        get_list_of_minigames,
        get_minigame_attempts,
        analyse_minigame_attempts,
        aggregate_minigame_errors,
        top_errors,
    )

    games = get_list_of_minigames()
    attempts = get_minigame_attempts(game_id=games[0]["Level_ID"])
    summary  = analyse_minigame_attempts(attempts)
    errors   = aggregate_minigame_errors(attempts)
    common   = top_errors(errors["minor"], top_n=5)
"""

import json
import logging
import re
from collections import Counter, defaultdict
from statistics import mean

from sqlalchemy import text

from utils.db import engine  # existing module in your project

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# 🔎  Fetch basic lists
# ────────────────────────────────────────────────────────────────────────────────
def get_list_of_minigames():
    """
    Return every distinct mini-game (Level_ID + Name) found in ima_game_level.
    """
    query = text(
        """
        SELECT Level_ID,
               Game_ID,
               REPLACE(Name, '<br>', ' - ') AS Name
        FROM   IMA_Game_Level
        ORDER  BY Game_ID, Level_ID;
        """
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()
        games = [dict(r._mapping) for r in rows]
        logger.info("Fetched %d minigames", len(games))
        return games
    except Exception as exc:
        logger.error("Failed to fetch minigames: %s", exc)
        return []


# ────────────────────────────────────────────────────────────────────────────────
# 🔎  Attempts & raw rows
# ────────────────────────────────────────────────────────────────────────────────
def get_minigame_attempts(game_id: int):
    """
    Pull every attempt of a given mini-game (level) across all users.

    Returns a list of dicts:
        {
            "Session_ID": …,
            "User_ID": …,
            "Status": "complete" | "fail" | "toplay",
            "Score": 87,
            "Results": '{…JSON…}',   # can be NULL
            "Game_Start": "2025-05-22 02:12:34",
            "Game_End":   "2025-05-22 02:17:41",
        }
    """
    query = text(
        """
        SELECT psgs.Session_ID,
               ps.User_ID,
               psgs.Status,
               psgs.Score,
               psgs.Results,
               psgs.Game_Start,
               psgs.Game_End
        FROM   IMA_Plan_Game              AS pg
        JOIN   IMA_Plan_Session_Game_Status AS psgs
                   ON pg.Plan_Game_ID = psgs.Plan_Game_ID
        JOIN   IMA_Plan_Session           AS ps
                   ON ps.Session_ID = psgs.Session_ID
        WHERE  pg.Level = :game_id;
        """
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(query, {"game_id": game_id}).fetchall()
        attempts = [dict(r._mapping) for r in rows]
        logger.info("Fetched %d attempts for minigame %s", len(attempts), game_id)
        return attempts
    except Exception as exc:
        logger.error("Failed to fetch attempts for game %s: %s", game_id, exc)
        return []


# ────────────────────────────────────────────────────────────────────────────────
# 📊  Summary stats
# ────────────────────────────────────────────────────────────────────────────────
def analyse_minigame_attempts(attempt_rows):
    """
    Produce aggregate statistics for a list of attempt dicts.
    """
    if not attempt_rows:
        return {}

    scores = [row["Score"] for row in attempt_rows if row["Score"] is not None]
    completions = [row for row in attempt_rows if row["Status"] == "complete"]
    fails = [row for row in attempt_rows if row["Status"] == "fail"]

    summary = {
        "total_attempts": len(attempt_rows),
        "unique_users": len({r["User_ID"] for r in attempt_rows}),
        "completed": len(completions),
        "failed": len(fails),
        "completion_rate": (
            round(len(completions) / len(attempt_rows) * 100, 2) if attempt_rows else 0
        ),
        "average_score": round(mean(scores), 2) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "max_score": max(scores) if scores else 0,
    }
    return summary


# ────────────────────────────────────────────────────────────────────────────────
# 🐞  Error aggregation & helpers
# ────────────────────────────────────────────────────────────────────────────────
def aggregate_minigame_errors(attempt_rows):
    """
    Traverse the Results JSON of each attempt and merge all errors into
    combined category lists: imprecision / warning / minor / severe.

    Returns:
        {
            "imprecision": [ {text,type}, …],
            "warning":     [ … ],
            "minor":       [ … ],
            "severe":      [ … ],
        }
    """
    buckets = defaultdict(list)  # category -> list[dict]

    for row in attempt_rows:
        raw = row.get("Results")
        if not raw:
            continue
        try:
            data = json.loads(raw)
            err = data.get("errors", {})
            for cat in ("imprecision", "warning", "minor", "severe"):
                buckets[cat].extend(err.get(cat, []))
        except json.JSONDecodeError:
            logger.debug("Bad JSON skipped for Session %s", row["Session_ID"])

    # Deduplicate within each bucket
    return {cat: deduplicate(entries) for cat, entries in buckets.items()}


def deduplicate(entries):
    """
    Remove duplicates by (text, type) pair while preserving order.
    """
    seen, dedup = set(), []
    for e in entries:
        key = (e.get("text"), e.get("type"))
        if key not in seen:
            seen.add(key)
            dedup.append({"text": e.get("text"), "type": e.get("type")})
    return dedup


def top_errors(entry_list, top_n=5):
    """
    For a list of error dicts (with 'text' keys) return the N most common texts.
    """
    counts = Counter(e["text"] for e in entry_list)
    return counts.most_common(top_n)


# ────────────────────────────────────────────────────────────────────────────────
# 📝  AI-powered summariser (optional)
# ────────────────────────────────────────────────────────────────────────────────
def ai_summary_for_minigame(game_name: str, summary_stats: dict, errors: dict, client):
    """
    Call your LLM client to produce a natural-language executive summary.
    """
    prompt = f"""
    You are an expert training analyst.

    The mini-game **{game_name}** has the following aggregated metrics:
    Return exactly these sections as second-level headings (##). Use short paragraphs (no bullet symbols). Do not include any introduction before the first heading.

    ## Overall Performance
    Summarize completion rate, number of attempts, average/min/max score, and inferred difficulty.

    ## Frequent Mistakes
    Describe the most common minor and severe errors and their implications on learning/performance.

    ## Recommendations for Instructors/Designers
    Give practical, actionable changes to content, pacing, scaffolding, or feedback loops.

    ## Tips for Players
    Give practical, actionable tips for improving performance in the next attempts.

    Data to analyze:
    SUMMARY_STATS:
    {json.dumps(summary_stats, indent=2)}

    ERROR_BUCKETS:
    {json.dumps(errors, indent=2)}
    """

    if callable(client):
        # If client is a callable function (e.g., local LLM)
        return cleanup_llm_response(client(prompt.strip()))
    else:
        # API supports role-based messages
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a gameplay data analyst."},
                {"role": "user", "content": prompt.strip()},
            ],
        )
        return cleanup_llm_response(response.choices[0].message.content)


# Helper similar to response_cleanup in user_analysis.py
def cleanup_llm_response(text):
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)  # bold
    text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)  # italics
    text = re.sub(r"`([^`]*)`", r"\1", text)  # inline code
    text = re.sub(r"<[^>]+>", "", text)  # html tags
    text = re.sub(r"\n{3,}", "\n\n", text)  # extra lines
    return text.strip()

def search_minigames_by_name(query: str):
    like_query = f"%{query.lower()}%"
    query = text("""
        SELECT Level_ID, Game_ID, REPLACE(Name, '<br>', ' - ') AS Name
        FROM IMA_Game_Level
        WHERE LOWER(Name) LIKE :like_query
        ORDER BY Game_ID, Level_ID;
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"like_query": like_query}).fetchall()
    return [dict(r._mapping) for r in rows]
