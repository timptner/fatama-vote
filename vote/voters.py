import click
import functools
import math

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Response,
    current_app,
)
from matplotlib.figure import Figure
from typing import Any
from werkzeug.security import check_password_hash
from pathlib import Path

from vote.authentication import login_required
from vote.database import get_database

BASE_DIR = Path(__file__).parent.parent

blueprint = Blueprint("voters", __name__, url_prefix="/voters")


@blueprint.route("/")
@login_required
def index() -> str:
    database = get_database()
    voters = database.execute("SELECT * FROM voters").fetchall()
    return render_template("voters/index.html", voters=voters)


def get_weight(students: int) -> int:
    weight = 4

    if 1000 <= students:
        n = min(students, 5000) - 999
        weight += math.ceil(n / 500)

    if 6000 <= students:
        n = min(students, 10000) - 5999
        weight += math.ceil(n / 1000)

    return weight


@click.command("plot-weight")
def plot_weight_curve() -> None:
    fig = Figure(figsize=(16, 9))
    ax = fig.subplots()

    x = range(1, 20000)
    y = [get_weight(n) for n in x]

    ax.plot(x, y)

    ax.set_xlabel("Studenten")
    ax.set_ylabel("Stimmen")

    click.echo(click.style("Diagram erstellt.", fg="green"))
    file = BASE_DIR / "vote" / "static" / "weight.svg"
    fig.savefig(file, format="svg")


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
                "INSERT INTO voters (name, weight) VALUES (?, ?)",
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
