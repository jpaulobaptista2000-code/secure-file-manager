"""Upload authorization, validation, authenticated encryption and failure handling."""

from io import BytesIO
import os
from pathlib import Path
import secrets
import stat
import unittest
from unittest.mock import patch

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import MultiDict

from encrypted_storage import MAGIC, associated_data, storage_paths
from extensions import db
from models import StoredFile, User
from tests.helpers import WebTestCase


def sample_pdf():
    """A small, structurally complete PDF with one empty page."""
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
    ]
    for number, contents in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + contents + b"\nendobj\n")
    xref = len(data)
    data.extend(b"xref\n0 5\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


class UploadTests(WebTestCase):
    def setUp(self):
        super().setUp()
        self.signed_in()

    def upload(self, data=b"a private test document", filename="notes.txt", client=None, extra=None):
        fields = {
            "csrf_token": self.token("/files", client),
            "file": (BytesIO(data), filename),
        }
        fields.update(extra or {})
        return self.post("/files/upload", fields, client)

    def records(self):
        with self.app.app_context():
            return db.session.execute(db.select(StoredFile).order_by(StoredFile.id)).scalars().all()

    def saved_bytes(self, record):
        with self.app.app_context():
            encrypted_path, key_path = storage_paths(record.id)
            return encrypted_path.read_bytes(), key_path.read_bytes()

    def assert_no_uploads(self):
        self.assertEqual(self.records(), [])
        for name in ("storage", "keys"):
            self.assertEqual(list((Path(self.app.instance_path) / name).iterdir()), [])

    def test_text_is_encrypted_on_disk_and_decrypts_exactly(self):
        data = "A private sentence for Alice, with acentos: João.\n".encode()
        response = self.upload(data)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/files")
        record, = self.records()
        encrypted, key = self.saved_bytes(record)
        self.assertEqual(record.filename, "notes.txt")
        self.assertEqual(record.content_type, "text/plain")
        self.assertEqual(record.size_bytes, len(data))
        self.assertEqual(len(key), 32)
        self.assertEqual(encrypted[:4], MAGIC)
        self.assertEqual(len(encrypted), len(data) + 4 + 12 + 16)
        self.assertNotIn(data, encrypted)
        self.assertEqual(AESGCM(key).decrypt(encrypted[4:16], encrypted[16:], associated_data(record)), data)
        database_bytes = (Path(self.app.instance_path) / "file_manager.sqlite3").read_bytes()
        self.assertNotIn(data, database_bytes)
        self.assertNotIn(key, database_bytes)
        page = self.get("/files")
        self.assertIn(b"notes.txt", page.data)
        self.assertIn(b"Encrypted", page.data)

    def test_pdf_and_utf8_bom_are_accepted(self):
        for data, name in [(sample_pdf(), "document.PDF"), (b"\xef\xbb\xbfHello\r\n", "notes.txt")]:
            with self.subTest(name=name):
                self.assertEqual(self.upload(data, name).status_code, 303)
        self.assertEqual(len(self.records()), 2)

    def test_identical_names_and_content_get_independent_keys_and_nonces(self):
        self.assertEqual(self.upload().status_code, 303)
        self.assertEqual(self.upload().status_code, 303)
        first, second = self.records()
        first_cipher, first_key = self.saved_bytes(first)
        second_cipher, second_key = self.saved_bytes(second)
        self.assertNotEqual(first.id, second.id)
        self.assertNotEqual(first_key, second_key)
        self.assertNotEqual(first_cipher[4:16], second_cipher[4:16])
        self.assertNotEqual(first_cipher, second_cipher)

    def test_invalid_extensions_empty_and_binary_files_are_rejected(self):
        cases = [(b"hello", "page.html"), (b"MZ\x00\xff", "program.exe"),
                 (b"", "empty.txt"), (b"\xff\x00\x01", "binary.txt"),
                 (b"hello", "fake.pdf"), (b"hello", "notes.txt.exe"),
                 (b"hello", "noextension"), (b"hello", "a" * 181 + ".txt")]
        for data, name in cases:
            with self.subTest(name=name):
                self.assertEqual(self.upload(data, name).status_code, 400)
        self.assert_no_uploads()

    def test_path_traversal_and_windows_paths_are_rejected(self):
        # A quoted multipart parameter escapes backslashes with another backslash.
        for name in ["../outside.txt", "folder/notes.txt", r"..\\outside.txt", r"C:\\notes.txt", "a:b.txt"]:
            with self.subTest(name=name):
                self.assertEqual(self.upload(filename=name).status_code, 400)
        self.assert_no_uploads()

    def test_browser_content_type_cannot_make_fake_pdf_valid(self):
        response = self.post("/files/upload", {
            "csrf_token": self.token("/files"),
            "file": (BytesIO(b"not a PDF"), "fake.pdf", "application/pdf"),
        })
        self.assertEqual(response.status_code, 400)
        self.assert_no_uploads()

    def test_missing_and_multiple_files_are_rejected(self):
        token = self.token("/files")
        self.assertEqual(self.post("/files/upload", {"csrf_token": token}).status_code, 400)
        response = self.post("/files/upload", MultiDict([
            ("csrf_token", token), ("file", (BytesIO(b"one"), "one.txt")),
            ("file", (BytesIO(b"two"), "two.txt")),
        ]))
        self.assertEqual(response.status_code, 400)
        self.assert_no_uploads()

    def test_anonymous_upload_is_rejected_before_file_parsing(self):
        other = self.app.test_client()
        with patch("upload_request.UploadRequest._get_file_stream", side_effect=AssertionError("must not parse")):
            response = self.post("/files/upload", {"file": (BytesIO(b"data"), "notes.txt")}, other)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/login")
        self.assert_no_uploads()

    def test_upload_requires_csrf_and_same_origin(self):
        for token in [None, "forged"]:
            fields = {"file": (BytesIO(b"data"), "notes.txt")}
            if token is not None:
                fields["csrf_token"] = token
            self.assertEqual(self.post("/files/upload", fields).status_code, 400)
        response = self.post("/files/upload", {
            "csrf_token": self.token("/files"), "file": (BytesIO(b"data"), "notes.txt"),
        }, referer="https://attacker.example/")
        self.assertEqual(response.status_code, 400)
        self.assert_no_uploads()

    def test_owner_fields_are_ignored_and_other_accounts_cannot_list_files(self):
        other = self.app.test_client()
        self.register("bob", client=other)
        self.login("bob", client=other)
        with self.app.app_context():
            bob_id = db.session.execute(db.select(User).filter_by(username="bob")).scalar_one().id
            alice_id = db.session.execute(db.select(User).filter_by(username="alice")).scalar_one().id
        self.assertEqual(self.upload(filename="alice-private.txt", extra={"owner_id": str(bob_id)}).status_code, 303)
        record, = self.records()
        self.assertEqual(record.owner_id, alice_id)
        self.assertNotIn(b"alice-private.txt", self.get("/files?owner_id=" + str(alice_id), other).data)
        self.assertEqual(self.upload(filename="bob-private.txt", client=other).status_code, 303)
        self.assertNotIn(b"bob-private.txt", self.get("/files").data)

    def test_file_size_boundary_is_enforced_without_plaintext_tempfiles(self):
        limit = self.app.config["UPLOAD_MAX_BYTES"]
        # Werkzeug normally spools files larger than 500 KiB to disk.
        with patch("werkzeug.formparser.default_stream_factory", side_effect=AssertionError("no plaintext spool")):
            self.assertEqual(self.upload(b"x" * limit, "maximum.txt").status_code, 303)
            self.assertEqual(self.upload(b"x" * (limit + 1), "too-large.txt").status_code, 413)
        self.assertEqual(len(self.records()), 1)

    def test_request_size_and_part_count_are_bounded(self):
        response = self.post("/files/upload", {
            "csrf_token": self.token("/files"), "padding": "x" * (6 * 1024 * 1024),
        })
        self.assertEqual(response.status_code, 413)
        fields = MultiDict([("csrf_token", self.token("/files"))])
        for number in range(9):
            fields.add("file", (BytesIO(b"data"), f"{number}.txt"))
        self.assertEqual(self.post("/files/upload", fields).status_code, 413)
        self.assert_no_uploads()

    def test_uploaded_names_are_normalized_and_list_output_is_escaped(self):
        self.assertEqual(self.upload(filename="João's notes.txt").status_code, 303)
        record, = self.records()
        self.assertEqual(record.filename, "Joaos_notes.txt")
        with self.app.app_context():
            stored = db.session.get(StoredFile, record.id)
            stored.filename = '<img src=x onerror="alert(1)">.txt'
            db.session.commit()
        page = self.get("/files")
        self.assertNotIn(b"<img", page.data)
        self.assertIn(b"&lt;img", page.data)

    def test_ciphertext_nonce_key_and_metadata_tampering_fail_authentication(self):
        self.upload()
        record, = self.records()
        encrypted, key = self.saved_bytes(record)
        nonce, ciphertext, aad = encrypted[4:16], encrypted[16:], associated_data(record)
        cases = [
            (key, nonce, ciphertext[:-1] + bytes([ciphertext[-1] ^ 1]), aad),
            (key, bytes([nonce[0] ^ 1]) + nonce[1:], ciphertext, aad),
            (AESGCM.generate_key(bit_length=256), nonce, ciphertext, aad),
        ]
        record.owner_id += 1
        cases.append((key, nonce, ciphertext, associated_data(record)))
        for selected_key, selected_nonce, selected_ciphertext, selected_aad in cases:
            with self.assertRaises(InvalidTag):
                AESGCM(selected_key).decrypt(selected_nonce, selected_ciphertext, selected_aad)

    def test_filename_collision_cannot_overwrite_existing_storage(self):
        self.upload()
        record, = self.records()
        original = self.saved_bytes(record)
        with patch("file_routes.secrets.token_hex", return_value=record.id):
            self.assertEqual(self.upload(b"replacement content").status_code, 503)
        self.assertEqual(self.saved_bytes(record), original)
        self.assertEqual(len(self.records()), 1)

    def test_partial_disk_failure_removes_the_new_key(self):
        original_open = os.open

        def fail_encrypted_write(path, *args, **kwargs):
            if str(path).endswith(".enc"):
                raise OSError("simulated full disk")
            return original_open(path, *args, **kwargs)

        with patch("encrypted_storage.os.open", side_effect=fail_encrypted_write):
            self.assertEqual(self.upload().status_code, 503)
        self.assert_no_uploads()

    def test_database_failure_removes_new_ciphertext_and_key(self):
        original_commit = db.session.commit
        failed = False

        def fail_upload_commit_once():
            nonlocal failed
            if not failed:
                failed = True
                raise SQLAlchemyError("simulated database failure")
            return original_commit()

        token = self.token("/files")
        with patch("encrypted_storage.db.session.commit", side_effect=fail_upload_commit_once):
            response = self.post("/files/upload", {"csrf_token": token, "file": (BytesIO(b"data"), "notes.txt")})
        self.assertEqual(response.status_code, 503)
        self.assert_no_uploads()

    def test_storage_and_keys_have_no_public_route(self):
        self.upload()
        record, = self.records()
        for path in [f"/instance/storage/{record.id}.enc", f"/instance/keys/{record.id}.key",
                     f"/storage/{record.id}.enc", f"/keys/{record.id}.key",
                     f"/static/../instance/keys/{record.id}.key"]:
            self.assertEqual(self.get(path).status_code, 404)

    def test_upload_rate_limit_is_per_account(self):
        for _ in range(10):
            self.assertEqual(self.upload().status_code, 303)
        self.assertEqual(self.upload().status_code, 429)
        self.assertEqual(len(self.records()), 10)
        other = self.app.test_client()
        self.register("bob", client=other)
        self.login("bob", client=other)
        self.assertEqual(self.upload(client=other).status_code, 303)

    def test_listing_pagination_is_owner_scoped(self):
        self.upload(filename="owned.txt")
        with self.app.app_context():
            owner_id = db.session.execute(db.select(User).filter_by(username="alice")).scalar_one().id
            for number in range(24):
                db.session.add(StoredFile(
                    id=secrets.token_hex(16), owner_id=owner_id, filename=f"page-test-{number}.txt",
                    content_type="text/plain", size_bytes=10,
                ))
            db.session.commit()
        first = self.get("/files")
        second = self.get("/files?page=2")
        self.assertEqual(first.data.count(b'class="file-name"'), 20)
        self.assertEqual(second.data.count(b'class="file-name"'), 5)
        self.assertIn(b"Next", first.data)
        self.assertIn(b"Previous", second.data)

    @unittest.skipIf(os.name == "nt", "POSIX mode bits; Windows uses directory ACLs")
    def test_private_storage_permissions(self):
        self.upload()
        for name in ("storage", "keys"):
            folder = Path(self.app.instance_path) / name
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
            for path in folder.iterdir():
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
