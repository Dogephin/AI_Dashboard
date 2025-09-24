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
from datetime import datetime

logger = logging.getLogger(__name__)

# -- Error Frequency Over Time --
def get_error_frequency_results(start_month=None, end_month=None):
    # print(f"[DEBUG] get_error_frequency_results called with: start_month={start_month}, end_month={end_month}")
    role = session.get("role")  
    user_id = session.get("user_id")

    start_dt, end_dt = parse_month_range(start_month, end_month)

    print(f"[DEBUG] Parsed dates: start_dt={start_dt}, end_dt={end_dt}, {user_id}")

    if role == "teacher":
        query_text = """
            SELECT IPSGS.Results, IPSGS.Game_Start
            FROM IMA_Plan_Session_Game_Status IPSGS
            INNER JOIN IMA_Plan_Session IPS ON IPSGS.Session_ID = IPS.Session_ID
            INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
            WHERE IAU.Admin_ID = :user_id
        """
        params = {"user_id": user_id}
    else:
        query_text = """
            SELECT IPSGS.Results, IPSGS.Game_Start
            FROM IMA_Plan_Session_Game_Status IPSGS
            WHERE 1=1
        """
        params = {}

    # Add date filtering
    if start_dt:
        query_text += " AND IPSGS.Game_Start >= :start_dt"
        params["start_dt"] = start_dt
    if end_dt:
        query_text += " AND IPSGS.Game_Start <= :end_dt"
        params["end_dt"] = end_dt


    query = text(query_text)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, params)
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
        raw_json = row.get("Results") or row.get("results")
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
    Explain whether certain error types cluster early, mid, or late in sessions. Highlight differences between warnings, minor, and severe errors.

    ## Error Co-occurrence Patterns
    Describe if certain types of errors tend to happen together within the same time bins or sequence in the session.

    ## Severity Impact
    Analyze whether severe errors contribute disproportionately to overall session difficulty or completion time compared to warnings and minor errors.

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
def get_duration_vs_errors(start_month=None, end_month=None):
    role = session.get("role")  
    user_id = session.get("user_id")
    start_dt, end_dt = parse_month_range(start_month, end_month)

    # Start with a string, not text()
    if role == "teacher":
        query_text = """
            SELECT IPSGS.Game_Start AS game_start,
                   IPSGS.Game_End AS game_end,
                   IPSGS.Score AS score
            FROM IMA_Plan_Session_Game_Status IPSGS
            INNER JOIN IMA_Plan_Session IPS ON IPSGS.Session_ID = IPS.Session_ID
            INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
            WHERE IAU.Admin_ID = :user_id
              AND IPSGS.Game_Start IS NOT NULL
              AND IPSGS.Game_End IS NOT NULL
              AND IPSGS.Score IS NOT NULL
        """
        params = {"user_id": user_id}
    else:
        query_text = """
            SELECT Game_Start AS game_start,
                   Game_End AS game_end,
                   Score AS score
            FROM IMA_Plan_Session_Game_Status
            WHERE Game_Start IS NOT NULL
              AND Game_End IS NOT NULL
              AND Score IS NOT NULL
        """
        params = {}

    # Add date filters (still strings)
    if start_dt:
        query_text += " AND IPSGS.Game_Start >= :start_dt" if role == "teacher" else " AND Game_Start >= :start_dt"
        params["start_dt"] = start_dt
    if end_dt:
        query_text += " AND IPSGS.Game_Start <= :end_dt" if role == "teacher" else " AND Game_End <= :end_dt"
        params["end_dt"] = end_dt

    # Only convert to TextClause here
    query = text(query_text)

    try:
        with engine.connect() as conn:
            result = conn.execute(query , params)
            rows = result.fetchall()
            logger.info(f"Fetched {len(rows)} rows for perf vs dura analysis.")
            if rows:
                logger.debug(f"[DEBUG] First row sample (duration): {dict(rows[0]._mapping)}")
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return []

    duration_score_data = []
    for row in rows:
        try:
            row_data = row._mapping
            start = row_data["game_start"]
            end = row_data["game_end"]
            score = int(row_data["score"])
            duration_minutes = round((end - start).total_seconds() / 60.0, 2)
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

    ## Outliers and Extremes
    Identify sessions with unusually high or low scores relative to duration. Suggest possible reasons for these outliers.

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
def get_practice_assessment_rows(start_month=None, end_month=None):
    print(f"[DEBUG] get_practice_assessment_rows called with: start_month={start_month}, end_month={end_month}")
    role = session.get("role")  
    user_id = session.get("user_id")

    start_dt, end_dt = parse_month_range(start_month, end_month)

    if role == "teacher":
        query_text = """
            SELECT IPS.Session_ID, IPS.Results, IPS.Session_Start
            FROM IMA_Plan_Session IPS
            INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
            WHERE IAU.Admin_ID = :user_id
            AND (IPS.Results LIKE '%Practice%' OR IPS.Results LIKE '%Training%')
        """
        params = {"user_id": user_id}

    else:
        query_text = """
            SELECT IPS.Session_ID, IPS.Results, IPS.Session_Start
            FROM IMA_Plan_Session IPS
            WHERE (Results LIKE '%Practice%' OR Results LIKE '%Training%')
        """
        params = {}
    
    # Add date filtering
    if start_dt:
        query_text += " AND IPS.Session_Start >= :start_dt"
        params["start_dt"] = start_dt
    if end_dt:
        query_text += " AND IPS.Session_Start <= :end_dt"
        params["end_dt"] = end_dt

    query = text(query_text)

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

            match = re.match(r"(MG\d+\s+(?:Practice|Training))", cleaned_name, re.IGNORECASE)
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


def get_avg_scores_for_practice_assessment(start_month=None, end_month=None):
    sessions = get_practice_assessment_rows(start_month, end_month)
    session_ids = [s["Session_ID"] for s in sessions]

    scores_rows = get_scores_for_sessions(session_ids)
    avg_scores, max_score_by_minigame = calculate_avg_score_per_minigame(scores_rows)

    return avg_scores, max_score_by_minigame


def avg_scores_for_practice_assessment_analysis(
    avg_scores, max_score_by_minigame, client
):
    combined_scores = [
        {"game": game,
        "average_score": round(avg_scores.get(game, 0), 2),
        "max_score": max_score_by_minigame.get(game, 0)}
        for game in avg_scores
    ]

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

# -- Total Error vs Completion Time --
def get_error_type_vs_score(start_month=None, end_month=None):
    role = session.get("role")
    user_id = session.get("user_id")
    start_dt, end_dt = parse_month_range(start_month, end_month)
    
    if role == "teacher":
        query_text = """
            SELECT IPSGS.results, IPSGS.Game_Start
            FROM IMA_Plan_Session_Game_Status IPSGS
            INNER JOIN IMA_Plan_Session IPS ON IPSGS.Session_ID = IPS.Session_ID
            INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
            WHERE IAU.Admin_ID = :user_id
            AND IPSGS.score IS NOT NULL
        """
        params = {"user_id": user_id}
    else:
        query_text = """SELECT IPSGS.Results AS results, IPSGS.Game_Start
            FROM IMA_Plan_Session_Game_Status IPSGS
            WHERE IPSGS.Score IS NOT NULL"""
        params = {}

    if start_dt:
        query_text += " AND IPSGS.Game_Start >= :start_dt"
        params["start_dt"] = start_dt
    if end_dt:
        query_text += " AND IPSGS.Game_Start <= :end_dt"
        params["end_dt"] = end_dt
    
    query = text(query_text)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch error vs score data: {e}")
        return []

    error_score_data = []
    for row in rows:
        try:
            data = json.loads(row.results)
            errors = data.get("errors", {})

            # Sum all errors for this session
            total_errors = sum(len(errors.get(err_type, [])) for err_type in ["warning", "minor", "severe"])

            # Keep the breakdown if needed for analysis
            error_counts = {
                "warnings": len(errors.get("warning", [])),
                "minors": len(errors.get("minor", [])),
                "severes": len(errors.get("severe", []))
            }

            total_time_for_session = data.get("total-time", None)
            error_score_data.append({
                "errors": error_counts,       # breakdown for analysis
                "total_errors": total_errors, # summed for plotting
                "total_time": total_time_for_session
            })
        except Exception as e:
            logger.warning(f"Skipping row due to JSON or score error: {e}")
            continue

    return error_score_data

def error_type_vs_score_analysis(data, client):
    json_data = json.dumps(data, indent=2)
    prompt = f"""
    You are an expert training analyst.

    I have aggregated session data with the total number of errors (sum of warnings, minor, and severe) and the completion time in each session.
    Return exactly these sections as second-level headings (##). Use short paragraphs (no bullet symbols). Do not include any introduction before the first heading.

    ## Error Impact
    Identify whether session duration results in fewer errors.

    ## Severity Analysis
    Compare the impact of different error types (warnings, minor, severe) on session completion time. Highlight which error types are most disruptive.

    ## Co-occurrence Patterns
    Identify if certain error types tend to occur together and whether these patterns affect completion time.

    ## Patterns
    Describe patterns where certain error types occur together and their effect on completion time.

    ## Recommendations
    Suggest interventions to reduce high-impact errors and help users complete sessions more efficiently.

    Data to analyze:
    {json_data}
    """

    if callable(client):
        insights_text = client(prompt)
    else:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        insights_text = response.choices[0].message.content

    cleaned_insights = clear_formatting(insights_text)
    return cleaned_insights


# Calculate Student Improvements
def get_monthly_avg_scores_by_minigame(start_month=None, end_month=None):
    role = session.get("role")
    user_id = session.get("user_id")
    start_dt, end_dt = parse_month_range(start_month, end_month)

    # --- SQL query ---
    if role == "teacher":
        query_text = """
            SELECT IPSGS.Game_Start, IPSGS.Results
            FROM IMA_Plan_Session_Game_Status IPSGS
            INNER JOIN IMA_Plan_Session IPS 
                ON IPSGS.Session_ID = IPS.Session_ID
            INNER JOIN IMA_Admin_User IAU 
                ON IPS.User_ID = IAU.User_ID
            WHERE IAU.Admin_ID = :user_id
              AND (IPS.Results LIKE '%Practice%' OR IPS.Results LIKE '%Training%' OR IPS.Results LIKE '%Assessment%')
        """
        params = {"user_id": user_id}
    else:
        query_text = """
            SELECT IPSGS.Game_Start, IPSGS.Results
            FROM IMA_Plan_Session_Game_Status IPSGS
            INNER JOIN IMA_Plan_Session IPS 
                ON IPSGS.Session_ID = IPS.Session_ID
            WHERE (IPS.Results LIKE '%Practice%' OR IPS.Results LIKE '%Training%' OR IPS.Results LIKE '%Assessment%')
        """
        params = {}

    # Date filters
    if start_dt:
        query_text += " AND IPSGS.Game_Start >= :start_dt"
        params["start_dt"] = start_dt
    if end_dt:
        query_text += " AND IPSGS.Game_Start <= :end_dt"
        params["end_dt"] = end_dt

    query = text(query_text)

    # --- Fetch rows ---
    with engine.connect() as conn:
        rows = [dict(row._mapping) for row in conn.execute(query, params).fetchall()]

    # --- Aggregate: scores by minigame + month ---
    scores_by_game_month = defaultdict(list)

    for row in rows:
        try:
            data = json.loads(row["Results"])
            score = data.get("final-score")
            level_name = data.get("level_name", "")

            # Strip Game Name
            minigame_match = re.match(r"^(MG\d+\s+(Training|Practice))<br>", level_name)
            if minigame_match:
                minigame = minigame_match.group(1)
            elif level_name == "Assessment":
                minigame = "Assessment"
            else:
                minigame = None

            if score is None or not minigame:
                continue

            month_key = row["Game_Start"].strftime("%Y-%m")
            scores_by_game_month[(minigame, month_key)].append(score)
        except Exception as e:
            print(f"Error parsing row: {e}", flush=True)
            continue

    # --- Compute averages ---
    results = defaultdict(list)
    for (minigame, month_key), scores in scores_by_game_month.items():
        avg_score = sum(scores) / len(scores)
        results[minigame].append({"month": month_key, "average_score": avg_score})

    # --- Sort months for each minigame ---
    for minigame in results:
        results[minigame] = sorted(results[minigame], key=lambda x: x["month"])

    return results

def trend_analysis_daily_scores(daily_avg_scores, client):
    import json
    data_json = json.dumps(daily_avg_scores, indent=2)

    prompt = f"""
    You are an expert training analyst.

    I have collected the monthly average scores of students over the past month for different minigames.
    Each object has keys: "date" and "average_score".

    Return exactly these sections as second-level headings (##). Use short paragraphs (no bullet symbols). Do not include any introduction before the first heading.

    ## Trend Line
    Describe whether the scores are increasing, plateauing, or declining over the month. Identify general trends or anomalies.

    ## Minigame Comparison
    Highlight any differences in performance trends between minigames. Identify which minigames students perform best or struggle most with.

    ## Interpretation
    Explain what this trend suggests about student improvement. Are they sustaining growth, plateauing, or showing inconsistent performance?

    ## Anomalies and Recommendations
    If there are sudden drops or spikes in scores, suggest possible reasons (e.g., difficulty of minigame, engagement issues) and provide actionable recommendations to improve student performance.

    Data to analyze:
    {data_json}
    """

    if callable(client):
        insights_text = client(prompt)
    else:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        insights_text = response.choices[0].message.content

    return clear_formatting(insights_text)

def get_student_game_results(start_month=None, end_month=None):
    role = session.get("role")
    user_id = session.get("user_id")
    
    start_dt, end_dt = parse_month_range(start_month, end_month)

    # Build query
    if role == "teacher":
        query_text = """
            SELECT IPSGS.Results AS results,
                   IPSGS.Game_Start AS game_start,
                   IPS.User_ID,
                   A.username
            FROM IMA_Plan_Session_Game_Status IPSGS
            INNER JOIN IMA_Plan_Session IPS ON IPSGS.Session_ID = IPS.Session_ID
            INNER JOIN IMA_Admin_User IAU ON IPS.User_ID = IAU.User_ID
            INNER JOIN Account A ON IPS.User_ID = A.Id
            WHERE IAU.Admin_ID = :user_id
        """
        params = {"user_id": user_id}
    else:
        query_text = """
            SELECT IPSGS.Results AS results,
                   IPSGS.Game_Start AS game_start,
                   IPS.User_ID,
                   A.username
            FROM IMA_Plan_Session_Game_Status IPSGS
            INNER JOIN IMA_Plan_Session IPS ON IPSGS.Session_ID = IPS.Session_ID
            INNER JOIN Account A ON IPS.User_ID = A.Id
            WHERE 1=1
        """
        params = {}

    if start_dt:
        query_text += " AND IPSGS.Game_Start >= :start_dt"
        params["start_dt"] = start_dt
    if end_dt:
        query_text += " AND IPSGS.Game_Start <= :end_dt"
        params["end_dt"] = end_dt

    query = text(query_text)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, params)
            rows = [dict(row._mapping) for row in result.fetchall()]
    except Exception as e:
        print(f"[ERROR] Failed to fetch student game results: {e}")
        return {"raw": [], "top": [], "bottom": [], "top_rows": [], "bottom_rows": []}

    # Track performance and completion
    performance = defaultdict(list)
    completion_counts = defaultdict(lambda: {"completed": 0, "total": 0})

    for row in rows:
        try:
            result_data = json.loads(row["results"])
            score = result_data.get("final-score", 0)
            performance[row["username"]].append(score)

            status = result_data.get("status", "").lower()
            completion_counts[row["username"]]["total"] += 1
            if status == "complete":
                completion_counts[row["username"]]["completed"] += 1
        except Exception:
            continue

    # Weighted average calculation
    all_scores = [score for scores in performance.values() for score in scores]
    global_avg = sum(all_scores) / len(all_scores) if all_scores else 0
    k = 3  # Confidence weight in a single game's information of being accurate

    weighted_scores = {}
    for u, scores in performance.items():
        n = len(scores)
        if n > 0:
            # Use Bayesian Average which balances two competing feature
            # Formula for Bayesian Average
            # WeightedAvg = [sum(scores) + k * global average score across all students] / no. of games the student played + k
            weighted_avg = (sum(scores) + global_avg * k) / (n + k)
            weighted_scores[u] = weighted_avg

    sorted_students = sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True)

    top_usernames = {u for u, _ in sorted_students[:3]}
    bottom_usernames = {u for u, _ in sorted_students[-3:]}

    def simplify_rows(rows_list):
        simplified = []
        for r in rows_list:
            try:
                results_data = json.loads(r.get("results", "{}"))
            except Exception:
                results_data = {}
            counts = completion_counts[r["username"]]
            simplified.append({
                "username": r["username"],
                "completion_rate": round(counts["completed"]/counts["total"]*100, 2) if counts["total"]>0 else 0,
                "games_played": counts["total"],
                "status": results_data.get("status", ""),
                "accuracy": results_data.get("accuracy", 0),
                "total_time": results_data.get("total-time", 0)
            })
        return simplified

    top_rows = simplify_rows([r for r in rows if r["username"] in top_usernames])
    bottom_rows = simplify_rows([r for r in rows if r["username"] in bottom_usernames])

    return {
        "top": sorted_students[:3],
        "bottom": sorted_students[-3:],
        "top_rows": top_rows,
        "bottom_rows": bottom_rows
    }


def top_vs_bottom_analysis(student_data, client):
    """
    Analyze top vs bottom students using AI, safely handling datetime objects.
    Assumes student_data rows are already simplified with key fields.
    """

    def default_serializer(o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"Type {type(o)} not serializable")

    # Use the rows as-is; no further parsing needed
    top_summary = student_data.get("top", [])
    bottom_summary = student_data.get("bottom", [])
    top_rows = student_data.get("top_rows", [])
    bottom_rows = student_data.get("bottom_rows", [])

    # Prepare JSON payload for AI
    analysis_payload = {
        "top_summary": top_summary,
        "bottom_summary": bottom_summary,
        "top_rows": top_rows,
        "bottom_rows": bottom_rows
    }

    json_data = json.dumps(analysis_payload, indent=2, default=default_serializer)

    # Construct AI prompt
    prompt = f"""
    You are an expert training analyst.

    I have aggregated data on student performance from training sessions. Focus specifically on the top performers and bottom performers. 
    Top and bottom summaries contain usernames and average scores. Detailed rows contain completion_rate, games_played, status, accuracy, and total_time for each game.

    Return exactly these sections as second-level headings (##). Use short paragraphs, no bullet points, and avoid introducing the analysis before the first heading. Only use normal sentences in short paragraphs.

    ## Performance Overview
    Compare the top performers versus the bottom performers. Highlight key differences in scores, completion rates, and consistency.

    ## Strengths of Top Performers
    Describe patterns or behaviors that may explain why these students perform well. Mention completion rates, score distribution, or any notable trends.

    ## Challenges of Bottom Performers
    Explain possible reasons for lower performance. Highlight trends, low completion rates, or specific games where students struggled.

    ## Actionable Recommendations
    Suggest targeted interventions or strategies to help lower performers improve and to maintain or further enhance top performers’ results.

    Data to analyze (JSON):
    {json_data}
    """

    # Send prompt to AI
    if callable(client):
        insights_text = client(prompt)
    else:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        insights_text = response.choices[0].message.content

    return clear_formatting(insights_text)

def personalised_feedback_analysis(student_row, client):    
    prompt = f"""
    You are an expert training analyst.

    Analyze the following student's performance data which contains usernames and average scores. Detailed rows contain completion_rate, games_played, status, accuracy, and total_time for each gameand provide feedback.

    Data:
    {json.dumps(student_row, indent=2)}

    Return exactly these sections as second-level headings (##). Use short paragraphs, no bullet points, and avoid introducing the analysis before the first heading.

    ## Personalized Recommendation
    Write short, practical guidance on how this student can improve.

    ## Motivational Strategies
    Suggest encouragement or adaptive support strategies for this student.

    ## Actions Teacher's Can Take
    Suggest motivational strategies that can help support this student.
    """

    # Send prompt to AI
    if callable(client):
        feedback = client(prompt)
    else:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a supportive student coach."},
                {"role": "user", "content": prompt},
            ],
        )
        feedback = response.choices[0].message.content

    return clear_formatting(feedback)

    
def parse_month_range(start_month, end_month):
    """
    Convert 'YYYY-MM' strings into datetime objects for filtering.
    """
    start_dt = None
    end_dt = None

    if start_month:
        # First day of the start month
        start_dt = datetime.strptime(start_month, "%Y-%m")
    if end_month:
        # Last day of the end month
        end_dt = datetime.strptime(end_month, "%Y-%m")
        # Move to the next month and subtract 1 second to get last moment of the month
        from calendar import monthrange
        last_day = monthrange(end_dt.year, end_dt.month)[1]
        end_dt = end_dt.replace(day=last_day, hour=23, minute=59, second=59)

    return start_dt, end_dt

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

