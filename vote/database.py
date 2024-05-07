import click
import sqlite3

from flask import current_app, g


def get_database() -> sqlite3.Connection:
    if 'database' not in g:
        g.database = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.database.row_factory = sqlite3.Row
    return g.database


def close_database(e=None) -> None:
    database = g.pop("database", None)

    if database is not None:
        database.close()


def init_database() -> None:
    database = get_database()

    with current_app.open_resource("schema.sql") as file:
        database.executescript(file.read().decode("utf-8"))


@click.command("init-db")
def init_database_command() -> None:
    """Clear the existing data and create new tables."""
    init_database()
    click.echo("Initialized the database.")


def init_application(application) -> None:
    application.teardown_appcontext(close_database)
    application.cli.add_command(init_database_command)
