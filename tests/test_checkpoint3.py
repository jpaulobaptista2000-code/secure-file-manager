"""Checkpoint 3 attack demonstrations and error/logging regression checks.

All accounts, files, payloads and failures are disposable local test fixtures.
"""

from html.parser import HTMLParser
from io import BytesIO, StringIO
import json
import logging
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import event

from audit import PrivateRotatingHandler, SecurityFormatter
from extensions import db
from models import StoredFile, User
from tests.helpers import BASE_URL, PASSWORD, WebTestCase


class TagCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


class Checkpoint3Tests(WebTestCase):
    def setUp(self):
        super().setUp()
        self.log_path = Path(self.app.instance_path) / "logs" / "security.jsonl"
        self.log_offset = self.log_path.stat().st_size

    def log_text(self):
        with self.log_path.open("rb") as log:
            log.seek(self.log_offset)
            return log.read().decode("utf-8")

    def events(self):
        return [json.loads(line) for line in self.log_text().splitlines()]

    def upload(self, data=b"private test contents", name="notes.txt"):
        response = self.post("/files/upload", {
            "csrf_token": self.token("/files"), "file": (BytesIO(data), name),
        })
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            return db.session.execute(db.select(StoredFile)).scalar_one().id

    def test_csrf_missing_forged_and_foreign_tokens_block_every_post_form(self):
        """CSRF: all five state-changing forms reject missing/forged/foreign tokens."""
        self.signed_in()
        file_id = self.upload()
        other = self.app.test_client()
        tokens = [None, "forged", self.token("/login", other)]
        paths = ["/register", "/login", "/logout", "/files/upload", f"/files/{file_id}/delete"]
        for path in paths:
            for token in tokens:
                with self.subTest(path=path, token=token is not None):
                    fields = {} if token is None else {"csrf_token": token}
                    response = self.post(path, fields)
                    self.assertEqual(response.status_code, 400)
                    request_id = response.headers["X-Request-ID"]
                    self.assertTrue(any(e["event"] == "csrf_rejected" and e["request_id"] == request_id
                                        for e in self.events()))
        self.assertEqual(self.get("/files").status_code, 200)
        self.assertEqual(self.get(f"/files/{file_id}/download").data, b"private test contents")
        with self.app.app_context():
            self.assertEqual(db.session.query(User).count(), 1)
            self.assertEqual(db.session.query(StoredFile).count(), 1)

    def test_cross_site_delete_with_valid_token_is_rejected(self):
        """CSRF: valid token plus https://attacker.example/ Referer returns 400."""
        self.signed_in()
        file_id = self.upload()
        response = self.post(f"/files/{file_id}/delete", {"csrf_token": self.token("/files")},
                             referer="https://attacker.example/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get(f"/files/{file_id}/download").status_code, 200)

    def test_reflected_xss_is_text_not_an_html_element(self):
        """XSS: a username containing an img/onerror payload creates no img element."""
        payload = '\"><img src=x onerror=alert(1)>'
        response = self.login(payload)
        self.assertEqual(response.status_code, 401)
        parser = TagCollector()
        parser.feed(response.get_data(as_text=True))
        self.assertNotIn("img", parser.tags)
        self.assertNotIn("script", parser.tags)
        self.assertIn(b"&lt;img", response.data)
        self.assertIn("script-src 'none'", response.headers["Content-Security-Policy"])

    def test_stored_xss_is_escaped_on_both_filename_pages(self):
        """XSS: even poisoned database metadata is escaped in list and delete views."""
        self.signed_in()
        file_id = self.upload()
        with self.app.app_context():
            db.session.get(StoredFile, file_id).filename = '<img src=x onerror="alert(1)">.txt'
            db.session.commit()
        for path in ["/files", f"/files/{file_id}/confirm-delete"]:
            response = self.get(path)
            parser = TagCollector()
            parser.feed(response.get_data(as_text=True))
            self.assertNotIn("img", parser.tags)
            self.assertIn(b"&lt;img", response.data)

    def test_html_in_a_text_upload_is_only_downloaded_as_an_attachment(self):
        """XSS: HTML in a TXT body is stored as data and downloaded, never previewed."""
        self.signed_in()
        payload = b'<script>alert("test")</script>'
        file_id = self.upload(payload)
        self.assertNotIn(payload, self.get("/files").data)
        response = self.get(f"/files/{file_id}/download")
        self.assertEqual(response.data, payload)
        self.assertEqual(response.content_type, "application/octet-stream")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_sql_injection_payloads_cannot_authenticate_or_remove_accounts(self):
        """SQLi: boolean, comment and DROP TABLE login inputs do not grant access."""
        self.register()
        for payload in ["' OR '1'='1", "admin'--", "'; DROP TABLE users;--"]:
            response = self.login(payload, payload)
            self.assertEqual(response.status_code, 401)
            self.assert_login_required()
        # A valid username ensures the password payload reaches the hash verifier.
        self.assertEqual(self.login("alice", "' OR '1'='1").status_code, 401)
        self.assert_login_required()
        with self.app.app_context():
            self.assertEqual(db.session.query(User).count(), 1)

    def test_real_login_query_sends_username_as_a_bound_parameter(self):
        """SQLi defence: capture the executed login query and its separate parameters."""
        self.register()
        statements = []

        def capture(connection, cursor, statement, parameters, context, executemany):
            if "FROM users" in statement and "users.username" in statement:
                statements.append((statement, parameters))

        with self.app.app_context():
            engine = db.engine
            event.listen(engine, "before_cursor_execute", capture)
            try:
                self.assertEqual(self.login().status_code, 303)
            finally:
                event.remove(engine, "before_cursor_execute", capture)
        self.assertTrue(statements)
        self.assertTrue(any("alice" in parameters for _, parameters in statements))
        for statement, _ in statements:
            self.assertIn("?", statement)
            self.assertNotIn("alice", statement)

    def test_foreign_file_access_is_denied_and_recorded_without_disclosing_its_name(self):
        """IDOR: Bob's valid session/token cannot download, confirm or delete Alice's file."""
        self.signed_in()
        file_id = self.upload(name="alice-confidential.txt")
        bob = self.app.test_client()
        self.register("bob", client=bob)
        self.login("bob", client=bob)
        token = self.token("/files", bob)
        for suffix in ("download", "confirm-delete", "delete"):
            path = f"/files/{file_id}/{suffix}"
            response = self.post(path, {"csrf_token": token}, bob) if suffix == "delete" else self.get(path, bob)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn(b"alice-confidential", response.data)
        denied = [e for e in self.events() if e["event"] == "file_access_denied"]
        self.assertEqual(len(denied), 3)
        self.assertTrue(all(e["file_id"] == file_id and e["user_id"] == 2 for e in denied))
        self.assertNotIn("alice-confidential", self.log_text())
        self.assertEqual(self.get(f"/files/{file_id}/download").status_code, 200)

    def test_unexpected_exception_returns_generic_500_and_redacted_json_log(self):
        """Errors: a simulated exception containing secrets leaks neither text nor traceback."""
        self.register()
        token = self.token("/login")
        secret = "secret-value /private/database.sqlite SELECT password FROM users"
        with patch.dict(self.app.config, {"PROPAGATE_EXCEPTIONS": False}):
            with patch("auth.password_matches", side_effect=RuntimeError(secret)):
                response = self.post("/login", {"username": "alice", "password": PASSWORD, "csrf_token": token})
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Something went wrong", response.data)
        self.assertNotIn(secret.encode(), response.data)
        self.assertNotIn(b"Traceback", response.data)
        self.assertNotIn(secret, self.log_text())
        self.assertNotIn(PASSWORD, self.log_text())
        errors = [e for e in self.events() if e["event"] == "application_error"]
        self.assertTrue(any(e.get("error_type") == "RuntimeError" for e in errors))
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assert_login_required()
        self.assertEqual(self.login().status_code, 303)

    def test_bad_request_and_wrong_method_keep_safe_pages_and_http_semantics(self):
        """Errors: 400/404/405 responses stay generic and preserve the Allow header."""
        self.assertEqual(self.client.get("/login").status_code, 400)
        payload = "do-not-reflect-this-unknown-path"
        response = self.get("/" + payload)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(payload.encode(), response.data)
        response = self.get("/logout")
        self.assertEqual(response.status_code, 405)
        self.assertIn("POST", response.headers["Allow"])
        self.assertNotIn(payload, self.log_text())

    def test_structured_logs_correlate_events_and_omit_secrets_and_untrusted_input(self):
        """Logs: passwords, cookies, CSRF tokens, filenames, bodies and CRLF input are absent."""
        self.register()
        token = self.token("/login")
        response = self.post("/login", {"username": "alice", "password": PASSWORD, "csrf_token": token})
        cookie = self.client.get_cookie("sfm_session").value
        file_id = self.upload(b"do-not-log-file-contents", name="do-not-log-filename.txt")
        self.get(f"/files/{file_id}/download")
        self.post(f"/files/{file_id}/delete", {"csrf_token": self.token("/files")})
        self.post("/logout", {"csrf_token": self.token("/files")})
        forged = 'wrong\r\n{"event":"forged_event"}'
        self.login(forged)
        self.get("/login?secret=do-not-log-query")
        for value in [PASSWORD, token, cookie, "do-not-log-file-contents", "do-not-log-filename.txt",
                      "forged_event", "do-not-log-query"]:
            self.assertNotIn(value, self.log_text())
        entries = self.events()
        names = {entry["event"] for entry in entries}
        self.assertTrue({"registration_succeeded", "login_succeeded", "file_uploaded",
                         "file_download_prepared", "file_deleted", "logout", "login_failed"} <= names)
        request_id = response.headers["X-Request-ID"]
        self.assertRegex(request_id, r"^[0-9a-f]{32}$")
        related = [entry for entry in entries if entry.get("request_id") == request_id]
        self.assertTrue(any(e["event"] == "login_succeeded" and e["user_id"] == 1 for e in related))
        self.assertTrue(any(e["event"] == "request_completed" and e["status"] == 303 for e in related))

    def test_request_id_is_generated_by_the_server(self):
        """Logs: a supplied X-Request-ID cannot impersonate another log correlation ID."""
        response = self.client.get("/login", base_url=BASE_URL, headers={"X-Request-ID": "attacker-value"})
        self.assertRegex(response.headers["X-Request-ID"], r"^[0-9a-f]{32}$")
        self.assertNotIn("attacker-value", self.log_text())

    def test_log_write_failure_does_not_break_login_or_print_sensitive_details(self):
        """Logs: simulated full-disk failure keeps login working and emits a safe warning."""
        self.register()
        handler = self.app.logger.handlers[0]
        stderr = StringIO()
        with patch.object(handler, "shouldRollover", side_effect=OSError("secret error detail")):
            with patch("sys.stderr", stderr):
                response = self.login()
        self.assertEqual(response.status_code, 303)
        self.assertIn('"event":"logging_failed"', stderr.getvalue())
        self.assertNotIn("secret error detail", stderr.getvalue())
        self.assertNotIn(PASSWORD, stderr.getvalue())
        self.assertEqual(self.get("/files").status_code, 200)

    def test_log_rotation_is_bounded_and_keeps_valid_json(self):
        """Logs: size-based rotation retains only the configured backup count."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "security.jsonl"
            handler = PrivateRotatingHandler(path, maxBytes=300, backupCount=3)
            handler.setFormatter(SecurityFormatter())
            try:
                for _ in range(30):
                    record = logging.LogRecord("test", logging.INFO, "", 0, "sensitive raw message", (), None)
                    record.security_event = "rotation_test"
                    handler.handle(record)
            finally:
                handler.close()
            files = list(Path(directory).iterdir())
            self.assertEqual(len(files), 4)
            for file in files:
                text = file.read_text()
                self.assertNotIn("sensitive raw message", text)
                for line in text.splitlines():
                    self.assertEqual(json.loads(line)["event"], "rotation_test")

    def test_security_log_has_no_public_route(self):
        for path in ["/instance/logs/security.jsonl", "/logs/security.jsonl", "/static/../instance/logs/security.jsonl"]:
            self.assertEqual(self.get(path).status_code, 404)

    @unittest.skipIf(os.name == "nt", "POSIX mode bits; Windows uses directory ACLs")
    def test_security_log_has_private_posix_permissions(self):
        self.assertEqual(stat.S_IMODE(self.log_path.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.log_path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
