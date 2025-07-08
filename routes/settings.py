from flask import Blueprint, render_template, request, jsonify, g, current_app
import utils.llm as llm

settings_bp = Blueprint("settings", __name__, template_folder="templates")


@settings_bp.route("/settings", methods=["GET", "POST"])
def settings():

    if request.method == "POST":
        # If toggle is toggled, value will be "API", if unchecked, set to "LOCAL"
        ai_type = request.form.get("ai_type", "LOCAL").upper()
        ai_model = request.form.get("ai_model", "")

        if ai_type == "LOCAL":
            available_models = llm.get_models()
            if ai_model not in available_models:
                return jsonify({"message": f"Model '{ai_model}' not found."}), 400

        current_type = current_app.config.get("AI-TYPE")
        current_model = current_app.config.get("AI-MODEL")

        # Only update if something changed
        if current_type != ai_type or current_model != ai_model:
            current_app.config["AI-TYPE"] = ai_type
            current_app.config["AI-MODEL"] = ai_model if ai_type == "LOCAL" else ""
            g.pop("llm_client", None)  # Invalidate the per-request client cache

        message = f"Settings saved successfully. AI type set to {ai_type}."
        if ai_type == "LOCAL" and ai_model:
            message += f" Model set to {ai_model}."

        return jsonify({"message": message})

    print(f"Current AI type: {current_app.config.get('AI-TYPE')}")
    print(
        f"Current AI model: {current_app.config.get('AI-MODEL')}"
        if current_app.config.get("AI-TYPE") == "LOCAL"
        else "Current AI model: N/A"
    )

    return render_template(
        "settings.html",
        ai_type=current_app.config.get("AI-TYPE"),
        models=llm.get_models(),
        selected_model=current_app.config.get("AI-MODEL"),
    )
