from flask import Blueprint, render_template, request, jsonify
from analysis import overall_analysis as oa
from utils.context import get_llm_client
from utils.cache import generate_cache_key, cache
from utils.auth import login_required


overall_bp = Blueprint("overall", __name__, template_folder="templates")


@overall_bp.route("/api/analysis/avg-scores")
@login_required
def api_avg_scores_analysis():
    start_month = request.args.get("start_month")
    end_month = request.args.get("end_month")
    avg_scores, max_score_by_minigame = oa.get_avg_scores_for_practice_assessment(start_month=start_month, end_month=end_month)
    if not avg_scores:
        return jsonify([])

    # Cache the average scores analysis
    key = generate_cache_key(
        "avg_scores_analysis",
        {"avg_scores": avg_scores, "max_score_by_minigame": max_score_by_minigame},
    )

    # Check for force refresh (bypass cache)
    force_refresh = request.args.get("force_refresh", "false").lower() == "true"
    avg_scores_analysis_response = None if force_refresh else cache.get(key)

    if not avg_scores_analysis_response:
        avg_scores_analysis_response = oa.avg_scores_for_practice_assessment_analysis(
            avg_scores, max_score_by_minigame, get_llm_client()
        )
        cache.set(key, avg_scores_analysis_response)

    return jsonify(avg_scores_analysis_response)


@overall_bp.route("/api/analysis/error-frequency")
@login_required
def api_error_frequency_analysis():
    start_month = request.args.get("start_month")
    end_month = request.args.get("end_month")
    # print(f"[DEBUG] Start Month and End Month Specific: {start_month, end_month}", flush=True)
    results = oa.get_error_frequency_results(start_month=start_month, end_month=end_month)
    # print(f"[DEBUG] /api/analysis/error-frequency results length: {len(results) if results else 0}", flush=True)
    if not results:
        return jsonify({"text": "No data found."})

    # Cache the error frequency analysis
    key = generate_cache_key("error_frequency_analysis", {"results": results})

    # Check for force refresh (bypass cache)
    force_refresh = request.args.get("force_refresh", "false").lower() == "true"
    error_frequency_analysis_response = None if force_refresh else cache.get(key)

    if not error_frequency_analysis_response:
        error_frequency_analysis_response = oa.error_frequency_analysis(
            results, get_llm_client()
        )
        cache.set(key, error_frequency_analysis_response)

    return jsonify(error_frequency_analysis_response)


@overall_bp.route("/api/analysis/performance-duration")
@login_required
def api_performance_duration_analysis():
    start_month = request.args.get("start_month")
    end_month = request.args.get("end_month")
    # print(f"[DEBUG] Start Month and End Month Specific Perf vs Dura: {start_month, end_month}", flush=True)
    duration_data = oa.get_duration_vs_errors(start_month=start_month, end_month=end_month)
    if not duration_data:
        return jsonify({"text": "No session duration data available."})

    # Cache the performance duration analysis
    key = generate_cache_key(
        "performance_duration_analysis", {"duration_data": duration_data}
    )

    # Check for force refresh (bypass cache)
    force_refresh = request.args.get("force_refresh", "false").lower() == "true"
    performance_duration_analysis_response = None if force_refresh else cache.get(key)

    if not performance_duration_analysis_response:
        performance_duration_analysis_response = oa.performance_vs_duration(
            duration_data, get_llm_client()
        )
        cache.set(key, performance_duration_analysis_response)

    return jsonify(performance_duration_analysis_response)


@overall_bp.route("/api/analysis/overall-user")
@login_required
def api_overall_user_analysis():
    results2 = oa.get_user_results()
    if not results2:
        return jsonify({"text": "No user data available."})

    # Cache the overall user analysis
    key = generate_cache_key("overall_user_analysis", {"results": results2})

    # Check for force refresh (bypass cache)
    force_refresh = request.args.get("force_refresh", "false").lower() == "true"
    overall_user_analysis_response = None if force_refresh else cache.get(key)

    if not overall_user_analysis_response:
        overall_user_analysis_response = oa.overall_user_analysis(
            results2, get_llm_client()
        )
        cache.set(key, overall_user_analysis_response)

    return jsonify(overall_user_analysis_response)

# -- Error vs Completion Time Analysis --
@overall_bp.route("/api/analysis/error-completion")
@login_required
def api_error_completion_analysis():
    start_month = request.args.get("start_month")
    end_month = request.args.get("end_month")
    duration_vs_errors = oa.get_error_type_vs_score(start_month=start_month, end_month=end_month) 
    if not duration_vs_errors:
        return jsonify({"text": "No error vs completion data available."})

    # Cache key
    key = generate_cache_key("error_completion_analysis", {"data": duration_vs_errors})

    force_refresh = request.args.get("force_refresh", "false").lower() == "true"
    error_completion_analysis_response = None if force_refresh else cache.get(key)

    if not error_completion_analysis_response:
        # Call the analysis function for error vs completion
        error_completion_analysis_response = oa.error_type_vs_score_analysis(
            duration_vs_errors, get_llm_client()
        )
        cache.set(key, error_completion_analysis_response)

    return jsonify(error_completion_analysis_response)

# -- Students Improvements --
@overall_bp.route("/api/analysis/students-improvement")
@login_required
def api_students_improvement_analysis():
    start_month = request.args.get("start_month")
    end_month = request.args.get("end_month")
    student_improvement = oa.get_monthly_avg_scores_by_minigame(start_month=start_month, end_month=end_month) 
    if not student_improvement:
        return jsonify({"text": "No error vs completion data available."})

    # Cache key
    key = generate_cache_key("student_improvement", {"data": student_improvement})

    force_refresh = request.args.get("force_refresh", "false").lower() == "true"
    student_improvement_analysis_response = None if force_refresh else cache.get(key)

    if not student_improvement_analysis_response:
        # Call the analysis function for error vs completion
        student_improvement_analysis_response = oa.trend_analysis_daily_scores(
            student_improvement, get_llm_client()
        )
        cache.set(key, student_improvement_analysis_response)

    return jsonify(student_improvement_analysis_response)


@overall_bp.route("/overall")
@login_required
def overall():
    start_month = request.args.get("start_month")
    end_month = request.args.get("end_month")      
    print(f"[DEBUG] Start Month and End Month Overall: {start_month, end_month}", flush=True)

    # Average Scores per Minigame
    avg_scores, max_score_by_minigame = oa.get_avg_scores_for_practice_assessment(start_month=start_month, end_month=end_month)
    print(f"[DEBUG] /overall avg score results length: {len(avg_scores) if avg_scores else 0}")

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
    results = oa.get_error_frequency_results(start_month=start_month, end_month=end_month)
    print(f"[DEBUG] /overall results length: {len(results) if results else 0}")
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
    duration_data = oa.get_duration_vs_errors(start_month=start_month, end_month=end_month)
    print(f"[DEBUG] /overall results length perf vs dura: {len(results) if results else 0}")
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

    # Error vs Completion Time Chart Data
    error_vs_completion_data_rows = oa.get_error_type_vs_score(start_month=start_month, end_month=end_month)
    error_vs_completion_chart_data = {
        "datasets": [
            {
                "label": "Errors vs Completion Time",
                "data": [
                    {"x": row["total_time"], "y": row.get("total_errors", 0)}
                    for row in error_vs_completion_data_rows
                ],
                "backgroundColor": "purple",
                "pointRadius": 4
            }
        ]
    }

    # --- Student Improvements Monthly ---
    student_improvement_data = oa.get_monthly_avg_scores_by_minigame(
        start_month=start_month, end_month=end_month
    )

    # Collect all unique months across all minigames
    all_months = sorted(
        {entry["month"] for game_data in student_improvement_data.values() for entry in game_data}
    )

    datasets = []
    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#1a1818", "#9467bd", 
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
        "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173"
    ]

    for i, (minigame, game_data) in enumerate(student_improvement_data.items()):
        month_to_avg = {entry["month"]: entry["average_score"] for entry in game_data}
        data_points = [month_to_avg.get(month, None) for month in all_months]  # align with labels

        datasets.append({
            "label": minigame,
            "data": data_points,
            "borderColor": colors[i % len(colors)],
            "backgroundColor": colors[i % len(colors)],
            "fill": False,
            "tension": 0.2,
            "pointRadius": 3
        })

    student_improvement_chart_data = {
        "labels": all_months,
        "datasets": datasets 
    }

    # Overall User Performance
    results2 = oa.get_user_results()
    insights = "Loading..."

    return render_template(
        "overall.html",
        header_title="Game Analysis Dashboard - Overall",
        chart_data=chart_data,
        analysis=analysis_text,
        insights=insights,
        duration_analysis=duration_analysis,
        scatter_chart_data=scatter_chart_data,
        avg_score_chart_data=avg_score_chart_data,
        avg_scores_analysis=avg_scores_analysis,
        error_vs_completion_chart_data=error_vs_completion_chart_data,
        studentImprovementChartData=student_improvement_chart_data,
    )
