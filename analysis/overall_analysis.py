from sqlalchemy import text
from db import engine
from collections import defaultdict
import json
import math
import re
import logging

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

    Can you analyze this data and provide the analysis and insights

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
