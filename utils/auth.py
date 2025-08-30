from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:  # check if user is logged in
            flash("You must be logged in to access this page.", "warning")
            return redirect(url_for("login.login"))  # redirect to login page
        return f(*args, **kwargs)
    return decorated_function
