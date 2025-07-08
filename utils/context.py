from flask import current_app, g
import utils.llm as llm


def get_llm_client():
    if "llm_client" not in g:
        ai_type = current_app.config.get("AI-TYPE", "API")
        ai_model = (
            current_app.config.get("AI-MODEL", "") if ai_type == "LOCAL" else None
        )
        g.llm_client = llm.create_llm_client(type=ai_type, model=ai_model)
    return g.llm_client
