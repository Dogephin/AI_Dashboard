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
               TRIM(
                REPLACE(
                    REPLACE(Name, '<br>', ' - '),   -- change <br> to ' - '
                    'Training', ''                  -- remove the word Training
                    )
                ) AS Name
        FROM   IMA_Game_Level
        WHERE Name Like '%Training%' OR Name Like '%Assessment%'
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
    
def get_minigame_attempts_by_mode(game_id: int, mode: str = "all"):
    """
    Pull every attempt of a given mini-game (level) across all users,
    filtered by mode ('practice', 'training', or 'all').

    Returns a list of dicts:
        {
            "Session_ID": …,
            "User_ID": …,
            "Status": "complete" | "fail" | "Userexit" | "toplay",
            "Score": 87,
            "Results": '{…JSON…}',   # can be NULL
            "Game_Start": "2025-05-22 02:12:34",
            "Game_End":   "2025-05-22 02:17:41",
            "Mode": "practice" | "training" | "unknown"
        }
    """
    # Build optional WHERE clause
    mode = (mode or "all").lower()
    if mode == "practice":
        mode_pred = (
            "AND (LOWER(ps.Results) LIKE '%practice%' "
            "  OR LOWER(psgs.Results) LIKE '%practice%')"
        )
    elif mode == "training":
        mode_pred = (
            "AND (LOWER(ps.Results) LIKE '%training%' "
            "  OR LOWER(psgs.Results) LIKE '%training%')"
        )
    else:
        mode_pred = ""

    query = text(f"""
        SELECT 
            psgs.Session_ID,
            ps.User_ID,
            psgs.Status,
            psgs.Score,
            psgs.Results,
            psgs.Game_Start,
            psgs.Game_End,
            CASE 
                WHEN LOWER(ps.Results) LIKE '%practice%' 
                     OR LOWER(psgs.Results) LIKE '%practice%' 
                     THEN 'practice'
                WHEN LOWER(ps.Results) LIKE '%training%' 
                     OR LOWER(psgs.Results) LIKE '%training%' 
                     THEN 'training'
                ELSE 'unknown'
            END AS Mode
        FROM IMA_Plan_Game AS pg
        JOIN IMA_Plan_Session_Game_Status AS psgs
          ON pg.Plan_Game_ID = psgs.Plan_Game_ID
        JOIN IMA_Plan_Session AS ps
          ON ps.Session_ID = psgs.Session_ID
        WHERE pg.Level = :game_id
        {mode_pred}
        ORDER BY psgs.Game_Start, psgs.Session_ID;
    """)

    try:
        with engine.connect() as conn:
            rows = conn.execute(query, {"game_id": game_id}).fetchall()
        attempts = [dict(r._mapping) for r in rows]
        logger.info("Fetched %d attempts for minigame %s (mode=%s)", len(attempts), game_id, mode)
        return attempts
    except Exception as exc:
        logger.error("Failed to fetch attempts for game %s (mode=%s): %s", game_id, mode, exc)
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

def _summarize_attempts_for_mode(attempts):
    """
    attempts: list[dict] from get_minigame_attempts_by_mode(...)
    returns per-mode summary:
      {
        "mode": "practice|training",
        "completed": int, "failed": int, "userexit": int, "unique_users": int,
        "failure_success_ratio": float|None, "failure_success_str": "f:c",
        "avg_attempts_before_success": float|None, "users_considered": int
      }
    """
    if not attempts:
        return {
            "mode": None, "completed": 0, "failed": 0, "userexit": 0,
            "unique_users": 0, "failure_success_ratio": None, "failure_success_str": "0:0",
            "avg_attempts_before_success": None, "users_considered": 0
        }

    mode = attempts[0].get("Mode") or None
    completed = sum(1 for a in attempts if a.get("Status") == "complete")
    failed    = sum(1 for a in attempts if a.get("Status") == "fail")
    userexit  = sum(1 for a in attempts if a.get("Status") == "Userexit")
    users     = {a.get("User_ID") for a in attempts if a.get("User_ID") is not None}
    unique_users = len(users)

    ratio = (failed / completed) if completed > 0 else None
    ratio_str = f"{failed}:{completed}"

    # Average attempts before first success per user:
    # number of attempts strictly before the first 'complete' for that user in this mode.
    attempts_by_user = {}
    for a in sorted(attempts, key=lambda x: (x.get("Game_Start") or x.get("Game_End"), x.get("Session_ID"))):
        uid = a.get("User_ID")
        if uid is None:
            continue
        attempts_by_user.setdefault(uid, []).append(a)

    per_user_counts = []
    for uid, seq in attempts_by_user.items():
        first_success_idx = next((i for i, row in enumerate(seq) if row.get("Status") == "complete"), None)
        if first_success_idx is not None:
            per_user_counts.append(first_success_idx)  # N-1 attempts before success (0-based index)
    users_considered = len(per_user_counts)
    avg_before = round(sum(per_user_counts) / users_considered, 2) if users_considered > 0 else None

    return {
        "mode": mode,
        "completed": completed,
        "failed": failed,
        "userexit": userexit,
        "unique_users": unique_users,
        "failure_success_ratio": None if ratio is None else round(float(ratio), 2),
        "failure_success_str": ratio_str,
        "avg_attempts_before_success": avg_before,
        "users_considered": users_considered,
    }


def build_ai_explain_payload_from_attempts(level_id: int, mode: str = "all"):
    """
    Uses get_minigame_attempts_by_mode to build the AI explain payload.
    If mode='all', returns both practice and training rows (if present).
    """
    # Get identity/name
    ident_sql = text("""
        SELECT gl.Level_ID, gl.Game_ID, REPLACE(gl.Name, '<br>', ' - ') AS Name
        FROM IMA_Game_Level gl WHERE gl.Level_ID = :level_id LIMIT 1;
    """)
    with engine.connect() as conn:
        ident = conn.execute(ident_sql, {"level_id": level_id}).mappings().first()

    if not ident:
        return {"level_id": level_id, "rows": []}

    rows = []
    m = (mode or "all").lower()
    if m == "all":
        for m1 in ("practice", "training"):
            attempts = get_minigame_attempts_by_mode(level_id, m1)
            if attempts:
                rows.append(_summarize_attempts_for_mode(attempts))
    else:
        attempts = get_minigame_attempts_by_mode(level_id, m)
        if attempts:
            rows.append(_summarize_attempts_for_mode(attempts))

    return {
        "level_id": ident["Level_ID"],
        "game_id":  ident["Game_ID"],
        "name":     ident["Name"],
        "rows":     rows
    }

# --- universal LLM caller (SDK-agnostic), if not already defined ---------------
def _extract_text_from_openai_response(resp):
    choice = getattr(resp, "choices", None)
    if choice and len(choice) > 0:
        msg = getattr(choice[0], "message", None)
        if msg:
            content = getattr(msg, "content", None)
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for p in content:
                    t = p.get("text") if isinstance(p, dict) else None
                    if t: parts.append(t)
                if parts: return "\n".join(parts)
    text_attr = getattr(resp, "output_text", None)
    if isinstance(text_attr, str) and text_attr.strip(): return text_attr
    content = getattr(resp, "content", None)
    if isinstance(content, list):
        chunks = []
        for item in content:
            if hasattr(item, "text") and getattr(item.text, "value", None):
                chunks.append(item.text.value)
            elif isinstance(item, dict) and item.get("type") == "output_text":
                val = item.get("text", {}).get("value")
                if val: chunks.append(val)
        if chunks: return "\n".join(chunks)
    return getattr(resp, "text", None) or getattr(resp, "content", None) or None

def _llm_complete_universal(client, prompt, *, model=None, system=None):
    model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
    if hasattr(client, "complete"):
        resp = client.complete(prompt=prompt)
        text = getattr(resp, "text", None) or getattr(resp, "content", None) or str(resp)
        return text.strip()
    chat = getattr(client, "chat", None)
    completions = getattr(chat, "completions", None) if chat else None
    create = getattr(completions, "create", None) if completions else None
    if callable(create):
        messages = []
        if system: messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = create(model=model, messages=messages, temperature=0.2)
        text = _extract_text_from_openai_response(resp)
        if text: return text.strip()
    responses = getattr(client, "responses", None)
    create2 = getattr(responses, "create", None) if responses else None
    if callable(create2):
        try:
            resp = create2(model=model, input=prompt)
        except TypeError:
            resp = create2(model=model, instructions=prompt)
        text = _extract_text_from_openai_response(resp)
        if text: return text.strip()
    raise AttributeError("No compatible completion method found on LLM client")

def ai_explain_minigame_from_attempts(level_name: str, payload: dict, llm_client):
    def line(r):
        return (f"- Mode: {r['mode']}\n"
                f"  • Completed: {r['completed']} | Failed: {r['failed']} | Userexit: {r['userexit']}\n"
                f"  • Failure:Success = {r['failure_success_str']} (Ratio: {r['failure_success_ratio'] or '—'})\n"
                f"  • Avg Attempts Before First Success: {r['avg_attempts_before_success'] or '—'} "
                f"(Users considered: {r['users_considered']})")
    bullets = "\n".join(line(r) for r in payload.get("rows", []))
    prompt = (
        "You are an instructional game designer. Analyze minigame difficulty and intuitiveness.\n"
        f"Minigame: {level_name}\n"
        "Metrics (by mode):\n"
        f"{bullets}\n\n"
        "Explain succinctly:\n"
        "1) Which mode is more intuitive vs trial-and-error heavy and why (tie to numbers).\n"
        "2) Likely friction points (ambiguity, UI cues, timing, cognitive load, exit causes).\n"
        "3) 3–5 concrete redesign actions improving early success without dumbing down the skill."
    )
    try:
        return _llm_complete_universal(
            llm_client,
            prompt,
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            system="You are an instructional game designer. Be concise, specific, and actionable."
        )
    except Exception as e:
        return f"(AI generation failed: {e})"


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

def ai_explain_for_minigame(game_name: str, payload: dict, client):
    """
    Generate an AI explanation for a minigame.
    Uses the same prompt style as ai_summary_for_minigame,
    but driven by the attempts-based payload.

    Arguments:
        game_name: str - Cleaned minigame name
        payload: dict - { "rows": [ {mode, completed, failed, userexit, ...}, ...] }
        client: OpenAI client

    Returns:
        str: AI explanation
    """
    # Convert attempts payload into a pseudo-summary for the prompt
    summary_stats = {
        "rows": payload.get("rows", [])
    }
    errors = {}  # not relevant here, but kept for signature parity

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

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are an instructional game designer. Provide concise, specific, actionable insights."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"(AI generation failed: {e})"


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
    
def get_combined_game_stats(mode: str = "all"):
    """
    Per-minigame combined stats with optional filtering by Practice/Training/All.
    When mode='all', rows are separated by Mode ('practice' / 'training'), and
    'unknown' is EXCLUDED by default to avoid mixed/ambiguous sessions.
    """
    pred, params = _mode_predicate_and_params(mode)

    # When showing "all", hide unknown by requiring either practice or training text present.
    unknown_filter_all = (
        "AND (COALESCE(LOWER(ps.Results),'') LIKE '%practice%' "
        "  OR COALESCE(LOWER(ps.Results),'') LIKE '%training%' "
        "  OR COALESCE(LOWER(s.Results),'')  LIKE '%practice%' "
        "  OR COALESCE(LOWER(s.Results),'')  LIKE '%training%')"
        if (mode or "all").lower() == "all" else ""
    )

    # ── Failure / Success / Userexit, Users ─────────────────────────────────────
    ratio_sql = text(f"""
        SELECT
            gl.Level_ID,
            gl.Game_ID,
            REPLACE(gl.Name, '<br>', ' - ') AS Name,
            {MODE_EXPR} AS Mode,
            COALESCE(SUM(CASE WHEN s.Status = 'complete' THEN 1 END), 0) AS completed,
            COALESCE(SUM(CASE WHEN s.Status = 'fail'     THEN 1 END), 0) AS failed,
            COALESCE(SUM(CASE WHEN s.Status = 'Userexit' THEN 1 END), 0) AS userexit,
            COALESCE(COUNT(DISTINCT ps.User_ID), 0) AS unique_users
        FROM IMA_Game_Level gl
        LEFT JOIN IMA_Plan_Game pg
               ON pg.Level   = gl.Level_ID
              AND pg.Game_ID = gl.Game_ID
        LEFT JOIN IMA_Plan_Session_Game_Status s
               ON s.Plan_Game_ID = pg.Plan_Game_ID
        LEFT JOIN IMA_Plan_Session ps
               ON ps.Session_ID = s.Session_ID
        WHERE 1=1
        {pred}
        {unknown_filter_all}
        GROUP BY gl.Level_ID, gl.Game_ID, gl.Name, {MODE_EXPR}
        ORDER BY gl.Game_ID, gl.Level_ID, {MODE_EXPR};
    """)

    # ── Avg attempts before first success (partition by Mode too) ───────────────
    avg_sql = text(f"""
        WITH attempts AS (
            SELECT
                gl.Level_ID,
                gl.Game_ID,
                ps.User_ID,
                s.Status,
                s.Session_ID,
                s.Plan_Game_ID,
                COALESCE(s.Game_Start, s.Game_End) AS ts,
                {MODE_EXPR} AS Mode,
                ROW_NUMBER() OVER (
                    PARTITION BY gl.Level_ID, gl.Game_ID, ps.User_ID, {MODE_EXPR}
                    ORDER BY COALESCE(s.Game_Start, s.Game_End), s.Session_ID, s.Plan_Game_ID
                ) AS rn
            FROM IMA_Plan_Session_Game_Status s
            JOIN IMA_Plan_Game pg
              ON pg.Plan_Game_ID = s.Plan_Game_ID
            JOIN IMA_Game_Level gl
              ON gl.Level_ID = pg.Level AND gl.Game_ID = pg.Game_ID
            JOIN IMA_Plan_Session ps
              ON ps.Session_ID = s.Session_ID
            WHERE 1=1
            {pred}
            {unknown_filter_all}
        ),
        first_success AS (
            SELECT Level_ID, Game_ID, User_ID, Mode, MIN(rn) AS first_success_rn
            FROM attempts
            WHERE Status = 'complete'
            GROUP BY Level_ID, Game_ID, User_ID, Mode
        )
        SELECT
            Level_ID,
            Game_ID,
            Mode,
            AVG(first_success_rn - 1) AS avg_attempts_before_success,
            COUNT(User_ID) AS users_considered
        FROM first_success
        GROUP BY Level_ID, Game_ID, Mode;
    """)

    with engine.connect() as conn:
        ratio_rows = {
            (r.Level_ID, r.Game_ID, r.Mode): dict(r._mapping)
            for r in conn.execute(ratio_sql, params).fetchall()
        }
        avg_rows = {
            (r.Level_ID, r.Game_ID, r.Mode): dict(r._mapping)
            for r in conn.execute(avg_sql, params).fetchall()
        }

    combined = []
    for key, base in ratio_rows.items():
        avg = avg_rows.get(key, {})
        completed = base["completed"] or 0
        failed = base["failed"] or 0
        ratio = (failed / completed) if completed > 0 else None
        combined.append({
            **base,  # includes Mode
            "failure_success_ratio": ratio,
            "failure_success_str": f"{failed}:{completed}",
            "avg_attempts_before_success": (
                None if avg.get("avg_attempts_before_success") is None
                else round(float(avg["avg_attempts_before_success"]), 2)
            ),
            "users_considered": avg.get("users_considered", 0),
        })

    return combined



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

def _mode_predicate_and_params(mode: str):
    """
    Filter by Practice / Training / All.
    We match on BOTH ps.Results and s.Results (case-insensitive).
    """
    m = (mode or "all").lower()
    if m == "practice":
        return (
            "AND (COALESCE(LOWER(ps.Results),'') LIKE :practice_q "
            "  OR COALESCE(LOWER(s.Results),'') LIKE :practice_q)",
            {"practice_q": "%practice%"},
        )
    if m == "training":
        return (
            "AND (COALESCE(LOWER(ps.Results),'') LIKE :training_q "
            "  OR COALESCE(LOWER(s.Results),'') LIKE :training_q)",
            {"training_q": "%training%"},
        )
    return "", {}

# Label expression for session mode
MODE_EXPR = (
    "CASE "
    " WHEN COALESCE(LOWER(ps.Results),'') LIKE '%practice%' "
    "   OR COALESCE(LOWER(s.Results),'')  LIKE '%practice%' THEN 'practice' "
    " WHEN COALESCE(LOWER(ps.Results),'') LIKE '%training%' "
    "   OR COALESCE(LOWER(s.Results),'')  LIKE '%training%' THEN 'training' "
    " ELSE 'unknown' END"
)