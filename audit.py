"""Small, private JSON security log; never serialize raw requests or exceptions."""

from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

from flask import current_app, g, has_request_context, request


class SecurityFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "security_event", "application_error"),
        }
        if has_request_context():
            entry.update(
                request_id=getattr(g, "request_id", None),
                endpoint=request.endpoint or "unmatched",
                method=request.method,
                user_id=getattr(g, "audit_user_id", None),
            )
        # Only these application-controlled fields may be recorded. In particular,
        # getMessage()/formatException() can expose SQL parameters and credentials.
        for name in ("status", "reason", "file_id"):
            value = getattr(record, name, None)
            if value is not None:
                entry[name] = value
        if record.exc_info:
            entry["error_type"] = record.exc_info[0].__name__
        return json.dumps(entry, ensure_ascii=True, separators=(",", ":"))


class PrivateRotatingHandler(RotatingFileHandler):
    def _open(self):
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(self.baseFilename, flags, 0o600)
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        return os.fdopen(descriptor, "a", encoding="utf-8")

    def handleError(self, record):
        # A full disk must not expose record contents through logging's own error
        # traceback, or turn a completed upload/deletion into an apparent failure.
        try:
            sys.stderr.write('{"level":"ERROR","event":"logging_failed"}\n')
        except (OSError, ValueError):
            pass


def init_audit_logging(app):
    path = Path(app.instance_path) / "logs" / "security.jsonl"
    if path.is_symlink():
        raise RuntimeError("The security log must not be a symbolic link.")
    handler = PrivateRotatingHandler(path, maxBytes=1024 * 1024, backupCount=3)
    handler.setFormatter(SecurityFormatter())
    for previous in app.logger.handlers[:]:
        app.logger.removeHandler(previous)
        previous.close()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False
    app.logger.info("", extra={"security_event": "application_started"})


def audit_event(event, *, level=logging.INFO, status=None, reason=None, file_id=None):
    """Call with fixed event/reason codes and validated internal IDs, never input."""
    current_app.logger.log(level, "", extra={
        "security_event": event, "status": status, "reason": reason, "file_id": file_id,
    })
