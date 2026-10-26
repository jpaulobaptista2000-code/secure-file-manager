"""AES-256-GCM storage. Only ciphertext and random keys are written to disk."""

import json
import os
from pathlib import Path
import re
import secrets
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from flask import current_app
from sqlalchemy.dialects.sqlite import insert

from extensions import db
from models import FileDeletion, StoredFile

MAGIC = b"SFM1"
NONCE_BYTES = 12


class FileUnavailableError(Exception):
    """Missing or unauthenticated stored data must never be returned as a download."""


def init_storage(app):
    # Python 3.13 added Windows ACL handling for directory mode 0o700.
    if os.name == "nt" and sys.version_info < (3, 13):
        raise RuntimeError("Use Python 3.13 or newer on Windows for private storage permissions.")
    for name in ("storage", "keys"):
        directory = Path(app.instance_path) / name
        if directory.is_symlink() or directory.is_junction():
            raise RuntimeError("Private storage folders must not be symbolic links or junctions.")
        directory.mkdir(mode=0o700, exist_ok=True)
        if os.name != "nt":
            directory.chmod(0o700)


def storage_paths(file_id):
    # Never interpret a filename or client-supplied path as a storage location.
    if not re.fullmatch(r"[0-9a-f]{32}", file_id):
        raise ValueError("Invalid internal file identifier.")
    instance = Path(current_app.instance_path)
    return instance / "storage" / (file_id + ".enc"), instance / "keys" / (file_id + ".key")


def associated_data(record):
    """Bind the encrypted content to its owner and metadata (these remain readable)."""
    return json.dumps({
        "version": 1, "id": record.id, "owner_id": record.owner_id,
        "filename": record.filename, "content_type": record.content_type,
        "size_bytes": record.size_bytes,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")


def store_file(record, plaintext):
    """Store a new file and its metadata, cleaning up on a handled failure."""
    key = AESGCM.generate_key(bit_length=256)
    nonce = secrets.token_bytes(NONCE_BYTES)
    encrypted = MAGIC + nonce + AESGCM(key).encrypt(nonce, plaintext, associated_data(record))
    encrypted_path, key_path = storage_paths(record.id)
    created = []
    committed = False
    try:
        for path, contents in ((key_path, key), (encrypted_path, encrypted)):
            # Exclusive creation prevents collisions from overwriting existing data.
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            descriptor = os.open(path, flags, 0o600)
            created.append(path)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(contents)
                handle.flush()
                os.fsync(handle.fileno())
        db.session.add(record)
        db.session.commit()
        committed = True
    finally:
        if not committed:
            try:
                db.session.rollback()
            finally:
                for path in reversed(created):
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        current_app.logger.error("Could not remove an incomplete encrypted upload.")


def decrypt_file(record):
    """Authenticate the complete bounded file before returning any plaintext."""
    try:
        if not 0 < record.size_bytes <= current_app.config["UPLOAD_MAX_BYTES"]:
            raise ValueError("Invalid stored size.")
        encrypted_path, key_path = storage_paths(record.id)
        if encrypted_path.is_symlink() or key_path.is_symlink():
            raise ValueError("Storage files must not be symbolic links.")
        expected_size = len(MAGIC) + NONCE_BYTES + record.size_bytes + 16
        with key_path.open("rb") as handle:
            key = handle.read(33)
        with encrypted_path.open("rb") as handle:
            encrypted = handle.read(expected_size + 1)
        if len(key) != 32 or len(encrypted) != expected_size or encrypted[:4] != MAGIC:
            raise ValueError("Invalid encrypted format.")
        plaintext = AESGCM(key).decrypt(
            encrypted[4:4 + NONCE_BYTES], encrypted[4 + NONCE_BYTES:], associated_data(record),
        )
        return plaintext
    except (OSError, ValueError, InvalidTag) as error:
        raise FileUnavailableError() from error


def delete_file(record):
    """Record the intent first, then remove private data; failures remain retryable."""
    file_id = record.id
    encrypted_path, key_path = storage_paths(file_id)
    try:
        # Downloads exclude marked files. The marker survives process restarts.
        # A repeated/concurrent owner request can safely reuse an existing marker.
        db.session.execute(insert(FileDeletion).values(file_id=file_id).on_conflict_do_nothing())
        db.session.commit()
        key_path.unlink(missing_ok=True)
        encrypted_path.unlink(missing_ok=True)
        db.session.execute(db.delete(FileDeletion).where(FileDeletion.file_id == file_id))
        db.session.execute(db.delete(StoredFile).where(StoredFile.id == file_id))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
