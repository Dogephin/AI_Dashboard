from flask import Flask, request, render_template, jsonify
from llm import create_llm_client
from db import test_db_connection
from analysis import overall_analysis as oa
from analysis import user_analysis as ua
from analysis import minigames_analysis as mg
import logging
import json
import datetime

app = Flask(__name__)

test_db_connection()
llm_client = create_llm_client()

logging.basicConfig(
    level=logging.INFO,  # or DEBUG for more detail
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/analysis/avg-scores")
def api_avg_scores_analysis():
    avg_scores, max_score_by_minigame = oa.get_avg_scores_for_practice_assessment()
    if not avg_scores:
        return jsonify([])

    text = oa.avg_scores_for_practice_assessment_analysis(
        avg_scores, max_score_by_minigame, llm_client
    )
    return jsonify(text)


@app.route("/api/analysis/error-frequency")
def api_error_frequency_analysis():
    results = oa.get_error_frequency_results()
    if not results:
        return jsonify({"text": "No data found."})

    analysis_response = oa.error_frequency_analysis(results, llm_client)
    # text = oa.extract_relevant_text(analysis_response)
    return jsonify(analysis_response)


@app.route("/api/analysis/performance-duration")
def api_performance_duration_analysis():
    duration_data = oa.get_duration_vs_errors()
    if not duration_data:
        return jsonify({"text": "No session duration data available."})

    text = oa.performance_vs_duration(duration_data, llm_client)
    return jsonify(text)


@app.route("/api/analysis/overall-user")
def api_overall_user_analysis():
    results2 = oa.get_user_results()
    if not results2:
        return jsonify({"text": "No user data available."})

    text = oa.overall_user_analysis(results2, llm_client)
    return jsonify(text)


@app.route("/overall")
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


@app.route("/minigames")
def minigames():
    return render_template("minigames.html")


@app.route("/api/minigames")
def api_minigames_list():
    """
    Return a JSON array of all mini-games (Level_ID, Game_ID, Name).
    Used by minigames.html to build the card grid.
    """
    games = mg.get_list_of_minigames()
    return jsonify(games)


@app.route("/api/minigames/<int:game_id>/stats")
def api_minigame_stats(game_id):
    """
    Aggregate numeric stats + grouped error buckets for one mini-game.
    """
    attempts = mg.get_minigame_attempts(game_id)
    if not attempts:
        return jsonify({"message": "No attempts found for this mini-game."})

    summary = mg.analyse_minigame_attempts(attempts)
    errors = mg.aggregate_minigame_errors(attempts)

    # Optionally expose most-common texts for quick display
    top_minor = mg.top_errors(errors.get("minor", []), top_n=5)
    top_severe = mg.top_errors(errors.get("severe", []), top_n=5)

    return jsonify(
        {
            "summary": summary,
            "errors": errors,
            "top_minor": top_minor,
            "top_severe": top_severe,
        }
    )


@app.route("/api/minigames/<int:game_id>/ai-summary")
def api_minigame_ai_summary(game_id):
    """
    Generate an LLM-powered executive summary for the selected mini-game.
    (Called on demand from the front-end because it’s relatively expensive.)
    """
    attempts = mg.get_minigame_attempts(game_id)
    if not attempts:
        return jsonify({"analysis": "No gameplay data available for this mini-game."})

    summary_stats = mg.analyse_minigame_attempts(attempts)
    error_buckets = mg.aggregate_minigame_errors(attempts)

    # Resolve a human-friendly game name
    game_name = next(
        (g["Name"] for g in mg.get_list_of_minigames() if g["Level_ID"] == game_id),
        f"Minigame {game_id}",
    )

    analysis_text = mg.ai_summary_for_minigame(
        game_name, summary_stats, error_buckets, llm_client
    )

    return jsonify({"analysis": analysis_text})


@app.route("/user", methods=["GET", "POST"])
def user():
    users = ua.get_list_of_users()
    games = ua.get_list_of_games()

    if request.method == "POST":
        payload = request.get_json()

        # ? For debugging, can remove this later
        # print("\nReceived POST payload:\n")
        # print(payload)

        if "user_id" in payload and "game_id" in payload:
            # Handle main form
            user_id = payload.get("user_id")
            game_id = payload.get("game_id")

            # Check if user_id is not empty, but game_id is empty
            if user_id and (not game_id or str(game_id).strip() == ""):
                results = ua.fetch_user_errors(user_id)
                return jsonify(
                    {
                        "status": "success",
                        "message": "Gameplay records retrieved for the selected user and game are displayed below.",
                        "results": results,
                    }
                )
            # Handle "Overall Assessment" selection
            elif user_id and game_id == "overall_assessment":
                results = ua.get_user_all_games_results(user_id)
                if not results:
                    return jsonify(
                        {
                            "status": "error",
                            "message": "No gameplay records were found for the selected user.",
                        }
                    )
                else:
                    analysis = ua.analyze_results(
                        results, analysis_type="overall_assessment"
                    )
                    return jsonify(
                        {
                            "status": "success",
                            "message": f"Overall assessment shows {analysis['total_games']} minigames analyzed.",
                            "results": results,
                            "analysis": analysis,
                        }
                    )
            else:
                results = ua.get_user_game_results(user_id, game_id)

                if not results:
                    return jsonify(
                        {
                            "status": "error",
                            "message": "No gameplay records were found for the selected user and game.",
                        }
                    )
                else:
                    analysis = ua.analyze_results(results)
                    return jsonify(
                        {
                            "status": "success",
                            "message": "Gameplay records retrieved for the selected user and game are displayed below.",
                            "results": results,
                            "analysis": analysis,
                        }
                    )

        elif "row_analysis" in payload:
            # Handle row analysis
            row_data = payload["row_analysis"]

            # ? For debugging, can remove this later
            # print("\nAnalyzing individual row:\n")
            # print(row_data)
            # single_attempt_analysis_response = ua.response_cleanup(ua.analyze_single_attempt(row_data, llm_client)) # with cleanup

            single_attempt_analysis_response = ua.analyze_single_attempt(
                row_data, llm_client
            )

            # ? For debugging, can remove this later
            # print("\nSingle attempt analysis response:\n")
            # print(single_attempt_analysis_response)

            return jsonify(
                {
                    "message": "AI Analysis Completed.",
                    "analysis": single_attempt_analysis_response,
                }
            )

        elif "bulk_analysis" in payload:
            all_attempts = payload["bulk_analysis"]

            # ? For debugging, save the attempts to a file wth a timestamp
            # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # all_attempts_filename = f'all_attempts_{timestamp}.json'
            # with open(all_attempts_filename, 'w') as f:
            #     json.dump(all_attempts, f, indent=4)

            bulk_analysis = ua.analyze_multiple_attempts(all_attempts, llm_client)
            return jsonify(
                {
                    "message": "AI Analysis for all attempts completed.",
                    "analysis": bulk_analysis,
                }
            )

        else:
            return jsonify({"status": "error", "message": "Invalid POST payload."})

    return render_template("user.html", users=users, games=games)


@app.route("/generate-ai-prompt", methods=["POST"])
def mistakes():
    data = request.get_json()
    items = data.get("items", [])
    mistake_categories = ua.categorize_mistakes(items, llm_client)
    return jsonify(
        {"message": "AI Categorization Completed.", "Categories": mistake_categories}
    )


if __name__ == "__main__":
    app.run(debug=True)
