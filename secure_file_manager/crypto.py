"""Small in-memory prototype of the planned file format; no persistent storage."""

from dataclasses import dataclass, field
import secrets
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"SFM\x01"
NONCE_BYTES = 12
TAG_BYTES = 16
MAX_FILE_BYTES = 5 * 1024 * 1024


class DecryptionError(ValueError):
    """A uniform error for an unreadable or unauthenticated file."""


@dataclass(frozen=True)
class EncryptedFile:
    payload: bytes = field(repr=False)
    # The caller must keep this separate from ciphertext. Never serialize the
    # entire object into a database row, log, HTTP response or Git commit.
    key: bytes = field(repr=False)


def _aad(file_id: UUID, owner_id: UUID) -> bytes:
    if not isinstance(file_id, UUID) or not isinstance(owner_id, UUID):
        raise ValueError("File and owner identifiers must be UUID objects")
    return MAGIC + file_id.bytes + owner_id.bytes


def encrypt_file(plaintext: bytes, file_id: UUID, owner_id: UUID) -> EncryptedFile:
    if not isinstance(plaintext, bytes):
        raise TypeError("File contents must be bytes")
    if not 0 < len(plaintext) <= MAX_FILE_BYTES:
        raise ValueError("File size must be between 1 byte and 5 MiB")
    aad = _aad(file_id, owner_id)
    # A fresh key for every immutable file avoids intentional key/nonce reuse.
    key = AESGCM.generate_key(bit_length=256)
    nonce = secrets.token_bytes(NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    return EncryptedFile(MAGIC + nonce + ciphertext, key)


def decrypt_file(payload: bytes, key: bytes, file_id: UUID, owner_id: UUID) -> bytes:
    aad = _aad(file_id, owner_id)
    overhead = len(MAGIC) + NONCE_BYTES + TAG_BYTES
    if (
        not isinstance(payload, bytes)
        or not isinstance(key, bytes)
        or len(key) != 32
        or not overhead < len(payload) <= MAX_FILE_BYTES + overhead
        or not payload.startswith(MAGIC)
    ):
        raise DecryptionError("File cannot be decrypted")
    nonce_end = len(MAGIC) + NONCE_BYTES
    try:
        return AESGCM(key).decrypt(
            payload[len(MAGIC):nonce_end], payload[nonce_end:], aad
        )
    except InvalidTag:
        raise DecryptionError("File cannot be decrypted") from None
