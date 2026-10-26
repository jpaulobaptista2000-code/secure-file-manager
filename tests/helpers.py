"""One test application per process, with fresh database/storage for each test."""

import atexit
from pathlib import Path
import re
import tempfile
import unittest

from app import create_app
from extensions import db, limiter

BASE_URL = "https://localhost"
PASSWORD = "a test passphrase with spaces"
_directory = None
_app = None


def cleanup():
    if _app is not None:
        with _app.app_context():
            db.session.remove()
            db.engine.dispose()
    if _directory is not None:
        _directory.cleanup()


atexit.register(cleanup)


class WebTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _directory, _app
        # Flask-Session 0.8 creates a SQLAlchemy model on each initialization.
        if _app is None:
            _directory = tempfile.TemporaryDirectory()
            _app = create_app({"TESTING": True}, instance_path=_directory.name)
        cls.app = _app

    def setUp(self):
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            limiter.reset()
        for name in ("storage", "keys"):
            for path in (Path(self.app.instance_path) / name).iterdir():
                path.unlink()
        self.client = self.app.test_client()

    def get(self, path, client=None):
        return (client or self.client).get(path, base_url=BASE_URL)

    def post(self, path, data, client=None, referer=None, **kwargs):
        response = (client or self.client).post(
            path, data=data, base_url=BASE_URL,
            headers={"Referer": referer or BASE_URL + path}, **kwargs,
        )
        response.get_data()
        # The test client can spool its outgoing multipart body; close that input.
        response.request.environ["wsgi.input"].close()
        return response

    def token(self, path, client=None):
        response = self.get(path, client)
        self.assertEqual(response.status_code, 200)
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def register(self, username="alice", password=PASSWORD, client=None):
        return self.post("/register", {
            "username": username, "password": password, "confirm_password": password,
            "csrf_token": self.token("/register", client),
        }, client)

    def login(self, username="alice", password=PASSWORD, client=None):
        return self.post("/login", {
            "username": username, "password": password,
            "csrf_token": self.token("/login", client),
        }, client)

    def signed_in(self):
        self.assertEqual(self.register().status_code, 303)
        self.assertEqual(self.login().status_code, 303)

    def assert_login_required(self, client=None):
        response = self.get("/files", client)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/login")
