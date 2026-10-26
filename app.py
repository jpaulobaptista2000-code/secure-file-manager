"""Flask application with local accounts, HTTPS and encrypted file management."""

from datetime import timedelta
from pathlib import Path

from flask import Flask, abort, g, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError

from auth import auth
from encrypted_storage import init_storage
from extensions import csrf, db, limiter, server_sessions
from file_routes import file_routes, render_file_list
from security import load_current_user, load_or_create_secret, login_required
from upload_request import UploadRequest


def create_app(test_config=None, instance_path=None):
    app = Flask(__name__, instance_relative_config=True, instance_path=instance_path)
    app.request_class = UploadRequest
    app.config.from_mapping(
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
        SQLALCHEMY_DATABASE_URI="sqlite:///file_manager.sqlite3",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE="sqlalchemy",
        SESSION_SQLALCHEMY_TABLE="sessions",
        SESSION_COOKIE_NAME="sfm_session",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_PATH="/",
        SESSION_PERMANENT=True,
        SESSION_ID_LENGTH=32,
        SESSION_SERIALIZATION_FORMAT="msgpack",
        SESSION_CLEANUP_N_REQUESTS=100,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=15),
        SESSION_REFRESH_EACH_REQUEST=True,
        AUTH_IDLE_SECONDS=15 * 60,
        AUTH_ABSOLUTE_SECONDS=2 * 60 * 60,
        WTF_CSRF_TIME_LIMIT=15 * 60,
        MAX_CONTENT_LENGTH=16 * 1024,
        UPLOAD_MAX_BYTES=5 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=128 * 1024,
        MAX_FORM_PARTS=8,
        RATELIMIT_HEADERS_ENABLED=True,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(mode=0o700, parents=True, exist_ok=True)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = load_or_create_secret(app.instance_path)
    init_storage(app)

    db.init_app(app)
    app.config["SESSION_SQLALCHEMY"] = db
    server_sessions.init_app(app)
    with app.app_context():
        db.create_all()

    @app.before_request
    def check_request_and_session():
        g.user = None
        if not request.is_secure:
            abort(400, description="Open this application using HTTPS.")
        if request.endpoint != "static":
            load_current_user()
        if request.endpoint in {
            "file_routes.upload", "file_routes.download",
            "file_routes.confirm_delete", "file_routes.delete",
        }:
            # Authenticate before rate-limit keys or POST form parsing use the account.
            if g.user is None:
                return redirect(url_for("auth.login"), code=303)
        if request.endpoint == "file_routes.upload":
            # Raise only the upload limit before Flask-WTF parses the body.
            request.max_content_length = app.config["UPLOAD_MAX_BYTES"] + 64 * 1024

    csrf.init_app(app)
    limiter.init_app(app)
    app.register_blueprint(auth)
    app.register_blueprint(file_routes)

    @app.get("/")
    def index():
        if g.user is not None:
            return redirect(url_for("files"), code=303)
        return render_template("index.html")

    @app.get("/files")
    @login_required
    def files():
        return render_file_list()

    @app.errorhandler(CSRFError)
    def invalid_form(error):
        return render_template(
            "error.html", title="Please reopen the form",
            message="This form is missing a valid security token or has expired. Open the page again and retry.",
        ), 400

    @app.errorhandler(429)
    def too_many_attempts(error):
        return render_template(
            "error.html", title="Too many attempts",
            message="Please wait a minute before trying again.",
        ), 429

    @app.errorhandler(413)
    def oversized_request(error):
        if request.endpoint == "file_routes.upload":
            message = "Choose one file of at most 5 MiB and submit it using the upload form."
        else:
            message = "The submitted form exceeds the allowed size."
        return render_template(
            "error.html", title="Request too large",
            message=message,
        ), 413

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'none'; "
            "style-src 'self'; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # Same-origin form submissions need a Referer for Flask-WTF's HTTPS check.
        response.headers["Referrer-Policy"] = "same-origin"
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
