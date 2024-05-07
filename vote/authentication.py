import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, Response
)
from typing import Any
from werkzeug.security import check_password_hash

from vote.database import get_database

blueprint = Blueprint('auth', __name__, url_prefix="/auth")


@blueprint.before_app_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        database = get_database()
        user = database.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        g.user = user


@blueprint.route("/login/", methods=("GET", "POST"))
def login() -> str | Response:
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        database = get_database()

        user = database.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None:
            error = "Falscher Benutzername."
        elif not check_password_hash(user["password"], password):
            error = "Falsches Passwort."
        else:
            error = None

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

        flash(error)

    return render_template("auth/login.html")


@blueprint.route("/logout/")
def logout() -> Response:
    session.clear()
    return redirect(url_for("index"))


def login_required(view) -> Response | Any:
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view
