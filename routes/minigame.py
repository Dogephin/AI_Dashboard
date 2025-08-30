from flask import Blueprint, render_template, request, jsonify
from analysis import minigames_analysis as mg
from utils.context import get_llm_client
from utils.cache import cache, generate_cache_key
from utils.auth import login_required

minigame_bp = Blueprint("minigame", __name__, template_folder="templates")


@minigame_bp.route("/minigames")
@login_required
def minigames():
    return render_template(
        "minigames.html", header_title="Game Analysis Dashboard - Minigames"
    )


@minigame_bp.route("/api/minigames")
@login_required
def api_minigames_list():
    """
    Return a JSON array of all mini-games (Level_ID, Game_ID, Name).
    Used by minigames.html to build the card grid.
    """
    games = mg.get_list_of_minigames()
    return jsonify(games)


@minigame_bp.route("/api/minigames/<int:game_id>/stats")
@login_required
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


@minigame_bp.route("/api/minigames/<int:game_id>/ai-summary")
@login_required
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

    # Caching the analysis to avoid repeated LLM calls
    key = generate_cache_key(
        "minigame_ai_summary",
        {
            "game_id": game_id,
            "summary_stats": summary_stats,
            "error_buckets": error_buckets,
        },
    )

    # Check for force refresh (bypass cache)
    force_refresh = request.args.get("force_refresh", "false").lower() == "true"
    analysis_text = None if force_refresh else cache.get(key)

    if not analysis_text:
        analysis_text = mg.ai_summary_for_minigame(
            game_name, summary_stats, error_buckets, get_llm_client()
        )
        cache.set(key, analysis_text)

    return jsonify({"analysis": analysis_text})
