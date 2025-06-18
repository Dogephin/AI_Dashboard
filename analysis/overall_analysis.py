from sqlalchemy import text
from db import engine
from collections import defaultdict
import json
import math
import re
import logging
from datetime import datetime
from sqlalchemy import bindparam 

logger = logging.getLogger(__name__)

# Error Frequency Over Time 
def get_error_frequency_results():
    query = text("SELECT results FROM PacMetaAOM.ima_plan_session_game_status")

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()

        results = [dict(row._mapping) for row in rows]
        logger.info(f"Fetched {len(results)} rows from the database.")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch results: {e}")
        return []

def bin_errors_over_time(results, bin_size=5):
    aggregated_bins = defaultdict(lambda: {'warnings': 0, 'minors': 0, 'severes': 0})
    max_time = 0

    for row in results:
        raw_json = row.get('results')
        if not raw_json:
            continue

        try:
            data = json.loads(raw_json)
        except Exception as e:
            logger.warning(f"Skipping invalid JSON: {e}")
            continue

        errors = data.get('errors', {})
        for err_type in ['warning', 'minor', 'severe']:
            for err in errors.get(err_type, []):
                t = err.get('time')
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
            aggregated_bins[bin_label] = {'warnings': 0, 'minors': 0, 'severes': 0}

    sorted_bins = dict(sorted(aggregated_bins.items(), key=lambda x: int(x[0].split('-')[0])))

    return sorted_bins

def error_frequency_analysis(results, client):
    binned_data = bin_errors_over_time(results, bin_size=5)
    binned_data_json = json.dumps(binned_data, indent=2)

    prompt_text = f"""
    I have aggregated the warning, minor and severe errors from multiple game sessions into 5-second time bins.
    The data below shows the count of warnings and minors occurring in each time interval over the entire session duration:

    {binned_data_json}

    Please provide a clear, concise analysis of this error frequency data, including:
    - When errors tend to spike (which time bins have highest counts).
    - Whether warnings or minors tend to cluster early, mid, or late in sessions.
    - Provide recommendations if possible.

    Please keep it as short and concise with clear titles.
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a data analyst."},
            {"role": "user", "content": prompt_text}
        ]
    )

    analysis_response = response.choices[0].message.content
    logger.info("Received analysis from LLM")
    return analysis_response

def extract_relevant_text(analysis_response):
    match = re.search(r'(#### \*\*1\..*?)(?=#### \*\*Summary|\Z)', analysis_response, re.DOTALL)
    if not match:
        return "No insights available."

    relevant_text = match.group(1)
    relevant_text = re.sub(r'#+\s*', '', relevant_text)  # Remove markdown headers
    relevant_text = re.sub(r'\*\*(.*?)\*\*', r'\1', relevant_text)  # Remove bold formatting
    relevant_text = relevant_text.strip()

    return relevant_text

# Overall User Analysis
def get_user_results():
    query = text("SELECT User_ID , results FROM PacMetaAOM.ima_plan_session ORDER BY User_ID")

    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()

        results2 = [dict(row._mapping) for row in rows]
        logger.info(f"Fetched {len(results2)} rows from the database.")
        return results2
    except Exception as e:
        logger.error(f"Failed to fetch results: {e}")
        return []
    
def overall_user_analysis(results2, client): 
    prompt_text = f"""
    I have collected the overall data of all users. Here is the data:

    {results2}

    Can you analyze this data and provide the analysis and insights. Please focus
    on overall user analysis for everyone instead of individuals.

    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a data analyst."},
            {"role": "user", "content": prompt_text}
        ]
    )
    
    user_analysis = response.choices[0].message.content
    return user_analysis

def extract_points_only(user_analysis):
    match = re.search(r"(### 1\..*?)(?=### Recommendations|$)", user_analysis, re.DOTALL)
    
    if not match:
        return "No key insights found."

    good_info = match.group(1)
    # Clean markdown formatting
    good_info = re.sub(r'#+\s*', '', good_info)  # Remove heading markers like ###, ####
    good_info = re.sub(r'\*\*(.*?)\*\*', r'\1', good_info)  # Remove bold formatting
    return good_info.strip()

# Session Duration vs Performance
def get_duration_vs_errors():
    query = text("""
        SELECT game_start, game_end, score 
        FROM PacMetaAOM.ima_plan_session_game_status
        WHERE game_start IS NOT NULL AND game_end IS NOT NULL AND score IS NOT NULL
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
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
                duration_score_data.append({
                    "duration_minutes": duration_minutes,
                    "score": score
                })
        except Exception as e:
            logger.warning(f"Skipping row due to error: {e}")
            continue

    return duration_score_data


def performance_vs_duration(data, client):
    json_data = json.dumps(data, indent=2)

    prompt = f"""
    Below is training session data showing session duration (in minutes) and the score achieved:

    {json_data}

    Please analyze:
    - Is there a relationship between session duration and score?
    - Do longer sessions lead to higher scores?
    - What is the ideal session length range, if observable?

    Provide concise analysis with bullet points or numbered insights.
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a data analyst."},
            {"role": "user", "content": prompt}
        ]
    )
    insights_text = response.choices[0].message.content
    cleaned_insights_avg_score = clear_formatting(insights_text)
    return cleaned_insights_avg_score

# Average Scores for all Minigames
def get_practice_assessment_rows():
    query = text("""
        SELECT Session_ID, Results
        FROM PacMetaAOM.ima_plan_session
        WHERE Results LIKE '%Practice%'
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()

        sessions = [dict(row._mapping) for row in rows]
        if sessions:
            print(f"[DEBUG] First 5 Session IDs: {[s['Session_ID'] for s in sessions[:5]]}")

        session_ids = [s["Session_ID"] for s in sessions]
        scores = get_scores_for_sessions(session_ids)

        print(f"[INFO] Retrieved {len(scores)} matching score entries.")

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

    query = text("""
        SELECT Session_ID, score, results
        FROM PacMetaAOM.ima_plan_session_game_status
        WHERE Session_ID IN :session_ids
    """).bindparams(bindparam("session_ids", expanding=True))

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"session_ids": session_ids})
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
    print(f"[INFO] Processing {len(scores_rows)} score rows for average calculation...")

    for row in scores_rows:
        try:
            # Load JSON from string field
            data = json.loads(row['results'])

            raw_name = data.get('level_name') or data.get('game', '')

            cleaned_name = re.sub(r'<.*?>', '', raw_name).strip()

            # Match pattern like "MG1 Practice", "MG2 Assessment"
            match = re.match(r'(MG\d+\s+(?:Practice))', cleaned_name)
            game_key = match.group(1) if match else cleaned_name

            score = row.get('score')
            max_score = data.get('max-score') or data.get('max_score')

            if score is not None:
                scores_by_minigame[game_key].append(score)
            
            if game_key not in max_score_by_minigame and max_score is not None:
                max_score_by_minigame[game_key] = max_score

        except Exception as e:
            print(f"[WARN] Skipping row due to error: {e}")

    # Compute averages
    avg_scores = {
        game: sum(scores) / len(scores) if scores else 0
        for game, scores in scores_by_minigame.items()
    }

    print(f"[INFO] Calculated average scores for {len(avg_scores)} minigames.")
    print(f"[DEBUG] Example averages: {dict(list(avg_scores.items())[:3])}")
    return avg_scores, max_score_by_minigame


def get_avg_scores_for_practice_assessment():
    print("[INFO] Starting average score computation for practice & assessment only.")
    sessions = get_practice_assessment_rows()
    session_ids = [s['Session_ID'] for s in sessions]

    scores_rows = get_scores_for_sessions(session_ids)
    avg_scores, max_score_by_minigame = calculate_avg_score_per_minigame(scores_rows)

    print(f"[RESULT] Final average scores: {avg_scores, max_score_by_minigame}")
    return avg_scores, max_score_by_minigame

def avg_scores_for_practice_assessment_analysis(avg_scores, max_score_by_minigame, client):
    combined_scores = {
        game: {
            "average_score": round(avg_scores.get(game, 0), 2),
            "max_score": max_score_by_minigame.get(game, 0)
        }
        for game in avg_scores
    }

    formatted_data = json.dumps(combined_scores, indent=2)

    prompt = f"""
    I have collected the average and maximum scores achieved across multiple minigames during training sessions.

    Each minigame has an average score based on all user sessions, and a max score representing the best possible performance.

    Here is the data:
    
    {formatted_data}

    Please analyze the following:
    - Which minigames have the largest gaps between average and max scores?
    - What might that suggest about difficulty or user performance?
    - Are there any games where performance is very close to the max score?
    - Provide clear, concise insights or bullet points that help stakeholders understand where users perform well or struggle.

    Format the response as a list of insights.
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a data analyst."},
            {"role": "user", "content": prompt}
        ]
    )

    insights_text = response.choices[0].message.content
    cleaned_insights_avg_score = clear_formatting(insights_text)
    return cleaned_insights_avg_score

def clear_formatting(response):
    relevant_text = response  

    # Clean markdown headers like ### or ####
    relevant_text = re.sub(r'#+\s*', '', relevant_text)

    # Remove bold formatting **bold**
    relevant_text = re.sub(r'\*\*(.*?)\*\*', r'\1', relevant_text)

    # Optionally remove italic formatting *italic*
    relevant_text = re.sub(r'\*(.*?)\*', r'\1', relevant_text)

    # Trim whitespace
    relevant_text = relevant_text.strip()

    return relevant_text