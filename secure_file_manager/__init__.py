"""Checkpoint 1 application factory. Authentication and storage are planned."""

from flask import Flask, jsonify, render_template
from werkzeug.exceptions import HTTPException


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DEBUG=False,
        TRUSTED_HOSTS=["localhost", "127.0.0.1"],
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=16 * 1024,
        MAX_FORM_PARTS=8,
    )
    if test_config:
        app.config.update(test_config)

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self'; "
            "script-src 'none'; base-uri 'none'; object-src 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok", stage="checkpoint-1-foundation")

    @app.errorhandler(HTTPException)
    def request_error(error):
        # Preserve protocol headers, e.g. Allow for a 405 response.
        response = error.get_response()
        response.data = app.json.dumps({"error": error.name})
        response.content_type = "application/json"
        return response

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify(error="Internal server error"), 500

    return app
