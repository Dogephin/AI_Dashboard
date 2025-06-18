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


def analyze_single_attempt(results, client):

    prompt_text = f"""
    You are an expert training analyst. I will provide you with the detailed JSON result of a user's attempt in a serious game training module. Your task is to analyze the performance based on the structured metrics provided.

    The JSON will contain the following fields:

    `Game_Start` and `Game_End`: timestamps indicating the start and end of the attempt.
    `total-time`: the total time taken in seconds.
    `final-score`: the user's total score for the attempt.
    `accuracy`: percentage of accuracy based on correct actions performed.
    `status`: whether the attempt was complete or incomplete.
    `errors`: a nested object with categorized errors:

    `good`: actions correctly performed with relevant `score`, `time`, `text`, `short`, and `milestone`.
    `minor`: minor issues (e.g., suboptimal timing or missteps), each with a `score` penalty, `time`, `text`, and `type` (e.g., `"early"` or `"incorrect"`).
    `warning`: warning-level issues (not critical but worth noting).
    `severe`: severe mistakes (critical actions missed or incorrectly performed).
    `gameEvent`: a chronological list of start-end labeled milestones or stages performed by the user, with timestamps.

    Based on this JSON, please:

    1. Provide a summary of the user's overall performance (e.g., efficiency, accuracy, completion).
    2. Highlight any severe or minor errors and what they indicate about the user's understanding or behavior.
    3. Comment on the sequence and timing of the user's actions — was the progression logical or disorganized?
    4. Suggest specific areas for improvement, and which types of errors should be prioritized for training.
    5. If performance was good, point out the strengths and what the user did especially well.
    6. Provide any additional insights that could help in understanding the user's performance in this training module.
    7. Provide a overall conclusion about the user's performance in this attempt.

    Respond in a structured paragraph format and avoid referencing specific IDs (e.g., level\_id, seq\_id). Use human-friendly language. 
    No overall title is needed, just start with the main paragraphs and its headings.


    Here is the data:
    {json.dumps(results, indent=2)}
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a gameplay data analyst."},
            {"role": "user", "content": prompt_text}
        ]
    )

    analysis = response.choices[0].message.content
    return analysis

def response_cleanup(response):
    # Remove bold and italic (e.g., **text**, *text*, __text__, _text_)
    response = re.sub(r'(\*\*|__)(.*?)\1', r'\2', response)
    response = re.sub(r'(\*|_)(.*?)\1', r'\2', response)

    # Remove inline code `text`
    response = re.sub(r'`([^`]*)`', r'\1', response)

    # Remove headings (e.g., ### Title)
    response = re.sub(r'^\s{0,3}#{1,6}\s*', '', response, flags=re.MULTILINE)

    # Remove horizontal rules (---, ***, etc.)
    response = re.sub(r'^-{3,}|^\*{3,}|^_{3,}', '', response, flags=re.MULTILINE)

    # Remove blockquotes
    response = re.sub(r'^\s{0,3}>\s?', '', response, flags=re.MULTILINE)

    # Remove links but keep the text [text](url) -> text
    response = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', response)

    # Remove images ![alt](url) -> alt
    response = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', response)

    # Remove inline HTML tags (e.g., <b>, <i>)
    response = re.sub(r'<[^>]+>', '', response)

    # Normalize extra whitespace
    response = re.sub(r'\n{3,}', '\n\n', response)

    return response.strip()
