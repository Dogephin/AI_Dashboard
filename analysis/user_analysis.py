from sqlalchemy import text
from db import engine
import json
import logging
import re

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

