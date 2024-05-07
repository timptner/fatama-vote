from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, Response
)
from werkzeug.exceptions import abort

from vote.authentication import login_required
from vote.database import get_database

blueprint = Blueprint('polls', __name__)


@blueprint.route("/")
def index() -> str:
    database = get_database()
    polls = database.execute(
        "SELECT polls.id, subject, created, author_id, username"
        " FROM polls JOIN users ON polls.author_id = users.id"
        " ORDER BY created DESC"
    ).fetchall()
    return render_template("polls/index.html", polls=polls)


@blueprint.route("/create/", methods=("GET", "POST"))
@login_required
def create() -> str | Response:
    subject_min_length = 20
    subject_max_length = 250
    choices_min_count = 3
    choice_max_length = 50

    if request.method == "POST":
        subject = request.form["subject"].strip()
        choices = [choice.strip() for choice in request.form["choices"].splitlines() if choice.strip()]

        error = None

        if not subject:
            error = "Gegenstand wird benötigt."
        if len(subject) < subject_min_length:
            error = f"Gegenstand muss mindestens {subject_min_length} Zeichen lang sein."
        if len(subject) > subject_max_length:
            error = f"Gegenstand darf maximal {subject_max_length} Zeichen lang sein."

        if len(choices) < choices_min_count:
            error = f"Es müssen mindestens {choices_min_count} Optionen zur Auswahl stehen."
        if any([len(choice) > choice_max_length for choice in choices]):
            error = f"Optionen dürfen maximal {choice_max_length} Zeichen lang sein."

        if error is not None:
            flash(error)
        else:
            database = get_database()
            cursor = database.cursor()
            cursor.execute(
                "INSERT INTO polls (subject, author_id)"
                " VALUES (?, ?)",
                (subject, g.user["id"]),
            )
            poll_id = cursor.lastrowid
            cursor.executemany(
                "INSERT INTO choices (poll_id, name)"
                " VALUES (?, ?)",
                [(poll_id, choice) for choice in choices],
            )
            database.commit()
            return redirect(url_for("polls.index"))

    validation = {
        "subject_min": subject_min_length,
        "subject_max": subject_max_length,
    }
    return render_template("polls/create.html", validation=validation)


@blueprint.route("/<int:pk>/vote/", methods=("GET", "POST"))
def vote(pk: int) -> str | Response:
    database = get_database()

    poll = database.execute(
        "SELECT * FROM polls WHERE polls.id = ?",
        (pk,),
    ).fetchone()
    choices = database.execute(
        "SELECT * FROM choices WHERE poll_id = ?",
        (pk,),
    ).fetchall()

    if poll is None:
        abort(404, f"Poll with ID {pk} does not exist.")

    if request.method == "POST":
        token = request.form["token"]
        choice_id = int(request.form["choice"])

        error = None

        if not token:
            error = "Token wird benötigt."

        if choice_id not in [choice["id"] for choice in choices]:
            error = "Es können nur die zur Auswahl stehenden Optionen gewählt werden."

        if error is not None:
            flash(error)
        else:
            database.execute(
                "UPDATE choices SET count = count + 1 WHERE id = ?",
                (choice_id,),
            )
            database.commit()
            flash("Stimme wurde erfolgreich abgegeben.")
            return redirect(url_for("polls.index"))

    return render_template("polls/vote.html", poll=poll, choices=choices)
