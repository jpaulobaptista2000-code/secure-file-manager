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

At the end of step 2, `/files` only confirmed the signed-in account. Uploads and
file operations were still pending. Database creation is automatic on startup;
the database and random application secret remain in the ignored instance folder.

### Step 2 verification

The 18 automated authentication checks pass in the Linux development environment.
They exercise actual forms, cookies and SQLite records in a temporary database:
registration and salted hashing; duplicate and invalid input; wrong credentials;
CSRF rejection; session fixation prevention; idle, absolute and database expiry;
logout replay; forged cookies; rate limiting; injection input; failure handling;
and inaccessible private files. Windows Python 3.13 dependency wheels were also
resolved successfully.

A separate HTTP-client check used a real local HTTPS server and validated its
test certificate. Registration and login worked, accounts and authenticated
sessions survived a server restart, and a revoked cookie could not regain access
after logout. The automated browser could not be installed in this environment.

On 26 October 2026, the student completed the manual Windows browser walkthrough
using the local HTTPS application. They confirmed that the registration and
login buttons appeared, that creating an account and signing in reached the
welcome page, and that opening `/files` directly after signing out redirected
them to the login page. These are student-reported functional checks; they do
not replace the automated security tests above.

## Step 3 — Validated uploads and encrypted storage

The `/files` page now has an upload form and a paginated list belonging to the
authenticated account. `POST /files/upload` accepts one nonempty PDF or UTF-8
TXT file up to 5 MiB, checks its name, extension and basic content, and assigns
its owner from the server session. The browser's MIME type and owner fields
are not trusted. Uploads require CSRF protection and are limited to 10 submissions
per minute per account. The server limits request size and multipart parts.

Uploads remain in bounded memory before encryption. Each has a fresh AES-256-GCM
key and nonce. The encrypted format contains a version marker, nonce, ciphertext
and tag; additional authenticated data binds the contents to the file ID, owner,
name, media type and size. Ciphertext and keys are saved in separate private
folders under `instance/`, using random identifiers. SQLite holds metadata only.
New directories use restrictive permissions, including Python 3.13's Windows
ACL support. Existing accounts are preserved when the new file table is created.

Ordinary disk/database failures clean up new files and roll back metadata.
The PDF check validates header/end markers, not malware or the full document
structure. The current version has no aggregate storage quota or automatic
orphan reconciliation after a hard crash. The server holds the decryption keys,
so server compromise remains a threat. Filenames and ownership metadata remain
readable in SQLite. See the README for the format and local-data handling.

### Step 3 verification

All 39 automated checks pass in the Linux development environment: the 18
authentication checks plus 21 upload/storage checks. The latter cover owner
isolation, forged owner/MIME fields, CSRF, path and content validation, size and
multipart limits, independent keys/nonces, byte-for-byte decryption, tampering,
collision protection, rate limits, pagination, private paths/permissions and
cleanup after simulated disk/database failures. Dependency checks pass, and the
new cryptography dependency has an available Windows Python 3.13 binary wheel.

A separate HTTP-client test used a real HTTPS server with certificate validation.
It preserved a pre-existing account database, uploaded a TXT file larger than
500 KiB and a PDF, and independently decrypted the stored bytes back to the
original contents. The files and session survived a server restart. A second
account could not see the first account's filenames.

On 27 October 2026, the student confirmed the Windows browser walkthrough:
uploading a test TXT file displayed the success message and an `Encrypted` row.
After signing out and creating/signing into a second account, the list was empty;
the first account's file was not visible. These are student-reported functional
checks. No automated browser test was run, and the Windows PDF-upload check
remains unverified.

## Still to implement

- Ownership-checked download/decryption and deletion through the website.
- End-to-end security testing and a clean-machine Windows demonstration of the
  completed application.

Checkpoint 2 is in progress; the file-management requirements are not complete.
