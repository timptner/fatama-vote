from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
    Response,
)
from werkzeug.exceptions import abort

from vote import database
from vote.authentication import login_required
from vote.database import get_database

blueprint = Blueprint("polls", __name__)


@blueprint.route("/")
def index() -> str:
    database = get_database()
    polls = database.execute(
        "SELECT polls.id, subject, author_id, created, state, type, username"
        " FROM polls"
        " JOIN users ON polls.author_id = users.id"
        " ORDER BY created DESC"
    ).fetchall()

    results = {}
    for poll in polls:
        poll_id = poll["id"]
        if poll["type"] == "Namentlich":
            data = database.execute(
                "SELECT choices.name, voters.name"
                " FROM ballots"
                " RIGHT JOIN choices ON ballots.choice_id = choices.id"
                " LEFT JOIN voters ON ballots.voter_id = voters.id"
                " WHERE choices.poll_id = ?",
                (poll_id,),
            ).fetchall()
            result = {}
            for item in data:
                choice_name = item[0]
                voter_name = item[1]
                if choice_name not in result.keys():
                    result[choice_name] = []
                result[choice_name].append(voter_name)
        elif poll["type"] == "Gewichtet":
            result = database.execute(
                "SELECT choices.name, SUM(voters.weight) as count"
                " FROM ballots"
                " RIGHT JOIN choices ON ballots.choice_id = choices.id"
                " LEFT JOIN voters ON ballots.voter_id = voters.id"
                " WHERE choices.poll_id = ?"
                " GROUP BY choices.name",
                (poll_id,),
            ).fetchall()
        else:
            result = database.execute(
                "SELECT choices.name, COUNT(ballots.voter_id) AS count"
                " FROM ballots"
                " RIGHT JOIN choices ON ballots.choice_id = choices.id"
                " WHERE choices.poll_id = ?"
                " GROUP BY choices.name",
                (poll_id,),
            ).fetchall()
        results[poll_id] = result

    return render_template("polls/index.html", polls=polls, results=results)


@blueprint.route("/create/", methods=("GET", "POST"))
@login_required
def create() -> str | Response:
    subject_min_length = 20
    subject_max_length = 250
    choices_min_count = 3
    choice_max_length = 50
    type_choices = ("Einfach", "Namentlich", "Gewichtet", "Geheim")

    if request.method == "POST":
        subject = request.form["subject"].strip()
        choices = [
            choice.strip()
            for choice in request.form["choices"].splitlines()
            if choice.strip()
        ]
        type_ = request.form["type"]

        error = None

        if not subject:
            error = "Gegenstand wird benötigt."

        if len(subject) < subject_min_length:
            error = (
                f"Gegenstand muss mindestens {subject_min_length} Zeichen lang sein."
            )
        if len(subject) > subject_max_length:
            error = f"Gegenstand darf maximal {subject_max_length} Zeichen lang sein."

        if len(choices) < choices_min_count:
            error = (
                f"Es müssen mindestens {choices_min_count} Optionen zur Auswahl stehen."
            )
        if any([len(choice) > choice_max_length for choice in choices]):
            error = f"Optionen dürfen maximal {choice_max_length} Zeichen lang sein."

        if type_ not in type_choices:
            error = f"Es können nur {type_choices} ausgewählt werden."

        if error is not None:
            flash(error)
        else:
            database = get_database()
            cursor = database.cursor()
            cursor.execute(
                "INSERT INTO polls (subject, author_id, type) VALUES (?, ?, ?)",
                (subject, g.user["id"], type_),
            )
            poll_id = cursor.lastrowid
            cursor.executemany(
                "INSERT INTO choices (poll_id, name) VALUES (?, ?)",
                [(poll_id, choice) for choice in choices],
            )
            database.commit()
            return redirect(url_for("polls.index"))

    validation = {
        "subject_min": subject_min_length,
        "subject_max": subject_max_length,
        "type_choices": type_choices,
    }
    return render_template("polls/create.html", validation=validation)


@blueprint.route("/<int:poll_id>/state/", methods=("GET", "POST"))
@login_required
def state(poll_id: int) -> str | Response:
    state_choices = ("Vorbereitet", "Offen", "Geschlossen", "Gelöscht")

    database = get_database()
    poll = database.execute(
        "SELECT * FROM polls WHERE polls.id = ?",
        (poll_id,),
    ).fetchone()

    if poll is None:
        abort(404, f"Poll with ID {poll_id} does not exist.")

    if request.method == "POST":
        state = request.form["state"]

        error = None

        if not state:
            error = "Status wird benötigt."

        if state not in state_choices:
            error = f"Status kann nur {state_choices} sein."

        current_state = poll["state"]
        valid_transition = True

        if current_state == "Vorbereitet":
            if state not in ("Offen", "Gelöscht"):
                valid_transition = False
        elif current_state == "Offen":
            if state not in ("Geschlossen", "Gelöscht"):
                valid_transition = False
        elif current_state == "Geschlossen":
            if state != "Gelöscht":
                valid_transition = False
        elif current_state == "Gelöscht":
            valid_transition = False
        else:
            abort(500, "Unknown poll state.")

        if not valid_transition:
            error = f"Der Wechsel von {current_state} nach {state} ist nicht möglich."

        if error is not None:
            flash(error)
        else:
            database.execute(
                "UPDATE polls SET state = ? WHERE polls.id = ?",
                (state, poll_id),
            )
            database.commit()
            return redirect(url_for("polls.index"))

    return render_template("polls/state.html", poll=poll, states=state_choices)


@blueprint.route("/<int:poll_id>/vote/", methods=("GET", "POST"))
def vote(poll_id: int) -> str | Response:
    database = get_database()

    poll = database.execute(
        "SELECT * FROM polls WHERE polls.id = ?",
        (poll_id,),
    ).fetchone()

    if poll is None:
        abort(404, f"Poll with ID {poll_id} does not exist.")

    if poll["state"] != "Offen":
        abort(403, f"Poll with ID {poll_id} is not available for voting.")

    choices = database.execute(
        "SELECT * FROM choices WHERE poll_id = ?",
        (poll_id,),
    ).fetchall()

    if request.method == "POST":
        token_id = request.form["token"]
        choice_id = int(request.form["choice"])

        error = None

        if not token_id:
            error = "Token wird benötigt."

        data = database.execute(
            "SELECT expired, voters.id, name FROM tokens"
            " JOIN voters ON tokens.voter_id = voters.id WHERE key = ?",
            (token_id,),
        ).fetchone()

        if data is None:
            is_expired = True
        else:
            voter = {
                "id": data["id"],
                "name": data["name"],
            }

            if poll["type"] == "Geheim" and voter["name"]:
                error = "Es können nur Tokens einer anonymen Transaktionsliste bei dieser Abstimmung verwendet werden."

            if poll["type"] != "Geheim" and not voter["name"]:
                error = "Es können nur Tokens einer namentlichen Transaktionsliste bei dieser Abstimmung verwendet werden."

            is_expired = data["expired"]

            ballots = database.execute(
                "SELECT ballots.voter_id FROM polls"
                " JOIN choices ON choices.poll_id = polls.id"
                " JOIN ballots ON ballots.choice_id = choices.id"
                " WHERE polls.id = ?",
                (poll_id,),
            ).fetchall()
            voters_id = [ballot["voter_id"] for ballot in ballots]

            if voter["id"] in voters_id:
                error = "Du hast bereits an dieser Abstimmung teilgenommen."

        if is_expired:
            error = "Der Token ist ungültig."

        if choice_id not in [choice["id"] for choice in choices]:
            error = "Es können nur die zur Auswahl stehenden Optionen gewählt werden."

        if error is not None:
            flash(error)
        else:
            database.execute(
                "INSERT INTO ballots (choice_id, voter_id) VALUES (?, ?)",
                (choice_id, voter["id"]),
            )
            database.execute(
                "UPDATE tokens SET expired = TRUE WHERE key = ?",
                (token_id,),
            )
            database.commit()
            flash("Stimme wurde erfolgreich abgegeben.")
            return redirect(url_for("polls.index"))

    return render_template("polls/vote.html", poll=poll, choices=choices)
