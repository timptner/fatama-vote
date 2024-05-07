import click
import string
import segno

from werkzeug.security import generate_password_hash

from vote.database import get_database
from vote.voters import BASE_DIR


@click.command("create-user")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_user(username: str, password: str) -> None:
    """Create a new user."""
    username = username.lower()
    if not username:
        click.echo(click.style("Username can't be empty.", fg="red"), err=True)
        exit(1)

    if any([char not in (string.ascii_lowercase + string.digits) for char in username]):
        msg = "Username can only contain digits and ascii letters."
        click.echo(click.style(msg, fg="red"), err=True)
        exit(1)

    if not password:
        click.echo(click.style("Password can't be empty.", fg="red"), err=True)
        exit(1)

    special_chars = "*/:_-!?+"
    if any(
        [
            char not in (string.ascii_letters + string.digits + special_chars)
            for char in password
        ]
    ):
        msg = f"Password can only contain digits, ascii letters and '{special_chars}'."
        click.echo(click.style(msg, fg="red"), err=True)
        exit(1)

    database = get_database()

    try:
        database.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        database.commit()
    except database.IntegrityError:
        click.echo(click.style(f"User '{username}' already exists", fg="red"), err=True)
        exit(1)

    click.echo(click.style(f"User '{username}' created", fg="green"))


@click.command("create-code")
@click.option("--text", prompt=True)
@click.option("--name", required=True)
def create_code(text: str, name: str) -> None:
    file = BASE_DIR / "vote" / "static" / f"{name}.png"
    code = segno.make_qr(text)
    code.save(str(file), scale=10, light="#F3F4F6", dark="#2E333D")
