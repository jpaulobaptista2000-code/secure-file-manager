"""Demonstrate round-trip and tamper rejection using generated demo data only."""

from uuid import uuid4

from .crypto import DecryptionError, decrypt_file, encrypt_file


def main():
    original = b"A synthetic file for the Web Application Security project."
    file_id, owner_id = uuid4(), uuid4()
    sealed = encrypt_file(original, file_id, owner_id)
    assert decrypt_file(sealed.payload, sealed.key, file_id, owner_id) == original
    print("PASS: original bytes recovered after encryption and decryption")
    damaged = sealed.payload[:-1] + bytes([sealed.payload[-1] ^ 1])
    for label, payload, owner in (
        ("modified ciphertext rejected", damaged, owner_id),
        ("different owner binding rejected", sealed.payload, uuid4()),
    ):
        try:
            decrypt_file(payload, sealed.key, file_id, owner)
        except DecryptionError:
            print(f"PASS: {label}")
        else:
            raise RuntimeError(f"FAIL: {label}")
    print("Prototype only: HTTP ownership checks and key storage are not implemented.")


if __name__ == "__main__":
    main()
