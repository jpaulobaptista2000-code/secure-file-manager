"""Start the local development server with the project's TLS certificate."""

from pathlib import Path
import ssl

from app import create_app


def main():
    project_folder = Path(__file__).resolve().parent
    certificate = project_folder / "certs" / "localhost.pem"
    private_key = project_folder / "certs" / "localhost-key.pem"

    if not certificate.is_file() or not private_key.is_file():
        raise SystemExit(
            "Local TLS files are missing. Follow the 'Create the HTTPS certificate' "
            "section in README.md, then run this command again."
        )

    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        tls.load_cert_chain(certfile=certificate, keyfile=private_key)
    except (OSError, ssl.SSLError) as error:
        raise SystemExit(
            "Could not load the local TLS certificate and key. "
            "Check the files in certs/ using README.md."
        ) from error

    # The development server is available only on this computer.
    create_app().run(
        host="127.0.0.1",
        port=5000,
        ssl_context=tls,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
