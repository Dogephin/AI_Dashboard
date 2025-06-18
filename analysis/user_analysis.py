from sqlalchemy import text
from db import engine
import json
import logging
import re
from statistics import mean

logger = logging.getLogger(__name__)

def get_list_of_users():
    query = text("""
        SELECT DISTINCT Id as "user_id", Username as "username" FROM account
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            users = [dict(row._mapping) for row in result.fetchall()]
        logger.info(f"Fetched {len(users)} unique users from the database.")
        return users
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}")
        return []

def get_list_of_games():
    query = text("""
        SELECT igl.Level_ID, igl.Game_ID, REPLACE(igl.Name, '<br>', ' - ') AS Name, ipg.Plan_Game_ID
        FROM ima_plan_game AS ipg
        JOIN ima_progression_sequence_level AS ipsl ON ipg.Sequence = ipsl.Sequence_ID
        JOIN ima_game_level AS igl ON ipsl.Level_ID = igl.Level_ID

        UNION

        SELECT igl.Level_ID, igl.Game_ID, REPLACE(igl.Name, '<br>', ' - ') AS Name, ipg.Plan_Game_ID
        FROM ima_plan_game AS ipg
        JOIN ima_game_level AS igl ON ipg.Level = igl.Level_ID  -- assumes `ima_plan_game.Level` points to `ima_game_level.Level_ID`
        ORDER BY Name;
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            games = [dict(row._mapping) for row in result.fetchall()]
        logger.info(f"Fetched {len(games)} unique games from the database.")
        return games
    except Exception as e:
        logger.error(f"Failed to fetch games: {e}")
        return []

def get_user_game_results(user_id, game_id):
    query = text("""
        SELECT
        -- ps.Session_ID, ps.User_ID,
        -- psgs.Plan_Game_ID
        psgs.Status, psgs.Game_Start, psgs.Game_End, psgs.Score, psgs.Results AS "Overall_Results"
        -- pg.Level
        FROM ima_plan_session as ps
        JOIN ima_plan_session_game_status as psgs ON ps.Session_ID = psgs.Session_ID
        JOIN ima_plan_game as pg ON psgs.Plan_Game_ID = pg.Plan_Game_ID
        WHERE ps.User_ID = :user_id AND pg.Level = :game_id
    """
    )

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id, "game_id": game_id})
            rows = result.fetchall()

        results = [dict(row._mapping) for row in rows]
        logger.info(f"Fetched {len(results)} game results for user {user_id} and game {game_id}")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch game results for user {user_id} and game {game_id}: {e}")
        return []


def analyze_results(results):
    all_scores = [r["Score"] for r in results]
    completed = [r for r in results if r["Status"] == "complete"]
    failed = [r for r in results if r["Status"] == "fail"]

    # Create a trend based on order of attempts
    score_trend = [{"Attempt": f"Attempt {i+1}", "Score": r["Score"]} for i, r in enumerate(results)]

    return {
        "attempts": len(results),
        "completed_attempts": len(completed),
        "failed_attempts": len(failed),
        "average_score": round(mean(all_scores), 2) if all_scores else 0,
        "min_score": min(all_scores) if all_scores else 0,
        "max_score": max(all_scores) if all_scores else 0,
        "trend": score_trend
    }
