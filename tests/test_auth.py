"""Exercise real forms, cookies and database sessions in an isolated directory."""

from datetime import datetime, timedelta, timezone
import re
import tempfile
import time
import unittest
from unittest.mock import patch

from app import create_app
from extensions import db, limiter
from models import User
from security import password_hasher

BASE_URL = "https://localhost"
PASSWORD = "a test passphrase with spaces"


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.app = create_app({"TESTING": True}, instance_path=cls.directory.name)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()
        cls.directory.cleanup()

    def setUp(self):
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            limiter.reset()
        self.client = self.app.test_client()

    def get(self, path, client=None):
        return (client or self.client).get(path, base_url=BASE_URL)

    def post(self, path, data, client=None, referer=None, **kwargs):
        return (client or self.client).post(
            path, data=data, base_url=BASE_URL,
            headers={"Referer": referer or BASE_URL + path}, **kwargs,
        )

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

    def test_registration_hashes_password_with_unique_salts(self):
        self.assertEqual(self.register().status_code, 303)
        self.assertEqual(self.register("bob").status_code, 303)
        with self.app.app_context():
            users = db.session.execute(db.select(User).order_by(User.id)).scalars().all()
            self.assertEqual(len(users), 2)
            for user in users:
                self.assertTrue(user.password_hash.startswith("$argon2id$"))
                self.assertNotIn(PASSWORD, user.password_hash)
                self.assertTrue(password_hasher.verify(user.password_hash, PASSWORD))
            self.assertNotEqual(users[0].password_hash, users[1].password_hash)

    def test_duplicate_username_is_case_insensitive(self):
        self.assertEqual(self.register("Alice").status_code, 303)
        self.assertEqual(self.register("ALICE").status_code, 409)
        with self.app.app_context():
            self.assertEqual(db.session.query(User).count(), 1)

    def test_server_validates_registration_without_browser_checks(self):
        for username, password in [("../alice", PASSWORD), ("alice", "short"), ("alice", "x" * 129)]:
            with self.subTest(username=username, length=len(password)):
                self.assertEqual(self.register(username, password).status_code, 400)
        response = self.post("/register", {
            "username": "alice", "password": PASSWORD, "confirm_password": "different",
            "csrf_token": self.token("/register"),
        })
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertEqual(db.session.query(User).count(), 0)

    def test_unknown_user_and_wrong_password_have_same_error(self):
        self.register()
        for name in ["alice", "unknown"]:
            response = self.login(name, "a deliberately incorrect password")
            self.assertEqual(response.status_code, 401)
            self.assertIn(b"Incorrect username or password.", response.data)
            self.assert_login_required()

    def test_login_rotates_session_and_prelogin_cookie_cannot_access_files(self):
        self.register()
        self.token("/login")
        old_id = self.client.get_cookie("sfm_session").value
        response = self.login()
        self.assertEqual(response.status_code, 303)
        new_id = self.client.get_cookie("sfm_session").value
        self.assertNotEqual(old_id, new_id)
        self.assertNotIn("alice", new_id)
        other = self.app.test_client()
        other.set_cookie("sfm_session", old_id)
        self.assert_login_required(other)
        private = self.get("/files")
        self.assertEqual(private.status_code, 200)
        self.assertIn(b"Welcome, alice.", private.data)
        self.assertEqual(private.headers["Cache-Control"], "no-store")
        cookie = response.headers["Set-Cookie"]
        for flag in ["Secure", "HttpOnly", "SameSite=Lax", "Path=/"]:
            self.assertIn(flag, cookie)

    def test_logout_revokes_cookie_replay_and_protected_access(self):
        self.signed_in()
        old_id = self.client.get_cookie("sfm_session").value
        response = self.post("/logout", {"csrf_token": self.token("/files")})
        self.assertEqual(response.status_code, 303)
        self.assertIsNone(self.client.get_cookie("sfm_session"))
        self.assert_login_required()
        other = self.app.test_client()
        other.set_cookie("sfm_session", old_id)
        self.assert_login_required(other)

    def test_missing_csrf_rejected_for_all_state_changes(self):
        for path in ["/register", "/login", "/logout"]:
            with self.subTest(path=path):
                self.assertEqual(self.post(path, {"username": "alice", "password": PASSWORD}).status_code, 400)
        self.signed_in()
        self.assertEqual(self.post("/logout", {}).status_code, 400)
        self.assertEqual(self.get("/files").status_code, 200)
        self.assertEqual(self.get("/logout").status_code, 405)

    def test_other_sessions_csrf_token_and_cross_site_referer_rejected(self):
        self.register()
        other = self.app.test_client()
        foreign_token = self.token("/login", other)
        self.token("/login")
        data = {"username": "alice", "password": PASSWORD, "csrf_token": foreign_token}
        self.assertEqual(self.post("/login", data).status_code, 400)
        data["csrf_token"] = self.token("/login")
        self.assertEqual(self.post("/login", data, referer="https://attacker.example/").status_code, 400)
        self.assert_login_required()

    def test_idle_expiry_is_enforced_server_side(self):
        self.signed_in()
        with self.client.session_transaction(base_url=BASE_URL) as saved:
            saved["last_seen"] = int(time.time()) - 901
        self.assert_login_required()

    def test_absolute_expiry_applies_even_with_recent_activity(self):
        self.signed_in()
        with self.client.session_transaction(base_url=BASE_URL) as saved:
            saved["login_at"] = int(time.time()) - 7201
            saved["last_seen"] = int(time.time())
        self.assert_login_required()

    def test_expired_database_session_is_rejected(self):
        self.signed_in()
        with self.app.app_context():
            session_model = self.app.session_interface.sql_session_model
            for saved in db.session.query(session_model).all():
                saved.expiry = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
            db.session.commit()
        self.assert_login_required()

    def test_forged_cookie_cannot_create_authenticated_session(self):
        self.register()
        self.client.set_cookie("sfm_session", '{"user_id":1,"is_admin":true}')
        self.assert_login_required()

    def test_login_rate_limit_survives_new_browser_sessions(self):
        self.register()
        for _ in range(5):
            self.assertEqual(self.login(password="wrong password").status_code, 401)
        other = self.app.test_client()
        response = self.login(client=other)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)
        self.assert_login_required(other)

    def test_sql_and_html_payloads_do_not_grant_access_or_render_as_markup(self):
        payload = '\"><script>alert(1)</script>'
        response = self.login(payload, PASSWORD)
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(b"<script>", response.data)
        self.assertEqual(self.login("' OR '1'='1", PASSWORD).status_code, 401)
        self.assert_login_required()

    def test_invalid_password_hash_fails_closed(self):
        self.register()
        with self.app.app_context():
            user = db.session.execute(db.select(User)).scalar_one()
            user.password_hash = "corrupt hash"
            db.session.commit()
        self.assertEqual(self.login().status_code, 401)
        self.assert_login_required()

    def test_credential_check_exception_never_grants_access(self):
        self.register()
        token = self.token("/login")
        with patch("auth.password_matches", side_effect=RuntimeError("simulated check failure")):
            with self.assertRaises(RuntimeError):
                self.post("/login", {"username": "alice", "password": PASSWORD, "csrf_token": token})
        self.assert_login_required()

    def test_http_and_large_requests_are_rejected_and_private_files_not_served(self):
        self.assertEqual(self.client.get("/login").status_code, 400)
        self.assertEqual(self.post("/login", {"password": "x" * 20000}).status_code, 413)
        for path in ["/instance/secret.key", "/instance/file_manager.sqlite3", "/security.py"]:
            self.assertEqual(self.get(path).status_code, 404)

    def test_session_data_and_password_are_not_in_cookie(self):
        self.signed_in()
        cookie = self.client.get_cookie("sfm_session").value
        self.assertRegex(cookie, r"^[A-Za-z0-9_-]{43}$")
        with self.app.app_context():
            saved = db.session.query(self.app.session_interface.sql_session_model).all()
            self.assertTrue(saved)
            self.assertFalse(any(PASSWORD.encode() in record.data for record in saved))


if __name__ == "__main__":
    unittest.main()
