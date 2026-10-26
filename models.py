"""Database records for accounts and uploaded-file metadata."""

from datetime import datetime, timezone
import time

from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))


class StoredFile(db.Model):
    __tablename__ = "files"

    id = db.Column(db.String(32), primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(180), nullable=False)
    content_type = db.Column(db.String(40), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.Integer, nullable=False, default=lambda: int(time.time()))

    @property
    def uploaded_utc(self):
        return datetime.fromtimestamp(self.created_at, timezone.utc).strftime("%Y-%m-%d %H:%M")
