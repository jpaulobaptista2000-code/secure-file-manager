"""Owner-checked uploads, listing, downloads and confirmed deletion."""

from io import BytesIO
import re
import secrets

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template,
    request, send_file, url_for,
)
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from encrypted_storage import FileUnavailableError, decrypt_file, delete_file, store_file
from extensions import db, limiter
from models import FileDeletion, StoredFile
from security import login_required

file_routes = Blueprint("file_routes", __name__)


def render_file_list(error=None, status=200):
    page = db.paginate(
        db.select(StoredFile).where(StoredFile.owner_id == g.user.id)
        .order_by(StoredFile.created_at.desc(), StoredFile.id.desc()),
        per_page=20, max_per_page=20, error_out=False,
    )
    pending_ids = set(db.session.scalars(
        db.select(FileDeletion.file_id).where(FileDeletion.file_id.in_([file.id for file in page.items]))
    ))
    return render_template(
        "files.html", page=page, pending_ids=pending_ids, error=error,
        upload_limit_mib=current_app.config["UPLOAD_MAX_BYTES"] // (1024 * 1024),
    ), status


def validate_upload(upload):
    original = upload.filename or ""
    if not original or len(original) > 180:
        raise ValueError("Choose a file with a name of at most 180 characters.")
    if any(char in original for char in ("/", "\\", ":")) or any(ord(c) < 32 or ord(c) == 127 for c in original):
        raise ValueError("The filename must not contain paths or control characters.")
    filename = secure_filename(original)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in {"pdf", "txt"}:
        raise ValueError("Only PDF and TXT files are accepted.")
    data = upload.read(current_app.config["UPLOAD_MAX_BYTES"] + 1)
    if not data:
        raise ValueError("Empty files are not accepted.")
    if len(data) > current_app.config["UPLOAD_MAX_BYTES"]:
        raise RequestEntityTooLarge()
    # Content-Type is supplied by the browser, so it cannot prove the file type.
    if extension == "pdf":
        if not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)[\r\n]", data) or not data.rstrip().endswith(b"%%EOF"):
            raise ValueError("The file does not have the expected PDF header and end marker.")
        content_type = "application/pdf"
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("TXT files must use UTF-8 encoding.") from None
        if any((ord(c) < 32 and c not in "\t\r\n\f") or 127 <= ord(c) <= 159 for c in text):
            raise ValueError("The TXT file contains binary control characters.")
        content_type = "text/plain"
    return filename, content_type, data


@file_routes.post("/files/upload")
@login_required
@limiter.limit("10 per minute", key_func=lambda: str(g.user.id))
def upload():
    incoming = list(request.files.items(multi=True))
    if len(incoming) != 1 or incoming[0][0] != "file":
        return render_file_list("Choose exactly one PDF or TXT file.", 400)
    try:
        filename, content_type, data = validate_upload(incoming[0][1])
    except ValueError as error:
        return render_file_list(str(error), 400)
    record = StoredFile(
        id=secrets.token_hex(16), owner_id=g.user.id, filename=filename,
        content_type=content_type, size_bytes=len(data),
    )
    try:
        store_file(record, data)
    except (OSError, SQLAlchemyError):
        current_app.logger.error("Upload could not be saved; storage or database operation failed.")
        return render_template(
            "error.html", title="Upload could not be saved",
            message="The file could not be saved. Please try again later.",
        ), 503
    flash("File uploaded and encrypted successfully.", "success")
    return redirect(url_for("files"), code=303)


def owned_file(file_id, include_pending=False):
    """Scope the lookup by the authenticated account before any storage access."""
    if not re.fullmatch(r"[0-9a-f]{32}", file_id):
        abort(404)
    query = db.select(StoredFile).where(
        StoredFile.id == file_id, StoredFile.owner_id == g.user.id,
    )
    if not include_pending:
        query = query.where(~db.exists().where(FileDeletion.file_id == StoredFile.id))
    record = db.session.execute(query).scalar_one_or_none()
    if record is None:
        abort(404)
    return record


@file_routes.errorhandler(404)
def file_not_found(error):
    return render_template(
        "error.html", title="File not found",
        message="This file is not available in your account.",
    ), 404


@file_routes.get("/files/<file_id>/download")
@login_required
@limiter.limit("30 per minute", key_func=lambda: str(g.user.id))
def download(file_id):
    record = owned_file(file_id)
    try:
        plaintext = decrypt_file(record)
    except FileUnavailableError:
        current_app.logger.error("A stored file could not be read or authenticated.")
        return render_template(
            "error.html", title="Download unavailable",
            message="This file could not be opened safely. Please try again later.",
        ), 503
    # Never render uploads inline or write a decrypted temporary file.
    return send_file(
        BytesIO(plaintext), mimetype="application/octet-stream",
        as_attachment=True, download_name=record.filename,
        conditional=False, etag=False, max_age=0,
    )


@file_routes.get("/files/<file_id>/confirm-delete")
@login_required
def confirm_delete(file_id):
    record = owned_file(file_id, include_pending=True)
    pending = db.session.get(FileDeletion, record.id) is not None
    return render_template("confirm_delete.html", file=record, pending=pending)


@file_routes.post("/files/<file_id>/delete")
@login_required
@limiter.limit("10 per minute", key_func=lambda: str(g.user.id))
def delete(file_id):
    record = owned_file(file_id, include_pending=True)
    try:
        delete_file(record)
    except (OSError, SQLAlchemyError):
        current_app.logger.error("File deletion could not be completed.")
        return render_template(
            "error.html", title="Deletion incomplete",
            message="The file could not be fully removed. Return to My files and try deleting it again.",
        ), 503
    flash("File deleted successfully.", "success")
    return redirect(url_for("files"), code=303)
