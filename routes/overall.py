from flask import Blueprint, render_template, request, jsonify
from analysis import overall_analysis as oa
from utils.context import get_llm_client

overall_bp = Blueprint("overall", __name__, template_folder="templates")


@overall_bp.route("/api/analysis/avg-scores")
def api_avg_scores_analysis():
    avg_scores, max_score_by_minigame = oa.get_avg_scores_for_practice_assessment()
    if not avg_scores:
        return jsonify([])

    text = oa.avg_scores_for_practice_assessment_analysis(
        avg_scores, max_score_by_minigame, get_llm_client()
    )
    return jsonify(text)


@overall_bp.route("/api/analysis/error-frequency")
def api_error_frequency_analysis():
    results = oa.get_error_frequency_results()
    if not results:
        return jsonify({"text": "No data found."})

    analysis_response = oa.error_frequency_analysis(results, get_llm_client())
    # text = oa.extract_relevant_text(analysis_response)
    return jsonify(analysis_response)


@overall_bp.route("/api/analysis/performance-duration")
def api_performance_duration_analysis():
    duration_data = oa.get_duration_vs_errors()
    if not duration_data:
        return jsonify({"text": "No session duration data available."})

    text = oa.performance_vs_duration(duration_data, get_llm_client())
    return jsonify(text)


@overall_bp.route("/api/analysis/overall-user")
def api_overall_user_analysis():
    results2 = oa.get_user_results()
    if not results2:
        return jsonify({"text": "No user data available."})

    text = oa.overall_user_analysis(results2, get_llm_client())
    return jsonify(text)


@overall_bp.route("/overall")
def overall():
    # Average Scores per Minigame
    avg_scores, max_score_by_minigame = oa.get_avg_scores_for_practice_assessment()

    avg_scores_analysis = "Loading..."

    labels = list(avg_scores.keys())
    avg_values = [avg_scores[label] for label in labels]
    max_values = [max_score_by_minigame.get(label, 0) for label in labels]

    avg_score_chart_data = {
        "labels": labels,
        "datasets": [
            {
                "label": "Average Score",
                "data": avg_values,
                "backgroundColor": "rgba(54, 162, 235, 0.6)",
            },
            {
                "label": "Max Score",
                "data": max_values,
                "backgroundColor": "rgba(255, 99, 132, 0.6)",
            },
        ],
    }

    # Error Frequency vs Results
    results = oa.get_error_frequency_results()
    if not results:
        analysis_text = "No data found."
        chart_data = {"labels": [], "datasets": []}
    else:
        analysis_text = "Loading..."
        # analysis_text = oa.extract_relevant_text(analysis_response)

        binned = oa.bin_errors_over_time(results, bin_size=5)
        time_bins = list(binned.keys())
        warnings = [binned[t]["warnings"] for t in time_bins]
        minors = [binned[t]["minors"] for t in time_bins]
        severes = [binned[t]["severes"] for t in time_bins]

        chart_data = {
            "labels": time_bins,
            "datasets": [
                {"label": "Warnings", "data": warnings, "borderColor": "orange"},
                {"label": "Minors", "data": minors, "borderColor": "green"},
                {"label": "Severes", "data": severes, "borderColor": "red"},
            ],
        }

    # Performance vs Duration Analysis
    duration_data = oa.get_duration_vs_errors()
    duration_analysis = "Loading..."

    scatter_chart_data = {
        "datasets": [
            {
                "label": "Score vs Session Duration",
                "data": [
                    {"x": entry["duration_minutes"], "y": entry["score"]}
                    for entry in duration_data
                ],
                "backgroundColor": "blue",
                "pointRadius": 4,
            }
        ]
    }

    # Overall User Performance
    results2 = oa.get_user_results()
    insights = "Loading..."

    return render_template(
        "overall.html",
        chart_data=chart_data,
        analysis=analysis_text,
        insights=insights,
        duration_analysis=duration_analysis,
        scatter_chart_data=scatter_chart_data,
        avg_score_chart_data=avg_score_chart_data,
        avg_scores_analysis=avg_scores_analysis,
    )
