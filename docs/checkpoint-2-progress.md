# Checkpoint 2 progress

## Step 1 — Flask page and local HTTPS

The application now has a home page rendered by Flask and Jinja, with a local
CSS file. The startup command loads a locally generated TLS certificate,
listens on the loopback interface, and keeps debug mode disabled. It stops if
the required certificate files are missing.

The README contains Windows PowerShell setup, certificate generation, startup
and troubleshooting instructions. Local environments, certificates, keys and
future application data are excluded from Git.

## Step 1 verification

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

## Step 2 — Accounts and server-side sessions

Registration, login and POST-only logout are implemented. SQLite stores user
records with salted Argon2id password hashes, and Flask-Session stores session
data in the same database. The browser receives only a random session ID, using
the Secure, HttpOnly and SameSite=Lax cookie flags.

Login changes the session ID, logout removes the session, and authenticated
requests enforce 15 minutes of inactivity and a 2-hour absolute lifetime. Forms
have CSRF protection, and authentication pages use no-store caching. Server-side
validation checks usernames, password lengths and matching confirmation fields.
Invalid login credentials produce a generic error.

The registration and login endpoints each accept at most 5 POST submissions per
minute per client IP. These counters are in memory for the current single-process
local setup, so restarting resets them. Public deployment would require shared
persistent rate-limit storage.

The protected `/files` page currently confirms the signed-in account. Uploads and
file operations remain unimplemented. Database creation is automatic on startup;
the database and random application secret remain in the ignored instance folder.

### Step 2 verification

The 18 automated authentication checks pass in the Linux development environment.
They exercise actual forms, cookies and SQLite records in a temporary database:
registration and salted hashing; duplicate and invalid input; wrong credentials;
CSRF rejection; session fixation prevention; idle, absolute and database expiry;
logout replay; forged cookies; rate limiting; injection input; failure handling;
and inaccessible private files. Windows Python 3.13 dependency wheels were also
resolved successfully. Authentication still needs the student's Windows walkthrough.

A separate HTTP-client check used a real local HTTPS server and validated its
test certificate. Registration and login worked, accounts and authenticated
sessions survived a server restart, and a revoked cookie could not regain access
after logout. The automated browser could not be installed in this environment;
visual and native-browser validation of the new forms remains part of the
Windows walkthrough.

## Still to implement

- File validation, encryption, listing, ownership checks, decryption and deletion.
- End-to-end security testing and a clean-machine Windows demonstration of the
  completed application.

Checkpoint 2 is in progress; the file-management requirements are not complete.
