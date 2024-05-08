import click
import functools
import math
import string
import secrets

from flask import (
    abort,
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
    make_response,
)
from matplotlib.figure import Figure
from typing import Any
from werkzeug.security import check_password_hash
from pathlib import Path

from vote.authentication import login_required
from vote.database import get_database

BASE_DIR = Path(__file__).parent.parent

blueprint = Blueprint("voters", __name__, url_prefix="/voters")


@blueprint.route("/info/", methods=("GET", "POST"))
def info() -> str:
    voter = None

    if request.method == "POST":
        voter_id = request.form["voter_id"]

        error = None

        if voter_id is None:
            error = "Wähler-ID wird benötigt."
        else:
            database = get_database()
            voter_raw = database.execute(
                "SELECT * FROM voters WHERE id = ?",
                (voter_id,),
            ).fetchone()
            if voter_raw:
                voter = {
                    "id": voter_raw["id"],
                    "name": voter_raw["name"],
                    "weight": voter_raw["weight"],
                }

        if voter is None:
            error = "Unbekannte Wähler-ID."

        if error is not None:
            flash(error)
        else:
            pass

    return render_template("voters/info.html", voter=voter)


@blueprint.route("/")
@login_required
def index() -> str:
    database = get_database()
    data = database.execute(
        "SELECT id, name, weight, (SELECT COUNT(key) FROM tokens WHERE tokens.voter_id = voters.id) AS count FROM voters"
    ).fetchall()
    voters = []
    for item in data:
        voters.append(
            {
                "id": item["id"],
                "name": item["name"],
                "weight": item["weight"],
                "count": item["count"],
            }
        )
    print(voters)
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
    students_min = 1

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        students = int(request.form["students"])

        error = None

        if len(name) > name_max_length:
            error = f"Name darf maximal {name_max_length} Zeichen lang sein."

        if students < students_min:
            error = (
                f"Die Anzahl der Studierende muss mindestens {students_min} betragen."
            )

        if name == "" and students != 1:
            error = "Anonyme Wähler können keine Studierenden haben. (Studierende muss Wert 1 haben.)"

        if error is not None:
            flash(error)
        else:
            weight = get_weight(students) if name else 1
            database = get_database()
            database.execute(
                "INSERT INTO voters (name, weight) VALUES (?, ?)",
                (name, weight),
            )
            database.commit()
            return redirect(url_for("voters.index"))

    validation = {
        "name_max": name_max_length,
        "students_min": students_min,
    }
    return render_template("voters/create.html", validation=validation)


@blueprint.route("/<int:voter_id>/update/", methods=("GET", "POST"))
@login_required
def update(voter_id: int) -> str | Response:
    name_max_length = 250
    weight_min = 1
    weight_max = 20

    database = get_database()
    voter = database.execute(
        "SELECT * FROM voters WHERE id = ?",
        (voter_id,),
    ).fetchone()

    if voter is None:
        abort(404, "Wähler mit dieser ID existiert nicht.")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        weight = int(request.form["weight"])

        error = None

        if len(name) > name_max_length:
            error = f"Name darf maximal {name_max_length} Zeichen lang sein."

        if name == "" and voter["name"] != "":
            error = "Namentlicher Wähler kann nicht anonymisiert werden."

        if name != "" and voter["name"] == "":
            error = "Anonyme Wähler können nicht namentlich gemacht werden."

        if weight < weight_min:
            error = f"Die Anzahl der Stimmen muss mindestens {weight_min} betragen."

        if weight > weight_max:
            error = f"Die Anzahl der Stimmen darf maximal {weight_max} betragen."

        if name == "" and weight != 1:
            error = "Anonyme Wähler müssen 1 Stimme haben."

        if error is not None:
            flash(error)
        else:
            database = get_database()
            database.execute(
                "UPDATE voters SET name = ?, weight = ? WHERE id = ?",
                (name, weight, voter_id),
            )
            database.commit()
            flash("Wähler aktualisiert.")
            return redirect(url_for("voters.index"))

    validation = {
        "name_max": name_max_length,
        "weight_min": weight_min,
        "weight_max": weight_max,
    }
    return render_template("voters/update.html", validation=validation, voter=voter)


def get_token() -> str:
    chars = string.ascii_uppercase + string.digits
    token = [secrets.choice(chars) for n in range(6)]
    return "".join(token)


@blueprint.route("/<int:voter_id>/tokens/", methods=("GET", "POST"))
@login_required
def create_tokens(voter_id: int) -> str | Response:
    database = get_database()
    count = database.execute(
        "SELECT COUNT(key) FROM tokens WHERE voter_id = ? AND expired = FALSE",
        (voter_id,),
    ).fetchone()
    has_tokens = count[0] > 0

    amount_min = 10
    amount_max = 50

    if request.method == "POST":
        amount = int(request.form["amount"])

        error = None

        if amount < amount_min:
            error = f"Es müssen mindestens {amount_min} Tokens erstellt werden."

        if amount > amount_max:
            error = f"Es können maximal {amount_max} Tokens erstellt werden."

        if error is not None:
            flash(error)
        else:
            if has_tokens:
                database.execute(
                    "UPDATE tokens SET expired = TRUE WHERE voter_id = ?",
                    (voter_id,),
                )
                database.commit()

            existing_tokens = set(database.execute("SELECT key FROM tokens").fetchall())

            tokens = set()

            counter = 0
            while len(tokens) < amount:
                if counter > 20:
                    abort(500, "Failed to generate token set.")
                token = get_token()
                if token in existing_tokens:
                    counter += 1
                    continue
                tokens.add(token)

            database.executemany(
                "INSERT INTO tokens (voter_id, key) VALUES (?, ?)",
                [(voter_id, token) for token in tokens],
            )
            database.commit()

            flash("Neuer Tokensatz wurden generiert.")
            return redirect(url_for("voters.index"))

    validation = {
        "amount_min": amount_min,
        "amount_max": amount_max,
    }
    return render_template(
        "voters/tokens.html", validation=validation, has_tokens=has_tokens
    )


@blueprint.route("/<int:voter_id>/tokens/print/")
@login_required
def printable(voter_id: int) -> str:
    database = get_database()
    voter_raw = database.execute(
        "SELECT id, name, weight FROM voters WHERE id = ?",
        (voter_id,),
    ).fetchone()
    voter = {
        "id": voter_raw["id"],
        "name": voter_raw["name"] or "Anonym",
        "weight": voter_raw["weight"],
    }
    created = database.execute(
        "SELECT DISTINCT created FROM tokens WHERE voter_id = ? ORDER BY created DESC",
        (voter_id,),
    ).fetchone()[0]
    tokens = database.execute(
        "SELECT * FROM tokens WHERE voter_id = ? and created = ?",
        (voter_id, created),
    ).fetchall()

    if not tokens:
        abort(404, f"Voter with ID {voter_id} does not have any tokens.")

    return render_template(
        "voters/printable.html", voter=voter, tokens=tokens, created=created
    )
