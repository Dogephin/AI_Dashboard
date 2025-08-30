from flask import Blueprint, render_template
from utils.auth import login_required

home_bp = Blueprint("home", __name__, template_folder="templates")

@home_bp.route("/")
@login_required
def home():
    return render_template("index.html", header_title="Game Analysis Dashboard")
