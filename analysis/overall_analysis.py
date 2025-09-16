from sqlalchemy import text
from utils.db import engine
from collections import defaultdict
import json
import math
import re
import logging
from datetime import datetime
from sqlalchemy import bindparam
from flask import session


logger = logging.getLogger(__name__)


# -- Error Frequency Over Time --
def get_error_frequency_results():
    role = session.get("role")  
    user_id = session.get("user_id")
    if role == "teacher":
        query = text("""SELECT IPSGS.results 
                    FROM IMA_Plan_Session_Game_Status IPSGS
                    INNER JOIN IMA_Plan_Session IPS ON IPSGS.Session_ID = IPS.Session_ID
                    INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
                    WHERE IAU.Admin_ID = :user_id""")
        params = {"user_id": user_id}
    else:
        query = text("SELECT results FROM IMA_Plan_Session_Game_Status")
        params = {} 

    try:
        with engine.connect() as conn:
            result = conn.execute(query , params)
            rows = result.fetchall()

        results = [dict(row._mapping) for row in rows]
        logger.info(f"Fetched {len(results)} rows from the database.")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch results: {e}")
        return []


def bin_errors_over_time(results, bin_size=5):
    aggregated_bins = defaultdict(lambda: {"warnings": 0, "minors": 0, "severes": 0})
    max_time = 0

    for row in results:
        raw_json = row.get("results")
        if not raw_json:
            continue

        try:
            data = json.loads(raw_json)
        except Exception as e:
            logger.warning(f"Skipping invalid JSON: {e}")
            continue

        errors = data.get("errors", {})
        for err_type in ["warning", "minor", "severe"]:
            for err in errors.get(err_type, []):
                t = err.get("time")
                if t is not None:
                    bin_start = int(t // bin_size) * bin_size
                    bin_label = f"{bin_start}-{bin_start + bin_size}s"
                    aggregated_bins[bin_label][f"{err_type}s"] += 1
                    if t > max_time:
                        max_time = t

    # Ensure all bins up to max_time are represented
    total_bins = math.ceil(max_time / bin_size)
    for i in range(total_bins + 1):
        bin_start = i * bin_size
        bin_label = f"{bin_start}-{bin_start + bin_size}s"
        if bin_label not in aggregated_bins:
            aggregated_bins[bin_label] = {"warnings": 0, "minors": 0, "severes": 0}

    sorted_bins = dict(
        sorted(aggregated_bins.items(), key=lambda x: int(x[0].split("-")[0]))
    )

    return sorted_bins


def error_frequency_analysis(results, client):
    # Bin the data
    binned_data = bin_errors_over_time(results, bin_size=5)

    # Keep only bins with any errors
    non_empty_bins = {
        k: v for k, v in binned_data.items() if sum(v.values()) > 0
    }

    try:
        compact_bins = {
            k: {"w": v["warnings"], "m": v["minors"], "s": v["severes"]}
            for k, v in non_empty_bins.items()
        }
        binned_data_json = json.dumps(compact_bins)
    except Exception as e:
        print("[ERROR] Failed to serialize binned data:", e)
        return [{"title": "Error", "content": "Failed to serialize data"}]


    prompt_text = f"""
    You are an expert training analyst.

    I have aggregated the warning, minor and severe errors from multiple game sessions into 5-second time bins.
    The data below shows the count of warnings and minors occurring in each time interval over the entire session duration:

    Return exactly these sections as second-level headings (##). Use short paragraphs (no bullet symbols). Do not include any introduction before the first heading.

    ## Error Spikes 
    Identify when errors tend to spike. Mention which time bins show the highest counts.

    ## Error Distribution Over Time
    Explain whether warnings or minor errors tend to cluster early, mid, or late in sessions.

    ## Recommendations
    Provide clear, actionable recommendations to reduce or address error clustering.

    Data to analyze:
    {binned_data_json}
    """

    if callable(client):
        # If client is a callable function (e.g., local LLM)
        insights_text = client(prompt_text)
    else:
        # API supports role-based messages
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": prompt_text},
            ],
        )
        insights_text = response.choices[0].message.content

    cleaned_insights_frequency_score = clear_formatting(insights_text)
    return cleaned_insights_frequency_score


# -- Overall User Analysis --
def get_user_results():
    role = session.get("role")  
    user_id = session.get("user_id")
    if role == "teacher":
        query = text("""SELECT IPS.User_ID , IPS.results 
                     FROM IMA_Plan_Session IPS 
                     INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
                     WHERE IAU.Admin_ID = :user_id
                     ORDER BY IPS.User_ID""")
        params = {"user_id": user_id}
    else:
        query = text("SELECT User_ID , results FROM IMA_Plan_Session ORDER BY User_ID")
        params = {}

    try:
        with engine.connect() as conn:
            result = conn.execute(query , params)
            rows = result.fetchall()

        results2 = [dict(row._mapping) for row in rows]
        logger.info(f"Fetched {len(results2)} rows from the database.")
        return results2
    except Exception as e:
        logger.error(f"Failed to fetch results: {e}")
        return []


def overall_user_analysis(results2, client):
    prompt_text = f"""
    You are an expert training analyst.

    Return exactly these sections as second-level headings (##) for each point. Use short paragraphs (no bullet symbols). Do not include any introduction before the first heading.

    Data to analyze:
    {results2}

    Can you analyze this data and provide the analysis and insights. Please focus
    on overall user analysis for everyone instead of individuals. 

    """

    if callable(client):
        # If client is a callable function (e.g., local LLM)
        insights_text = client(prompt_text)
    else:
        # API supports role-based messages
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": prompt_text},
            ],
        )
        insights_text = response.choices[0].message.content

    cleaned_insights_overall_score = clear_formatting(insights_text)
    return cleaned_insights_overall_score


# -- Session Duration vs Performance --
def get_duration_vs_errors():
    role = session.get("role")  
    user_id = session.get("user_id")
    if role == "teacher":
        query = text(
            """
            SELECT IPSGS.game_start, IPSGS.game_end, IPSGS.score 
            FROM IMA_Plan_Session_Game_Status IPSGS
            INNER JOIN IMA_Plan_Session IPS ON IPSGS.Session_ID = IPS.Session_ID
            INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
            WHERE IAU.Admin_ID = :user_id
            AND IPSGS.game_start IS NOT NULL AND IPSGS.game_end IS NOT NULL AND score IS NOT NULL
        """
        )
        params = {"user_id": user_id}
    else:
        query = text(
            """
            SELECT game_start, game_end, score 
            FROM IMA_Plan_Session_Game_Status
            WHERE game_start IS NOT NULL AND game_end IS NOT NULL AND score IS NOT NULL
        """
        )
        params = {}

    try:
        with engine.connect() as conn:
            result = conn.execute(query , params)
            rows = result.fetchall()
            logger.info(f"Fetched {len(rows)} rows for duration vs score analysis.")
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return []

    duration_score_data = []
    for row in rows:
        try:
            start = row.game_start
            end = row.game_end
            duration_minutes = round((end - start).total_seconds() / 60.0, 2)
            score = int(row.score)
            if duration_minutes >= 0:
                duration_score_data.append(
                    {"duration_minutes": duration_minutes, "score": score}
                )
        except Exception as e:
            logger.warning(f"Skipping row due to error: {e}")
            continue

    return duration_score_data


def performance_vs_duration(data, client):
    json_data = json.dumps(data, indent=2)

    prompt = f"""
    You are an expert training analyst.

    I have aggregated the training session data showing session duration (in minutes) and the score achieved.
    Return exactly these sections as second-level headings (##). Use short paragraphs (no bullet symbols). Do not include any introduction before the first heading.

    ## Relationship
    Identify insights on the relationship between session duration and score.

    ## Shorter vs Longer Sessions
    Compare and contrast shorter versus longer sessions in terms of score results. 

    ## Optimal Session Length
    Provide clear, actionable recommendations for the users playing the game on optimal session length for best performance.

    ## Additional Insights
    Provide any additional insights regarding the performance vs duration of minigames.

    Data to analyze:
    {json_data}
    """

    if callable(client):
        # If client is a callable function (e.g., local LLM)
        insights_text = client(prompt)
    else:
        # API supports role-based messages
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        insights_text = response.choices[0].message.content

    cleaned_insights_avg_score = clear_formatting(insights_text)
    return cleaned_insights_avg_score


# -- Average Scores for all Minigames --
def get_practice_assessment_rows():
    role = session.get("role")  
    user_id = session.get("user_id")
    if role == "teacher":
        query = text(
            """
            SELECT IPS.Session_ID, IPS.Results
            FROM IMA_Plan_Session IPS
            INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
            WHERE IAU.Admin_ID = :user_id
            AND IPS.Results LIKE '%Practice%'
        """
        )
        params = {"user_id": user_id}

    else:
        query = text(
            """
            SELECT Session_ID, Results
            FROM IMA_Plan_Session
            WHERE Results LIKE '%Practice%'
        """
        )
        params = {}

    try:
        with engine.connect() as conn:
            result = conn.execute(query , params)
            rows = result.fetchall()

        sessions = [dict(row._mapping) for row in rows]
        if sessions:
            print(
                f"[DEBUG] First 5 Session IDs: {[s['Session_ID'] for s in sessions[:5]]}"
            )

        session_ids = [s["Session_ID"] for s in sessions]
        scores = get_scores_for_sessions(session_ids)

        scores_dict = {s["Session_ID"]: s for s in scores}
        for s in sessions:
            sid = s["Session_ID"]
            if sid in scores_dict:
                s["score"] = scores_dict[sid].get("score")
                s["game_results"] = scores_dict[sid].get("results")
            else:
                s["score"] = None
                s["game_results"] = None

        return sessions

    except Exception as e:
        print(f"[ERROR] Failed to fetch practice/assessment rows or scores: {e}")
        return []


def get_scores_for_sessions(session_ids):
    if not session_ids:
        print("[WARN] No session IDs provided to fetch scores.")
        return []
    role = session.get("role")  
    user_id = session.get("user_id")
    if role == "teacher":
        query = text(
            """
            SELECT IPSGS.Session_ID, IPSGS.score, IPSGS.results
            FROM IMA_Plan_Session_Game_Status IPSGS
            INNER JOIN IMA_Plan_Session IPS ON IPSGS.Session_ID = IPS.Session_ID
            INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
            WHERE IAU.Admin_ID = :user_id
            AND IPSGS.Session_ID IN :session_ids
        """
        ).bindparams(bindparam("session_ids", expanding=True))
        params = {"user_id": user_id , "session_ids": session_ids}
    else:

        query = text(
            """
            SELECT Session_ID, score, results
            FROM IMA_Plan_Session_Game_Status
            WHERE Session_ID IN :session_ids
        """
        ).bindparams(bindparam("session_ids", expanding=True))
        params = {"session_ids" : session_ids}
    try:
        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    except Exception as e:
        print(f"[ERROR] Failed to fetch scores: {e}")
        return []


def calculate_avg_score_per_minigame(scores_rows):
    from collections import defaultdict
    import re
    import json

    scores_by_minigame = defaultdict(list)
    max_score_by_minigame = {}

    for row in scores_rows:
        try:
            data = json.loads(row["results"])

            raw_name = data.get("level_name") or data.get("game", "")

            cleaned_name = re.sub(r"<.*?>", "", raw_name).strip()

            match = re.match(r"(MG\d+\s+(?:Practice))", cleaned_name)
            game_key = match.group(1) if match else cleaned_name

            score = row.get("score")
            max_score = data.get("max-score") or data.get("max_score")

            if score is not None:
                scores_by_minigame[game_key].append(score)

            if game_key not in max_score_by_minigame and max_score is not None:
                max_score_by_minigame[game_key] = max_score

        except Exception as e:
            print(f"[WARN] Skipping row due to error: {e}")

    avg_scores = {
        game: sum(scores) / len(scores) if scores else 0
        for game, scores in scores_by_minigame.items()
    }
    return avg_scores, max_score_by_minigame


def get_avg_scores_for_practice_assessment():
    sessions = get_practice_assessment_rows()
    session_ids = [s["Session_ID"] for s in sessions]

    scores_rows = get_scores_for_sessions(session_ids)
    avg_scores, max_score_by_minigame = calculate_avg_score_per_minigame(scores_rows)

    return avg_scores, max_score_by_minigame


def avg_scores_for_practice_assessment_analysis(
    avg_scores, max_score_by_minigame, client
):
    combined_scores = {
        game: {
            "average_score": round(avg_scores.get(game, 0), 2),
            "max_score": max_score_by_minigame.get(game, 0),
        }
        for game in avg_scores
    }

    formatted_data = json.dumps(combined_scores, indent=2)

    prompt = f"""
    You are an expert training analyst.

    I have collected the average and maximum scores achieved across multiple minigames during training sessions.
    Return exactly these sections as second-level headings (##). Use short paragraphs (no bullet symbols). Do not include any introduction before the first heading.

    ## Performance Gaps 
    Which minigames have the largest gaps between average and max scores? What does this suggest about user challenges or skill ceilings.

    ## Near-Optimal Games
    Which minigames have averages close to their max? What might this indicate (e.g. game is easy, well-learned, or lacks depth).

    ## Consistency vs. Variability
    Do any minigames suggest high variability in performance (e.g. wide average-to-max gap with low average).

    ## Skill Mastery Trends
    What can you infer about skill progression or difficulty across the minigames.

    ## Recommendations
    Suggest actions based on your findings

    Data to analyze:
    {formatted_data}
    """

    if callable(client):
        # If client is a callable function (e.g., local LLM)
        insights_text = client(prompt)
    else:
        # API supports role-based messages
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        insights_text = response.choices[0].message.content

    cleaned_insights_avg_score = clear_formatting(insights_text)
    return cleaned_insights_avg_score


def clear_formatting(response):
    relevant_text = response
    relevant_text = re.sub(r"\*\*(.*?)\*\*", r"\1", relevant_text)
    relevant_text = re.sub(r"\*(.*?)\*", r"\1", relevant_text)
    relevant_text = relevant_text.strip()

    final_points = parse_llm_insights(relevant_text)
    return final_points



def parse_llm_insights(response_text):
    insights = []

    # First, try to match numbered points (existing behavior)
    numbered_pattern = r"(\d+\.\s+[^\n]+)([\s\S]*?)(?=\n\d+\.|\Z)"
    matches = re.findall(numbered_pattern, response_text)
    if matches:
        for title_line, content in matches:
            title = re.sub(r"^\d+\.\s+", "", title_line).strip()
            content = content.strip()
            insights.append({"title": title, "content": content})
        return insights

    # If no numbered points, try headings (##)
    heading_pattern = r"##\s*(.+?)(?=\n##|\Z)"
    matches = re.findall(heading_pattern, response_text, flags=re.DOTALL)
    if matches:
        for section in matches:
            # Split first line as title, rest as content
            lines = section.strip().split("\n", 1)
            title = lines[0].strip()
            content = lines[1].strip() if len(lines) > 1 else ""
            insights.append({"title": title, "content": content})
    return insights

