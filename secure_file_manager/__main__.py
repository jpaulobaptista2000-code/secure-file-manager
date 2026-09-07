"""Start the loopback-only development server using a local TLS certificate."""

from pathlib import Path
import ssl

from . import create_app


def main():
    cert_dir = Path(__file__).resolve().parents[1] / "certs"
    cert, key = cert_dir / "localhost.pem", cert_dir / "localhost-key.pem"
    if not cert.is_file() or not key.is_file():
        raise SystemExit("Run: python scripts/create_dev_cert.py")
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(cert, key)
    create_app().run(
        host="127.0.0.1", port=5443, ssl_context=tls,
        debug=False, use_reloader=False,
    )


if __name__ == "__main__":
    main()
