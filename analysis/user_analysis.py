from flask import session
from sqlalchemy import text
from utils.db import engine
import json
import logging
import re
from statistics import mean
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def get_list_of_users():
    role = session.get("role")
    user_id = session.get("user_id")
    print("DEBUG session user_id:", user_id)

    if role == "teacher":
        query = text(
            """
            SELECT DISTINCT Id as "user_id", Username as "username"
            FROM Account A
            INNER JOIN IMA_Admin_User IAU ON A.Id = IAU.User_ID
            WHERE IAU.Admin_ID = :user_id
        """
        )
        params = {"user_id": user_id}
    else:
        query = text(
            """
            SELECT DISTINCT Id as "user_id", Username as "username"
            FROM Account
        """
        )
        params = {}

    try:
        with engine.connect() as conn:
            result = conn.execute(query, params)
            users = [dict(row._mapping) for row in result.fetchall()]
        logger.info(f"Fetched {len(users)} unique users from the database.")
        return users
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}")
        return []


def get_list_of_games():
    query = text(
        """
        SELECT igl.Level_ID, igl.Game_ID, REPLACE(igl.Name, '<br>', ' - ') AS Name, ipg.Plan_Game_ID
        FROM IMA_Plan_Game AS ipg
        JOIN IMA_Progression_Sequence_Level AS ipsl ON ipg.Sequence = ipsl.Sequence_ID
        JOIN IMA_Game_Level AS igl ON ipsl.Level_ID = igl.Level_ID

        UNION

        SELECT igl.Level_ID, igl.Game_ID, REPLACE(igl.Name, '<br>', ' - ') AS Name, ipg.Plan_Game_ID
        FROM IMA_Plan_Game AS ipg
        JOIN IMA_Game_Level AS igl ON ipg.Level = igl.Level_ID  -- assumes `IMA_Plan_Game.Level` points to `IMA_Game_Level.Level_ID`
        ORDER BY Name;
    """
    )

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            games = [dict(row._mapping) for row in result.fetchall()]

        # Add a custom row at the bottom for overall mistake analysis
        custom_row = {
            "Level_ID": "",
            "Game_ID": "",
            "Name": "Overall Mistakes",
            "Plan_Game_ID": "",
        }
        games.append(custom_row)
        logger.info(f"Fetched {len(games)} unique games from the database.")
        return games
    except Exception as e:
        logger.error(f"Failed to fetch games: {e}")
        return []


def get_user_game_results(user_id, game_id, date_start=None, date_end=None):
    query = """
        WITH combined AS (
            SELECT
                ps.User_ID, psgs.Game_Start, psgs.Game_End, psgs.Status, 
                psgs.Score, psgs.Results AS "Overall_Results",
                CASE 
                WHEN ps.Results LIKE '%Training%' 
                    THEN MAX(CASE WHEN psl.Sequence_Order = 0 THEN psl.Level_ID END)
                WHEN ps.Results LIKE '%Practice%' 
                    THEN MAX(CASE WHEN psl.Sequence_Order = 1 THEN psl.Level_ID END)
                END AS GameLevel
            FROM IMA_Plan_Session AS ps
            JOIN IMA_Plan_Session_Game_Status AS psgs ON ps.Session_ID = psgs.Session_ID
            JOIN IMA_Plan_Game AS pg ON psgs.Plan_Game_ID = pg.Plan_Game_ID
            JOIN IMA_Progression_Sequence_Level AS psl ON pg.Sequence = psl.Sequence_ID
            GROUP BY ps.Session_ID, pg.Plan_Game_ID

            UNION

            -- SELECT RESULTS THAT ARE NOT MATCHED ABOVE WITH NO PROGRESSION SEQUENCE (e.g. Assessment Levels)
            SELECT
                ps.User_ID, psgs.Game_Start, psgs.Game_End, psgs.Status, 
                psgs.Score, psgs.Results AS "Overall_Results",
                pg.Level AS GameLevel
            FROM IMA_Plan_Session AS ps
            JOIN IMA_Plan_Session_Game_Status AS psgs ON ps.Session_ID = psgs.Session_ID
            JOIN IMA_Plan_Game AS pg ON psgs.Plan_Game_ID = pg.Plan_Game_ID
            WHERE NOT EXISTS (
                SELECT 1
                FROM IMA_Progression_Sequence_Level psl2
                WHERE pg.Sequence = psl2.Sequence_ID
            )
        )
        SELECT *,
        JSON_LENGTH(Overall_Results->'$.errors.imprecision') AS "Imprecisions",
        JSON_LENGTH(Overall_Results->'$.errors.warning')     AS "Warnings",
        JSON_LENGTH(Overall_Results->'$.errors.minor')       AS "Minor Errors",
        JSON_LENGTH(Overall_Results->'$.errors.severe')      AS "Severe Errors"
        FROM combined
        WHERE User_ID = :user_id and GameLevel = :game_id
    """

    params = {"user_id": user_id, "game_id": game_id}

    if date_start and date_end:
        query += " AND Game_Start BETWEEN :date_start AND :date_end"
        params["date_start"] = date_start + " 00:00:00"
        params["date_end"] = date_end + " 23:59:59"

    query = text(query)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()

        results = [dict(row._mapping) for row in rows]
        logger.info(
            f"Fetched {len(results)} game results for user {user_id} and game {game_id}"
        )
        return results
    except Exception as e:
        logger.error(
            f"Failed to fetch game results for user {user_id} and game {game_id}: {e}"
        )
        return []


def get_user_all_games_results(user_id):
    """
    Get all games played by a specific user across all minigames
    Reuses existing query logic but for all games
    """
    query = text(
        """
        WITH combined AS (
            SELECT
                ps.Session_ID, ps.User_ID, ps.Results,
                psgs.Plan_Game_ID, psgs.Status, psgs.Game_Start, psgs.Game_End, 
                psgs.Score, psgs.Results AS "Overall_Results",
                CASE 
                    WHEN ps.Results LIKE '%Training%' 
                        THEN MAX(CASE WHEN psl.Sequence_Order = 0 THEN psl.Level_ID END)
                    WHEN ps.Results LIKE '%Practice%' 
                        THEN MAX(CASE WHEN psl.Sequence_Order = 1 THEN psl.Level_ID END)
                END AS GameLevel
            FROM IMA_Plan_Session AS ps
            JOIN IMA_Plan_Session_Game_Status AS psgs 
                ON ps.Session_ID = psgs.Session_ID
            JOIN IMA_Plan_Game AS pg 
                ON psgs.Plan_Game_ID = pg.Plan_Game_ID
            JOIN IMA_Progression_Sequence_Level AS psl 
                ON pg.Sequence = psl.Sequence_ID
            GROUP BY ps.Session_ID, ps.User_ID, ps.Results,
                    psgs.Plan_Game_ID, psgs.Status, psgs.Game_Start, 
                    psgs.Game_End, psgs.Score, psgs.Results
            UNION
            SELECT
                ps.Session_ID, ps.User_ID, ps.Results,
                psgs.Plan_Game_ID, psgs.Status, psgs.Game_Start, psgs.Game_End, 
                psgs.Score, psgs.Results AS "Overall_Results",
                pg.Level AS GameLevel
            FROM IMA_Plan_Session AS ps
            JOIN IMA_Plan_Session_Game_Status AS psgs 
                ON ps.Session_ID = psgs.Session_ID
            JOIN IMA_Plan_Game AS pg 
                ON psgs.Plan_Game_ID = pg.Plan_Game_ID
            WHERE NOT EXISTS (
                SELECT 1
                FROM IMA_Progression_Sequence_Level psl2
                WHERE pg.Sequence = psl2.Sequence_ID
            )
        )
        SELECT
            c.GameLevel AS Level_ID,
            REPLACE(igl.Name, '<br>', ' - ') AS Game_Name,
            c.Status,
            c.Game_Start,
            c.Game_End,
            c.Score,
            c.Overall_Results
        FROM combined c
        JOIN IMA_Game_Level igl 
            ON c.GameLevel = igl.Level_ID
        WHERE c.User_ID = :user_id
        ORDER BY igl.Name, c.Game_Start;
    """
    )

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id})
            rows = result.fetchall()

        results = [dict(row._mapping) for row in rows]
        logger.info(f"Fetched {len(results)} total game results for user {user_id}")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch all game results for user {user_id}: {e}")
        return []


def analyze_results(results, analysis_type="single_game"):
    """
    Extended existing analyze_results function to handle both single game and overall assessment
    """
    if analysis_type == "overall_assessment":
        return analyze_overall_assessment(results)

    # Existing single game analysis
    all_scores = [r["Score"] for r in results if r["Score"] is not None]
    completed = [r for r in results if r["Status"] == "complete"]
    failed = [r for r in results if r["Status"] == "fail"]

    error_trend = []

    # Create a trend based on order of attempts
    score_trend = [
        {"Attempt": f"Attempt {i+1}", "Score": r["Score"]}
        for i, r in enumerate(results)
        if r["Score"] is not None
    ]

    for i, r in enumerate(results):
        # Collect error counts per attempt
        attempt_label = f"Attempt {i+1}"
        error_trend.append(
            {
                "Attempt": attempt_label,
                "Imprecisions": r.get("Imprecisions", 0),
                "Warnings": r.get("Warnings", 0),
                "Minor": r.get("Minor Errors", 0),
                "Severe": r.get("Severe Errors", 0),
            }
        )

    return {
        "attempts": len(results),
        "completed_attempts": len(completed),
        "failed_attempts": len(failed),
        "average_score": round(mean(all_scores), 2) if all_scores else 0,
        "min_score": min(all_scores) if all_scores else 0,
        "max_score": max(all_scores) if all_scores else 0,
        "trend": score_trend,
        "errors": error_trend,
    }


def analyze_overall_assessment(results):
    """
    Analyze results for overall assessment across all minigames
    """
    from collections import defaultdict
    import re

    # Group results by game
    games_data = defaultdict(list)

    for result in results:
        if result.get("Score") is not None:
            # Clean game name
            game_name = re.sub(r"<.*?>", "", result.get("Game_Name", "")).strip()
            games_data[game_name].append(
                {"score": result["Score"], "status": result["Status"]}
            )

    # Calculate stats per game
    game_stats = []
    for game_name, game_results in games_data.items():
        scores = [r["score"] for r in game_results if r["score"] is not None]
        if scores:
            game_stats.append(
                {
                    "game_name": game_name,
                    "average_score": round(mean(scores), 2),
                    "total_attempts": len(game_results),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "completed": len(
                        [r for r in game_results if r["status"] == "complete"]
                    ),
                }
            )

    # Sort by average score (lowest to highest)
    game_stats.sort(key=lambda x: x["average_score"])

    return {
        "analysis_type": "overall_assessment",
        "total_games": len(game_stats),
        "overall_average": (
            round(mean([stat["average_score"] for stat in game_stats]), 2)
            if game_stats
            else 0
        ),
        "game_stats": game_stats,
        "chart_data": {
            "labels": [stat["game_name"] for stat in game_stats],
            "datasets": [
                {
                    "label": "Average Score",
                    "data": [stat["average_score"] for stat in game_stats],
                    "backgroundColor": "rgba(54, 162, 235, 0.6)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1,
                }
            ],
        },
    }


def analyze_single_attempt(results, client):

    prompt_text = f"""
    You are an expert training analyst. I will provide you with the detailed JSON result of a user's attempt in a serious game training module. Your task is to analyze the performance based on the structured metrics provided.

    The JSON will contain the following fields:

    `Game_Start` and `Game_End`: timestamps indicating the start and end of the attempt.
    `Imprecisions`: count of imprecision errors.
    `Warnings`: count of warning-level issues.
    `Minor Errors`: count of minor mistakes.
    `Severe Errors`: count of severe mistakes.
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
    4. Based on the error counts, what are the key areas where the user struggled and what is their current skill level?
    5. Suggest specific areas for improvement, and which types of errors should be prioritized for training.
    6. If performance was good, point out the strengths and what the user did especially well.
    7. Provide any additional insights that could help in understanding the user's performance in this training module.
    8. Provide a overall conclusion about the user's performance in this attempt.

    Respond in a structured paragraph format and avoid referencing specific IDs (e.g., level\_id, seq\_id). Use human-friendly language. 
    No overall title is needed, just start with the main paragraphs and its headings. The headings should be third-level headings (###).

    Your response must be in English language.

    Here is the data:
    {json.dumps(results, indent=2)}
    """

    if callable(client):
        # If client is a callable function (e.g., local LLM)
        return client(prompt_text)
    else:
        # API supports role-based messages
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a gameplay data analyst."},
                {"role": "user", "content": prompt_text},
            ],
        )
        return response.choices[0].message.content


def analyze_multiple_attempts(results, client):

    summarized_attempts = []

    for attempt in results:
        try:
            raw = json.loads(attempt.get("Overall_Results", "{}"))
        except json.JSONDecodeError:
            continue

        summarized_attempts.append(
            {
                "Start": attempt.get("Game_Start"),
                "End": attempt.get("Game_End"),
                "Status": attempt.get("Status"),
                "Final Score": raw.get("final-score", 0),
                "Accuracy (%)": raw.get("accuracy", 0),
                "Duration (s)": round(raw.get("total-time", 0), 2),
                "Minor Errors": raw.get("minor-count", 0),
                "Warnings": raw.get("warning-count", 0),
                "Severe Errors": raw.get("severe-count", 0),
                "Good Actions": len(raw.get("errors", {}).get("good", [])),
                "Minor Actions": len(raw.get("errors", {}).get("minor", [])),
                "Warning Actions": len(raw.get("errors", {}).get("warning", [])),
                "Severe Actions": len(raw.get("errors", {}).get("severe", [])),
            }
        )

        # If more than 20 attempts, summarize to the first 20
        if len(summarized_attempts) > 20:
            summarized_attempts = summarized_attempts[:20]

    prompt_text = f"""
    You are an expert training analyst. Below is a JSON list of gameplay attempts for a training module by the same user. 
    Each object contains the attempt's status, start and end time, final score, and a result field with detailed breakdown.

    Please analyze the entire dataset holistically by:
    1. Identify performance trends across attempts (improving, stable, declining).
    2. Highlight common patterns: error types, durations, success rates.
    3. Compare successful and failed attempts — what distinguishes them?
    4. Pinpoint what the user struggles with consistently.
    5. Provide improvement suggestions tailored to repeated weaknesses.
    6. Recognize strengths and highlight consistent good practices.
    7. End with a summary of the user's overall progress and training readiness.

    Respond in a structured paragraph format and avoid referencing specific IDs (e.g., level\_id, seq\_id). Use human-friendly language. 
    No overall title is needed, just start with the main paragraphs and its headings. The headings should be third-level headings (###).

    JSON Data:
    {json.dumps(summarized_attempts, indent=2)}
    """

    if callable(client):
        # If client is a callable function (e.g., local LLM)
        return client(prompt_text)
    else:
        # API supports role-based messages
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a gameplay data analyst."},
                {"role": "user", "content": prompt_text},
            ],
        )
        return response.choices[0].message.content


def response_cleanup(response):
    # Remove bold and italic (e.g., **text**, *text*, __text__, _text_)
    response = re.sub(r"(\*\*|__)(.*?)\1", r"\2", response)
    response = re.sub(r"(\*|_)(.*?)\1", r"\2", response)

    # Remove inline code `text`
    response = re.sub(r"`([^`]*)`", r"\1", response)

    # Remove headings (e.g., ### Title)
    response = re.sub(r"^\s{0,3}#{1,6}\s*", "", response, flags=re.MULTILINE)

    # Remove horizontal rules (---, ***, etc.)
    response = re.sub(r"^-{3,}|^\*{3,}|^_{3,}", "", response, flags=re.MULTILINE)

    # Remove blockquotes
    response = re.sub(r"^\s{0,3}>\s?", "", response, flags=re.MULTILINE)

    # Remove links but keep the text [text](url) -> text
    response = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", response)

    # Remove images ![alt](url) -> alt
    response = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", response)

    # Remove inline HTML tags (e.g., <b>, <i>)
    response = re.sub(r"<[^>]+>", "", response)

    # Normalize extra whitespace
    response = re.sub(r"\n{3,}", "\n\n", response)

    return response.strip()


def trim_first_and_last_line(text: str) -> str:
    lines = text.strip().splitlines()
    if len(lines) <= 2:
        return ""  # Not enough content to trim
    trimmed = "\n".join(lines[1:-1])
    return trimmed.strip()


# Deduplication helper
def deduplicate(entries):
    seen = set()
    result = []
    for entry in entries:
        key = (entry.get("text"), entry.get("type"))
        if key not in seen:
            seen.add(key)
            result.append({"text": entry.get("text"), "type": entry.get("type")})
    return result


def fetch_user_errors(user_id):
    thirty_days_ago = datetime.now() - timedelta(days=30)

    query = text(
        """
        SELECT GS.results
        FROM IMA_Plan_Session_Game_Status AS GS
        INNER JOIN IMA_Plan_Session AS PS ON GS.Session_ID = PS.Session_ID
        WHERE PS.User_ID = :user_id
        AND GS.Game_End >= :thirty_days_ago
    """
    )

    try:
        with engine.connect() as conn:
            result = conn.execute(
                query, {"user_id": user_id, "thirty_days_ago": thirty_days_ago}
            )
            rows = result.fetchall()

        # Storage for all error categories
        all_imprecision, all_warning, all_minor, all_severe = [], [], [], []

        for row in rows:
            raw = row[0]
            if raw is None:
                continue

            try:
                data = json.loads(raw)
                all_imprecision.extend(data.get("errors", {}).get("imprecision", []))
                all_warning.extend(data.get("errors", {}).get("warning", []))
                all_minor.extend(data.get("errors", {}).get("minor", []))
                all_severe.extend(data.get("errors", {}).get("severe", []))
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping invalid JSON: {e}")

        # Deduplicate results
        all_imprecision = deduplicate(all_imprecision)
        all_warning = deduplicate(all_warning)
        all_minor = deduplicate(all_minor)
        all_severe = deduplicate(all_severe)

        return {
            "imprecision": all_imprecision,
            "warning": all_warning,
            "minor": all_minor,
            "severe": all_severe,
        }

    except Exception as e:
        logger.error(f"Failed to fetch user errors for user {user_id}: {e}")
        return {"imprecision": [], "warning": [], "minor": [], "severe": []}


def categorize_mistakes(errors, client):
    prompt_text = f"""
    You are an expert training analyst.
    The data below shows the text and types of errors that a user has made:

    {errors}

    Please help to categorize these errors according to their texts 
    and provide any recommendations on what the user can do to reduce making these errors in the game
    assuming you can't change how the game works if possible

    Ensure that the texts are kept exactly the same
    """
    if callable(client):
        # If client is a callable function (e.g., local LLM)
        raw_output = client(prompt_text)
    else:
        # API supports role-based messages
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a gameplay data analyst."},
                {"role": "user", "content": prompt_text},
            ],
        )
        raw_output = response.choices[0].message.content

    cleaned_ouput = response_cleanup(raw_output)
    final_output = trim_first_and_last_line(cleaned_ouput)

    return final_output


def generate_error_trend_prompt(user_id, game_id, errors, scores, client):
    """
    Generate  AI prompt based on error trends and scores.
    """

    prompt_text = f"""
    You are an expert training analyst. I will provide you with summarized gameplay error data
    across multiple attempts for a serious game training module. Your task is to analyze performance trends.

    Data includes counts of:
    - Imprecisions
    - Warnings
    - Minor Errors
    - Severe Errors
    for each attempt. Scores achieved for each attempt are also provided.

    Please provide a structured analysis with the following sections:

    1. Overall Performance: Summarize the user's overall performance across all attempts.
    2. Error Trends: Highlight trends, repeated issues, or spikes in error types.
    3. Improvement with Practice: Analyze whether the user improves with practice; highlight improvement curves or stagnation points.
    4. Strengths: Point out areas where the user performs consistently well.
    5. Areas for Training: Suggest which error types should be prioritized for training.
    6. Recommendations: Provide actionable insights for future attempts or training focus areas.

    Respond in a structured paragraph format and avoid referencing specific IDs (e.g., level\_id, seq\_id). Use human-friendly language. 


    Here is the data:
    User ID: {user_id}
    Game ID: {game_id}
    Errors:
    {json.dumps(errors, indent=2)}
    Scores:
    {scores}
    """

    if callable(client):
        # If client is a callable function (e.g., local LLM)
        return client(prompt_text)
    else:
        # API supports role-based messages
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a gameplay data analyst."},
                {"role": "user", "content": prompt_text},
            ],
        )
        return response.choices[0].message.content
