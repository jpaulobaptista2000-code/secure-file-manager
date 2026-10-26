"""Registration, login and logout. File handling is added in a later step."""

import re

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template,
    request, session, url_for,
)
from sqlalchemy.exc import IntegrityError

from extensions import db, limiter
from models import User
from security import (
    dummy_password_hash, password_hasher, password_matches,
    start_authenticated_session,
)

auth = Blueprint("auth", __name__)
USERNAME = re.compile(r"[a-z0-9_]{3,30}\Z")


@auth.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def register():
    if g.user is not None:
        return redirect(url_for("files"), code=303)
    error = None
    username = ""
    status = 200
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirm_password", "")
        if not USERNAME.fullmatch(username):
            error = "Use 3–30 letters (a–z), numbers or underscores for your username."
        elif not 15 <= len(password) <= 128:
            error = "Use a password with 15–128 characters. Spaces are allowed."
        elif password != confirmation:
            error = "The passwords do not match."
        else:
            user = User(username=username, password_hash=password_hasher.hash(password))
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                error = "That username is unavailable. Choose another one."
                status = 409
            else:
                session.clear()
                flash("Account created. You can now sign in.", "success")
                current_app.session_interface.regenerate(session)
                return redirect(url_for("auth.login"), code=303)
        if status == 200:
            status = 400
    return render_template("register.html", error=error, username=username), status


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if g.user is not None:
        return redirect(url_for("files"), code=303)
    error = None
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if USERNAME.fullmatch(username) and 1 <= len(password) <= 128:
            user = db.session.execute(
                db.select(User).filter_by(username=username)
            ).scalar_one_or_none()
            stored_hash = user.password_hash if user else dummy_password_hash
            valid_password = password_matches(stored_hash, password)
            if user is not None and valid_password:
                if password_hasher.check_needs_rehash(user.password_hash):
                    user.password_hash = password_hasher.hash(password)
                    db.session.commit()
                start_authenticated_session(user)
                return redirect(url_for("files"), code=303)
        error = "Incorrect username or password."
    return render_template("login.html", error=error, username=username), 401 if error else 200


@auth.post("/logout")
def logout():
    # Flask-Session deletes the database session and cookie when saving an empty session.
    session.clear()
    return redirect(url_for("auth.login"), code=303)
