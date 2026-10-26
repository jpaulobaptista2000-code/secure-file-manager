"""Check ownership, authenticated downloads and retryable deletion through HTTP."""

from io import BytesIO
from pathlib import Path
import secrets
import unittest
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from encrypted_storage import storage_paths
from extensions import db, limiter
from models import FileDeletion, StoredFile
from tests.helpers import BASE_URL, WebTestCase
from tests.test_uploads import sample_pdf


class FileActionTests(WebTestCase):
    def setUp(self):
        super().setUp()
        self.signed_in()

    def upload_file(self, contents=b"An original private document.\r\n", name="private.txt", client=None):
        response = self.post("/files/upload", {
            "csrf_token": self.token("/files", client), "file": (BytesIO(contents), name),
        }, client)
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            return db.session.execute(db.select(StoredFile).where(StoredFile.filename == name)).scalar_one().id

    def paths(self, file_id):
        with self.app.app_context():
            return storage_paths(file_id)

    def download(self, file_id, client=None):
        return self.get(f"/files/{file_id}/download", client)

    def remove(self, file_id, client=None, extra=None):
        fields = {"csrf_token": self.token("/files", client)}
        fields.update(extra or {})
        return self.post(f"/files/{file_id}/delete", fields, client)

    def other_account(self):
        other = self.app.test_client()
        self.assertEqual(self.register("bob", client=other).status_code, 303)
        self.assertEqual(self.login("bob", client=other).status_code, 303)
        return other

    def assert_deleted(self, file_id):
        with self.app.app_context():
            self.assertIsNone(db.session.get(StoredFile, file_id))
            self.assertIsNone(db.session.get(FileDeletion, file_id))
        for path in self.paths(file_id):
            self.assertFalse(path.exists())

    def assert_pending(self, file_id):
        with self.app.app_context():
            self.assertIsNotNone(db.session.get(StoredFile, file_id))
            self.assertIsNotNone(db.session.get(FileDeletion, file_id))
        self.assertEqual(self.download(file_id).status_code, 404)
        page = self.get("/files")
        self.assertIn(b"Deletion pending", page.data)
        self.assertIn(b"Retry delete", page.data)
        self.assertNotIn(f'/files/{file_id}/download'.encode(), page.data)

    def test_txt_and_pdf_download_exact_original_bytes_as_attachments(self):
        for data, name in [(b"\xef\xbb\xbfHello\r\nWorld\n", "private.txt"), (sample_pdf(), "document.pdf")]:
            with self.subTest(name=name):
                file_id = self.upload_file(data, name)
                encrypted, key = self.paths(file_id)
                before = (encrypted.read_bytes(), key.read_bytes())
                response = self.download(file_id)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, data)
                self.assertEqual(response.headers["Content-Type"], "application/octet-stream")
                self.assertIn("attachment;", response.headers["Content-Disposition"])
                self.assertIn(name, response.headers["Content-Disposition"])
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                self.assertNotIn("ETag", response.headers)
                self.assertEqual((encrypted.read_bytes(), key.read_bytes()), before)

    def test_maximum_size_file_downloads_without_truncation(self):
        data = b"x" * self.app.config["UPLOAD_MAX_BYTES"]
        file_id = self.upload_file(data)
        self.assertEqual(self.download(file_id).data, data)

    def test_foreign_account_cannot_download_confirm_or_delete_even_with_valid_csrf(self):
        file_id = self.upload_file()
        other = self.other_account()
        other_token = self.token("/files", other)
        with patch("encrypted_storage.storage_paths", side_effect=AssertionError("unauthorized storage access")):
            for suffix in ("download", "confirm-delete"):
                response = self.get(f"/files/{file_id}/{suffix}", other)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(b"private.txt", response.data)
            self.assertEqual(other.head(f"/files/{file_id}/download", base_url=BASE_URL).status_code, 404)
            response = self.post(f"/files/{file_id}/delete", {
                "csrf_token": other_token, "owner_id": "1", "file_id": file_id,
            }, other)
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.download(file_id).status_code, 200)

    def test_anonymous_and_revoked_sessions_cannot_use_file_links(self):
        file_id = self.upload_file()
        previous_cookie = self.client.get_cookie("sfm_session").value
        self.post("/logout", {"csrf_token": self.token("/files")})
        anonymous = self.app.test_client()
        replay = self.app.test_client()
        replay.set_cookie("sfm_session", previous_cookie)
        for client in (anonymous, replay):
            for suffix in ("download", "confirm-delete"):
                response = self.get(f"/files/{file_id}/{suffix}", client)
                self.assertEqual(response.status_code, 303)
                self.assertEqual(response.headers["Location"], "/login")
            self.assertEqual(self.post(f"/files/{file_id}/delete", {}, client).status_code, 303)
        for path in self.paths(file_id):
            self.assertTrue(path.exists())

    def test_unknown_and_malformed_ids_are_not_interpreted_as_paths_or_sql(self):
        self.upload_file()
        for file_id in [secrets.token_hex(16), "123", "A" * 32, "..", "'OR'1'='1"]:
            for suffix in ("download", "confirm-delete"):
                self.assertEqual(self.get(f"/files/{file_id}/{suffix}").status_code, 404)
            self.assertEqual(self.remove(file_id).status_code, 404)
        self.assertEqual(self.get("/files/..%2F..%2Finstance%2Fsecret.key/download").status_code, 404)

    def test_query_and_form_fields_cannot_select_another_file_or_owner(self):
        first = self.upload_file(b"first contents", "first.txt")
        second = self.upload_file(b"second contents", "second.txt")
        response = self.get(f"/files/{first}/download?file_id={second}&owner_id=99&path=instance/secret.key")
        self.assertEqual(response.data, b"first contents")
        self.assertEqual(self.remove(first, extra={"file_id": second, "owner_id": "99", "path": "instance/secret.key"}).status_code, 303)
        self.assert_deleted(first)
        self.assertEqual(self.download(second).data, b"second contents")

    def test_tampered_ciphertext_nonce_header_and_key_never_return_plaintext(self):
        plaintext = b"private marker that must not appear in an error"
        file_id = self.upload_file(plaintext)
        encrypted, key_path = self.paths(file_id)
        original, original_key = encrypted.read_bytes(), key_path.read_bytes()
        corruptions = [
            (original[:-1] + bytes([original[-1] ^ 1]), original_key),
            (original[:4] + bytes([original[4] ^ 1]) + original[5:], original_key),
            (b"BAD1" + original[4:], original_key),
            (original, secrets.token_bytes(32)),
            (original, b"short key"),
            (original + b"extra bytes", original_key),
            (original[:-20], original_key),
        ]
        for blob, key in corruptions:
            encrypted.write_bytes(blob)
            key_path.write_bytes(key)
            response = self.download(file_id)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(plaintext, response.data)
            self.assertNotIn("Content-Disposition", response.headers)
        encrypted.write_bytes(original)
        key_path.write_bytes(original_key)
        self.assertEqual(self.download(file_id).data, plaintext)

    def test_metadata_tampering_fails_authentication(self):
        file_id = self.upload_file()
        with self.app.app_context():
            record = db.session.get(StoredFile, file_id)
            record.filename = "changed.txt"
            db.session.commit()
        self.assertEqual(self.download(file_id).status_code, 503)

    def test_missing_private_files_fail_safely_and_can_still_be_deleted(self):
        for index in (0, 1):
            file_id = self.upload_file(name=f"missing-{index}.txt")
            self.paths(file_id)[index].unlink()
            self.assertEqual(self.download(file_id).status_code, 503)
            self.assertEqual(self.remove(file_id).status_code, 303)
            self.assert_deleted(file_id)

    def test_range_and_cache_headers_do_not_bypass_full_authenticated_download(self):
        file_id = self.upload_file(b"all original bytes")
        response = self.client.get(f"/files/{file_id}/download", base_url=BASE_URL,
                                   headers={"Range": "bytes=0-2", "If-None-Match": "*"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"all original bytes")

    def test_confirmation_get_does_not_delete_and_get_delete_is_rejected(self):
        file_id = self.upload_file()
        response = self.get(f"/files/{file_id}/confirm-delete")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Delete this file?", response.data)
        self.assertIn(b"Cancel", response.data)
        self.assertIn(b'name="csrf_token"', response.data)
        self.assertEqual(self.get(f"/files/{file_id}/delete").status_code, 405)
        self.assertEqual(self.download(file_id).status_code, 200)

    def test_successful_deletion_removes_both_private_files_and_database_records(self):
        file_id = self.upload_file()
        response = self.remove(file_id)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/files")
        self.assert_deleted(file_id)
        self.assertNotIn(b"private.txt", self.get("/files").data)
        self.assertEqual(self.download(file_id).status_code, 404)
        self.assertEqual(self.get(f"/files/{file_id}/confirm-delete").status_code, 404)
        self.assertEqual(self.remove(file_id).status_code, 404)

    def test_deletion_requires_valid_csrf_and_same_origin(self):
        file_id = self.upload_file()
        other = self.other_account()
        for fields in [{}, {"csrf_token": "forged"}, {"csrf_token": self.token("/files", other)}]:
            self.assertEqual(self.post(f"/files/{file_id}/delete", fields).status_code, 400)
        response = self.post(f"/files/{file_id}/delete", {"csrf_token": self.token("/files")},
                             referer="https://attacker.example/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.download(file_id).status_code, 200)

    def test_confirmation_escapes_displayed_metadata(self):
        file_id = self.upload_file()
        with self.app.app_context():
            record = db.session.get(StoredFile, file_id)
            record.filename = '<img src=x onerror="alert(1)">.txt'
            db.session.commit()
        response = self.get(f"/files/{file_id}/confirm-delete")
        self.assertNotIn(b"<img", response.data)
        self.assertIn(b"&lt;img", response.data)

    def test_interrupted_disk_deletion_blocks_download_and_can_be_retried(self):
        file_id = self.upload_file()
        encrypted, key = self.paths(file_id)
        original_unlink = Path.unlink

        def fail_ciphertext_removal(path, *args, **kwargs):
            if path == encrypted:
                raise PermissionError("simulated busy file")
            return original_unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", fail_ciphertext_removal):
            self.assertEqual(self.remove(file_id).status_code, 503)
        self.assertFalse(key.exists())
        self.assertTrue(encrypted.exists())
        self.assert_pending(file_id)
        self.assertIn(b"Retry delete", self.get(f"/files/{file_id}/confirm-delete").data)
        self.assertEqual(self.remove(file_id).status_code, 303)
        self.assert_deleted(file_id)

    def test_failed_initial_database_commit_leaves_file_unchanged(self):
        file_id = self.upload_file()
        original = [path.read_bytes() for path in self.paths(file_id)]
        token = self.token("/files")
        original_commit = db.session.commit
        failed = False

        def fail_once():
            nonlocal failed
            if not failed:
                failed = True
                raise SQLAlchemyError("simulated initial commit failure")
            return original_commit()

        with patch("encrypted_storage.db.session.commit", side_effect=fail_once):
            self.assertEqual(self.post(f"/files/{file_id}/delete", {"csrf_token": token}).status_code, 503)
        self.assertEqual([path.read_bytes() for path in self.paths(file_id)], original)
        with self.app.app_context():
            self.assertIsNone(db.session.get(FileDeletion, file_id))
        self.assertEqual(self.download(file_id).status_code, 200)

    def test_failed_final_database_commit_remains_retryable(self):
        file_id = self.upload_file()
        token = self.token("/files")
        original_commit = db.session.commit
        calls = 0

        def fail_second_commit():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise SQLAlchemyError("simulated final commit failure")
            return original_commit()

        with patch("encrypted_storage.db.session.commit", side_effect=fail_second_commit):
            self.assertEqual(self.post(f"/files/{file_id}/delete", {"csrf_token": token}).status_code, 503)
        self.assert_pending(file_id)
        self.assertEqual(self.remove(file_id).status_code, 303)
        self.assert_deleted(file_id)

    def test_pending_deletion_does_not_give_another_user_access(self):
        file_id = self.upload_file()
        with self.app.app_context():
            db.session.add(FileDeletion(file_id=file_id))
            db.session.commit()
        other = self.other_account()
        self.assertEqual(self.download(file_id, other).status_code, 404)
        self.assertEqual(self.get(f"/files/{file_id}/confirm-delete", other).status_code, 404)
        self.assertEqual(self.remove(file_id, other).status_code, 404)
        self.assertNotIn(b"private.txt", self.get("/files", other).data)
        self.assertEqual(self.remove(file_id).status_code, 303)
        self.assert_deleted(file_id)

    def test_download_and_delete_rate_limits(self):
        file_id = self.upload_file()
        for _ in range(30):
            self.assertEqual(self.download(file_id).status_code, 200)
        self.assertEqual(self.download(file_id).status_code, 429)
        self.assertEqual(self.remove(file_id).status_code, 303)
        for _ in range(9):
            self.assertEqual(self.remove(file_id).status_code, 404)
        self.assertEqual(self.remove(file_id).status_code, 429)
        with self.app.app_context():
            limiter.reset()


if __name__ == "__main__":
    unittest.main()
