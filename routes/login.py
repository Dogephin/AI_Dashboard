from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import hashlib
from .models import SessionLocal, User

login_bp = Blueprint("login", __name__ , template_folder="templates")

@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_password = hashlib.md5(password.encode()).hexdigest()

        db = SessionLocal()
        user = db.query(User).filter_by(Username=username, Password=hashed_password).first()
        db.close()

        if user:
            session["user"] = user.Username
            session["role"] = "TBD"
            flash("Login successful!", "success")
            return redirect(url_for("home.home"))  
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@login_bp.route("/logout")
def logout():
    session.pop("user", None)
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login.login"))
