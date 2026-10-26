"""Shared Flask extensions, configured by create_app()."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
server_sessions = Session()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
