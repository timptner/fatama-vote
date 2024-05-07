import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, Response
)
from typing import Any
from werkzeug.security import check_password_hash

from vote.authentication import login_required
from vote.database import get_database

blueprint = Blueprint('voters', __name__, url_prefix="/voters")


@blueprint.route("/")
@login_required
def index() -> str:
    database = get_database()
    voters = database.execute(
        "SELECT * FROM voters"
    ).fetchall()
    return render_template("voters/index.html", voters=voters)


@blueprint.route("/create/", methods=("GET", "POST"))
@login_required
def create() -> str | Response:
    name_max_length = 250
    weight_min_amount = 1
    weight_max_amount = 20

    if request.method == "POST":
        name = request.form["name"] or ""
        name = name.strip()
        weight = int(request.form["weight"])

        error = None

        if len(name) > name_max_length:
            error = f"Name darf maximal {name_max_length} Zeichen lang sein."

        if weight < weight_min_amount:
            error = f"Die Gewichtung muss mindestens {weight_min_amount} betragen."
        if weight > weight_max_amount:
            error = f"Die Gewichtung darf maximal {weight_max_amount} betragen."

        if error is not None:
            flash(error)
        else:
            database = get_database()
            database.execute(
                "INSERT INTO voters (name, weight)"
                " VALUES (?, ?)",
                (name, weight),
            )
            database.commit()
            return redirect(url_for("voters.index"))

    validation = {
        "name_max": name_max_length,
        "weight_min": weight_min_amount,
        "weight_max": weight_max_amount
    }
    return render_template("voters/create.html", validation=validation)
