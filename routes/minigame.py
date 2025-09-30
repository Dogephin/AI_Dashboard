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
    Aggregate numeric stats + grouped error buckets for one mini-game,
    including monthly warning trends.
    """
    # Fetch all attempts
    attempts = mg.get_minigame_attempts(game_id)
    if not attempts:
        return jsonify({"message": "No attempts found for this mini-game."})

    # Basic stats
    summary = mg.analyse_minigame_attempts(attempts)
    errors = mg.aggregate_minigame_errors(attempts)
    
    # Top errors for display
    top_minor = mg.top_errors(errors.get("minor", []), top_n=5)
    top_severe = mg.top_errors(errors.get("severe", []), top_n=5)

    # Monthly warning trend
    warning_stats = mg.fetch_warning_stats(game_id)

    return jsonify({
        "summary": summary,
        "errors": errors,
        "top_minor": top_minor,
        "top_severe": top_severe,
        "warning_stats": warning_stats
    })


@minigame_bp.route("/api/minigames/<int:game_id>/ai-explain")
def api_minigame_ai_explain_from_attempts(game_id):
    mode = (request.args.get("mode") or "all").lower()
    data = mg.build_ai_explain_payload_from_attempts(level_id=game_id, mode=mode)

    text = mg.ai_explain_for_minigame(
        data.get("name") or f"Level {game_id}",
        data,
        get_llm_client()
    )
    return jsonify({"analysis": text, "data": data, "mode": mode})

@minigame_bp.route("/api/minigames/<int:game_id>/warnings/ai-summary")
@login_required
def api_warnings_ai_summary(game_id):
    """
    Generate an LLM-powered executive summary of monthly warnings.
    """
    # Get warning stats
    stats = mg.fetch_warning_stats(game_id)
    if not stats:
        return jsonify({"analysis": "No warning data available for this mini-game."})

    # Resolve human-friendly game name
    game_name = next(
        (g["Name"] for g in mg.get_list_of_minigames() if g["Level_ID"] == game_id),
        f"Minigame {game_id}",
    )

    # Optional caching
    key = generate_cache_key("warnings_ai_summary", {"game_id": game_id, "stats": stats})
    force_refresh = request.args.get("force_refresh", "false").lower() == "true"
    analysis_text = None if force_refresh else cache.get(key)

    if not analysis_text:
        analysis_text = mg.ai_summary_for_warnings(game_name, stats, get_llm_client())
        cache.set(key, analysis_text)

    return jsonify({"analysis": analysis_text})




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

@minigame_bp.route("/api/minigames/combined-stats")
def minigames_combined_stats():
    mode = (request.args.get("mode") or "all").lower()  # 'all' | 'practice' | 'training'
    rows = mg.get_combined_game_stats(mode=mode)

    worst_ratio = None
    toughest = None
    if rows:
        cr = [r for r in rows if r["failure_success_ratio"] is not None]
        if cr: worst_ratio = max(cr, key=lambda r: r["failure_success_ratio"])
        ca = [r for r in rows if r["avg_attempts_before_success"] is not None]
        if ca: toughest = max(ca, key=lambda r: r["avg_attempts_before_success"])

    return jsonify({"rows": rows, "worst_ratio": worst_ratio, "toughest": toughest, "mode": mode})

@minigame_bp.route("/api/minigames/completion")
@login_required
def api_minigames_completion():
    """Return per-minigame completion % with counts."""
    games = mg.get_list_of_minigames()
    out = []
    for g in games:
        gid = g["Level_ID"]
        attempts = mg.get_minigame_attempts(gid)
        if not attempts:
            out.append({
                "Level_ID": gid,
                "Name": g["Name"],
                "completed": 0,
                "attempted": 0,
                "completion_rate": 0.0
            })
            continue

        summary = mg.analyse_minigame_attempts(attempts)  # you already have this
        completed = summary.get("completed", 0)
        attempted = summary.get("total_attempts", 0)
        rate = float(summary.get("completion_rate", 0.0))  # already in %

        out.append({
            "Level_ID": gid,
            "Name": g["Name"],
            "completed": completed,
            "attempted": attempted,
            "completion_rate": rate
        })
    # sort by name for stable chart order
    out.sort(key=lambda r: r["Name"].lower())
    return jsonify({"rows": out})

@minigame_bp.route("/api/minigames/completion/ai-priority")
@login_required
def api_minigames_ai_priority():
    """
    Ask the LLM to highlight low-performing minigames and concrete next steps.
    Query params:
      - threshold (float, %). If provided, treat games below it as priority.
      - top_n (int). If provided, pick the N lowest completion-rate games.
    """
    try:
        threshold = float(request.args.get("threshold")) if request.args.get("threshold") else None
    except ValueError:
        threshold = None
    try:
        top_n = int(request.args.get("top_n")) if request.args.get("top_n") else None
    except ValueError:
        top_n = None

    # Reuse the completion API logic
    games = []
    for g in mg.get_list_of_minigames():
        gid = g["Level_ID"]
        attempts = mg.get_minigame_attempts(gid)
        if not attempts:
            games.append({"Level_ID": gid, "Name": g["Name"], "completion_rate": 0.0, "attempted": 0, "completed": 0})
            continue
        s = mg.analyse_minigame_attempts(attempts)
        games.append({
            "Level_ID": gid,
            "Name": g["Name"],
            "completion_rate": float(s.get("completion_rate", 0.0)),
            "attempted": int(s.get("total_attempts", 0)),
            "completed": int(s.get("completed", 0)),
        })

    # Select priority set
    ranked = sorted(games, key=lambda r: r["completion_rate"])
    if threshold is not None:
        priority = [r for r in ranked if r["completion_rate"] < threshold]
        picked_by = f"below {threshold:.1f}%"
    elif top_n is not None and top_n > 0:
        priority = ranked[:top_n]
        picked_by = f"bottom {top_n}"
    else:
        # default: bottom quartile (at least 3 items)
        n = max(3, max(1, len(ranked)//4))
        priority = ranked[:n]
        picked_by = f"bottom quartile ({n})"

    # LLM prompt
    client = get_llm_client()
    prompt = f"""
    You are the analytics assistant for a learning game platform.
    Given minigames with completion rates (%), attempted/completed counts,
    identify where support should be prioritised and what to do next.

    Selection rule used: {picked_by}

    Priority list (lowest completion first):
    {[
        {'id': r['Level_ID'], 'name': r['Name'], 'completion_%': r['completion_rate'],
        'attempted': r['attempted'], 'completed': r['completed']}
        for r in priority
    ]}

    All games (for context):
    {[
        {'id': r['Level_ID'], 'name': r['Name'], 'completion_%': r['completion_rate'],
        'attempted': r['attempted'], 'completed': r['completed']}
        for r in ranked
    ]}

    Write a concise, actionable markdown brief:
    - Bullet a ranked priority list with reasons (e.g., low completion %, high attempts but low success).
    - Suggest 2–3 targeted actions per game (UX tweaks, scaffolding hints, tutorial step, error messaging, difficulty curve).
    - Add a short global “next 2 weeks” plan (A/B tests, instrumentation to add).
    Keep it under 250 words.
    """
    # You already have an LLM helper; use it if you prefer, else call client directly.
    text = mg.ai_prioritise_low_performing(ranked, priority, picked_by, client)

    return jsonify({"analysis": text, "selected": priority, "all": ranked})
