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

The student also completed the initial Windows setup on 26 October 2026 using
Python 3.13.2 and mkcert 1.4.4. The shared terminal output confirms successful
dependency installation, local CA installation, generation of the localhost
certificate and HTTPS startup with debug mode off. Requests for the home page
and CSS returned 200, and the student confirmed that the page was visible in the
browser.

PowerShell initially could not find mkcert despite its installation. Reloading
the saved PATH values resolved this; the README now includes that step. A 404
for the optional favicon does not affect the page.

No login or file-security tests have been performed yet because those features
are not implemented.

## Still to implement

- Registration, Argon2id password hashing, login and logout.
- SQLite records and server-side sessions with expiry and fixation prevention.
- CSRF protection and login attempt limits.
- File validation, encryption, listing, ownership checks, decryption and deletion.
- End-to-end security testing and a clean-machine Windows demonstration of the
  completed application.

This is the first implementation increment, not the completed Checkpoint 2.
