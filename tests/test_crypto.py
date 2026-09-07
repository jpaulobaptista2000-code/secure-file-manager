from uuid import uuid4

import pytest

from secure_file_manager.crypto import (
    DecryptionError, MAX_FILE_BYTES, decrypt_file, encrypt_file,
)


def test_binary_round_trip():
    data = bytes(range(256)) * 100
    file_id, owner_id = uuid4(), uuid4()
    sealed = encrypt_file(data, file_id, owner_id)
    assert sealed.payload != data
    assert decrypt_file(sealed.payload, sealed.key, file_id, owner_id) == data


@pytest.mark.parametrize("change", ["version", "nonce", "ciphertext", "tag", "key", "owner", "file", "truncate"])
def test_tampering_and_wrong_context_are_rejected(change):
    file_id, owner_id = uuid4(), uuid4()
    sealed = encrypt_file(b"synthetic test contents", file_id, owner_id)
    payload, key = sealed.payload, sealed.key
    positions = {"version": 3, "nonce": 4, "ciphertext": 16, "tag": len(payload) - 1}
    if change in positions:
        altered = bytearray(payload)
        altered[positions[change]] ^= 1
        payload = bytes(altered)
    elif change == "key":
        key = bytes([key[0] ^ 1]) + key[1:]
    elif change == "owner":
        owner_id = uuid4()
    elif change == "file":
        file_id = uuid4()
    else:
        payload = payload[:10]
    with pytest.raises(DecryptionError, match="File cannot be decrypted"):
        decrypt_file(payload, key, file_id, owner_id)


def test_each_encryption_uses_an_independent_key():
    file_id, owner_id = uuid4(), uuid4()
    first = encrypt_file(b"same contents", file_id, owner_id)
    second = encrypt_file(b"same contents", file_id, owner_id)
    assert first.key != second.key
    assert first.payload != second.payload
    assert first.key.hex() not in repr(first)
    assert repr(first.key) not in repr(first)


@pytest.mark.parametrize("size", [0, MAX_FILE_BYTES + 1])
def test_size_limits(size):
    with pytest.raises(ValueError, match="File size"):
        encrypt_file(b"x" * size, uuid4(), uuid4())


def test_maximum_file_size_round_trip():
    data = b"x" * MAX_FILE_BYTES
    file_id, owner_id = uuid4(), uuid4()
    sealed = encrypt_file(data, file_id, owner_id)
    assert decrypt_file(sealed.payload, sealed.key, file_id, owner_id) == data
