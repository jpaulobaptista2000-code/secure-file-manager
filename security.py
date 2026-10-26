"""Local secret creation, password hashing and authenticated session checks."""

from functools import wraps
from pathlib import Path
import os
import secrets
import time

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from flask import current_app, g, redirect, session, url_for

from extensions import db
from models import User

password_hasher = PasswordHasher(type=Type.ID)
# Unknown usernames still perform a password verification to reduce timing differences.
dummy_password_hash = password_hasher.hash(secrets.token_urlsafe(32))


def load_or_create_secret(instance_path):
    folder = Path(instance_path)
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = folder / "secret.key"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "wb") as secret_file:
            secret_file.write(secrets.token_bytes(32))
    secret = path.read_bytes()
    if len(secret) != 32:
        raise RuntimeError("The local secret.key is invalid; restore its original contents.")
    return secret


def password_matches(stored_hash, password):
    try:
        return password_hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def load_current_user():
    g.user = None
    user_id = session.get("user_id")
    if user_id is None:
        return

    now = int(time.time())
    login_at = session.get("login_at", 0)
    last_seen = session.get("last_seen", 0)
    if (
        now - login_at >= current_app.config["AUTH_ABSOLUTE_SECONDS"]
        or now - last_seen >= current_app.config["AUTH_IDLE_SECONDS"]
    ):
        session.clear()
        return

    g.user = db.session.get(User, user_id)
    if g.user is None:
        session.clear()
        return
    session["last_seen"] = now


def start_authenticated_session(user):
    session.clear()
    session["user_id"] = user.id
    session["login_at"] = int(time.time())
    session["last_seen"] = session["login_at"]
    session.permanent = True
    # Regenerate after filling the session: Flask-Session ignores an empty session.
    current_app.session_interface.regenerate(session)


def login_required(view):
    @wraps(view)
    def protected_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"), code=303)
        return view(*args, **kwargs)

    return protected_view
