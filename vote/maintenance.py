import click
import string

from werkzeug.security import generate_password_hash

from vote.database import get_database


@click.command("create-user")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_user(username: str, password: str) -> None:
    """Create a new user."""
    username = username.lower()
    if not username:
        click.echo(click.style("Username can't be empty.", fg="red"), err=True)
        exit(1)

    if any([char not in (string.ascii_lowercase + string.digits) for char in username.split()]):
        click.echo(click.style("Username can only contain digits and ascii letters.", fg="red"), err=True)
        exit(1)

    if not password:
        click.echo(click.style("Password can't be empty.", fg="red"), err=True)
        exit(1)

    special_chars = "*/:_-!?+"
    if any([char not in (string.ascii_letters + string.digits + special_chars) for char in password.split()]):
        msg = f"Password can only contain digits, ascii letters and '{special_chars}'."
        click.echo(click.style(msg, fg="red"), err=True)
        exit(1)

    database = get_database()

    try:
        database.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        database.commit()
    except database.IntegrityError:
        click.echo(click.style(f"User '{username}' already exists", fg="red"), err=True)
        exit(1)

    click.echo(click.style("User created", fg="green"))


def add_maintenance_commands(application) -> None:
    application.cli.add_command(create_user)
