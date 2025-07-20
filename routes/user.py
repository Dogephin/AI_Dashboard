from flask import Blueprint, render_template, request, jsonify
from analysis import user_analysis as ua
from utils.context import get_llm_client
from utils.cache import cache, generate_cache_key

import json
import datetime

user_bp = Blueprint("user", __name__, template_folder="templates")


@user_bp.route("/user", methods=["GET", "POST"])
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

            key = generate_cache_key("row_analysis", row_data)
            single_attempt_analysis_response = cache.get(key)

            if not single_attempt_analysis_response:
                single_attempt_analysis_response = ua.analyze_single_attempt(
                    row_data, get_llm_client()
                )
                cache.set(key, single_attempt_analysis_response)

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

            key = generate_cache_key("bulk_analysis", all_attempts)
            bulk_analysis = cache.get(key)

            # ? For debugging, save the attempts to a file wth a timestamp
            # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # all_attempts_filename = f'all_attempts_{timestamp}.json'
            # with open(all_attempts_filename, 'w') as f:
            #     json.dump(all_attempts, f, indent=4)

            if not bulk_analysis:
                bulk_analysis = ua.analyze_multiple_attempts(
                    all_attempts, get_llm_client()
                )
                cache.set(key, bulk_analysis)

            return jsonify(
                {
                    "message": "AI Analysis for all attempts completed.",
                    "analysis": bulk_analysis,
                }
            )

        else:
            return jsonify({"status": "error", "message": "Invalid POST payload."})

    return render_template("user.html", users=users, games=games)


@user_bp.route("/generate-ai-prompt", methods=["POST"])
def mistakes():
    data = request.get_json()
    items = data.get("items", [])

    # Cache the mistake categories
    key = generate_cache_key("mistakes", items)
    mistake_categories = cache.get(key)

    if not mistake_categories:
        # If not cached, categorize mistakes using the LLM client
        mistake_categories = ua.categorize_mistakes(items, get_llm_client())
        cache.set(key, mistake_categories)

    return jsonify(
        {"message": "AI Categorization Completed.", "Categories": mistake_categories}
    )
