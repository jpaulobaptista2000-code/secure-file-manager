# Checkpoint 2 progress

## Step 1 — Flask page and local HTTPS

The application now has a home page rendered by Flask and Jinja, with a local
CSS file. The startup command loads a locally generated TLS certificate,
listens on the loopback interface, and keeps debug mode disabled. It stops if
the required certificate files are missing.

The README contains Windows PowerShell setup, certificate generation, startup
and troubleshooting instructions. Local environments, certificates, keys and
future application data are excluded from Git.

## Verification so far

Verified in a fresh Python 3.12 environment on Linux using a temporary test
certificate and an HTTPS client configured to trust that certificate:

- The home page and CSS are served over HTTPS with certificate validation.
- Startup stops when TLS files are missing; debug mode remains disabled.
- Requests for the application source and TLS private key return 404.
- An untrusted Host header is rejected, and plaintext HTTP does not serve the page.
- Security headers are present, and Git ignores generated keys and the environment.

The Windows PowerShell instructions and mkcert browser trust still need to be
verified on the student's Windows computer. No login or file-security tests have
been performed yet because those features are not implemented.

## Still to implement

- Registration, Argon2id password hashing, login and logout.
- SQLite records and server-side sessions with expiry and fixation prevention.
- CSRF protection and login attempt limits.
- File validation, encryption, listing, ownership checks, decryption and deletion.
- End-to-end security testing and a clean-machine Windows demonstration.

This is the first implementation increment, not the completed Checkpoint 2.
