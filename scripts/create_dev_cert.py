"""Generate a seven-day, self-signed localhost certificate. Never commit outputs."""

from datetime import datetime, timedelta, timezone
import ipaddress
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def main():
    target = Path(__file__).resolve().parents[1] / "certs"
    target.mkdir(mode=0o700, exist_ok=True)
    cert_path, key_path = target / "localhost.pem", target / "localhost-key.pem"
    if cert_path.exists() or key_path.exists():
        raise SystemExit("Certificate files already exist. Refusing to overwrite them.")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=7))
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        ]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(key, hashes.SHA256())
    )
    encoded_key = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    # POSIX mode 0600 is set on creation. Windows users must use NTFS ACLs.
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(encoded_key)
    with cert_path.open("xb") as stream:
        stream.write(cert.public_bytes(serialization.Encoding.PEM))
    print("Local certificate created. It expires after seven days.")
    print("Start with: python -m secure_file_manager")


if __name__ == "__main__":
    main()
