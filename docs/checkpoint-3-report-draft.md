# Secure Web-Based File Encryption and Management System

**Checkpoint 3 — draft report**  
**Web Application Security**  
**Date:** 11 November 2026  
**Repository:** https://github.com/jpaulobaptista2000-code/secure-file-manager  
**Development branch:** `checkpoint-3`  
**Tested implementation:** `4ef254099c14f778555181ce17b16885d387fd2c`

Draft status: this document follows the four report sections named in the
Checkpoint 3 brief. Additional requirements in Section 1.3 of the original
`Project.pdf` still need to be checked. Windows verification of this checkpoint
and the student's browser demonstration evidence are also pending.

## 1. Introduction

The aim of this project is to build a small web application that allows users
to store and manage their own files securely. Users can create an account, sign
in, upload PDF or text documents, list their files, download them and delete them.
The application encrypts file contents on the server before writing them to disk.

The project applies the web-security concepts studied in class: treating browser
input as untrusted, separating authentication from authorization, preventing
injection attacks, protecting state-changing requests, and limiting information
disclosure. For example, knowing a file's identifier must not allow another user
to download it. The server must check its own ownership record for every operation.

The intended environment is a local demonstration on Windows using HTTPS. File
sharing, public hosting and inline document previews are outside the chosen scope.
Encryption is server-side: the server has access to both the ciphertext and the
keys and can decrypt the files for an authorized user. It is therefore not an
end-to-end encrypted service.

## 2. Implementation

### Architecture and components

The browser displays HTML pages produced by Flask and Jinja. Requests travel over
HTTPS to the Flask application, which validates input and enforces authentication
and ownership checks. SQLAlchemy connects the application to SQLite. SQLite stores
users, password hashes, sessions, file metadata and pending deletion markers.
Encrypted file contents and their keys are stored separately under private folders.

There are three main trust boundaries: the browser-to-application boundary, the
application-to-database/storage boundary, and access to encryption keys. Data sent
by the browser cannot determine the authenticated user or override a file owner.
The storage and key directories have no public web route. These boundaries match
the design prepared for Checkpoint 1.

Flask keeps the application small enough to understand and demonstrate. SQLite
avoids a separate database service. SQLAlchemy constructs database queries with
bound values. The `cryptography` library provides AES-GCM, and `argon2-cffi`
provides password hashing. Checkpoint 3 uses Python's standard logging library
and adds no new dependency.

### Authentication and sessions

Registration checks the username and password on the server. Passwords contain
15–128 characters and are stored as salted Argon2id hashes. They are not stored
as readable text and are not used as file-encryption keys. Login failures return
a generic message. Unknown usernames still trigger password-hash verification
against a dummy hash to reduce timing differences.

Session data is held in SQLite. The browser receives a random identifier in a
cookie with `Secure`, `HttpOnly` and `SameSite=Lax`. Login changes the identifier,
while logout invalidates the server session. The server enforces a 15-minute idle
timeout and a two-hour absolute lifetime. Rate limits reduce repeated login and
file-operation attempts; their in-memory counters reset when the server restarts.

### File upload, encryption and download

An upload must contain one nonempty PDF or UTF-8 TXT file of at most 5 MiB. The
server rejects path separators, unsupported extensions, binary text data and
files that do not meet the basic expected format. Browser MIME types are not
trusted. Filenames are normalized for display; random internal identifiers are
used for storage paths.

Uploads stay in bounded memory before encryption. Each file receives a fresh
random 256-bit key and 12-byte nonce. AES-256-GCM protects confidentiality and
detects modification. The file identifier, owner, normalized filename, type and
size are authenticated as additional data. The encrypted file contains a format
marker, nonce, ciphertext and authentication tag. Its key is stored in a separate
restricted folder on the same host.

Downloads select a record using both the file identifier and the user from the
server session. The complete encrypted file is authenticated before plaintext is
returned. Downloads are attachments with an octet-stream content type and
`nosniff`; file bodies are never embedded in a web page. Missing or modified
encrypted data produces a generic error without an attachment.

Deletion is a CSRF-protected POST preceded by a confirmation page. The application
records a durable deletion marker before removing the key and ciphertext. A
partially completed deletion remains unavailable for download and can be retried.
The local TLS setup uses mkcert and supports TLS 1.2 or newer. The development
server listens only on the local computer with debug mode disabled.

### Errors and logging added in Checkpoint 3

Expected invalid requests retain appropriate HTTP status codes. Unexpected errors
return a generic 500 page. The application rolls back the current database
transaction and avoids displaying raw exceptions, queries or paths.

Security events are written as JSON lines under `instance/logs/security.jsonl`.
Each event includes a UTC timestamp, severity and event name. Request-related
events add a server-generated request ID, endpoint and HTTP method, with internal
account/file identifiers where relevant. This supports matching a rejected request
to its log entry without recording its secret values. The response includes the
same correlation identifier in `X-Request-ID`.

Logs cover authentication, CSRF rejection, denied file access, validation, file
operations and errors. They exclude passwords, cookies, tokens, usernames,
filenames, file contents, raw URLs and raw exception messages. Log files rotate
at approximately 1 MiB, retaining three backups. A runtime logging failure emits
a fixed warning and does not reverse a successful file operation. The private log
is separate from the development server's console output.

## 3. Security Analysis

### Main threats and controls

CSRF is addressed by checking session-bound tokens on all five state-changing
forms: registration, login, logout, upload and deletion. Flask-WTF also checks
the Referer origin for HTTPS requests. Cookie `SameSite` is an additional measure;
it does not replace the token checks.

XSS and HTML injection are addressed through Jinja output escaping and a Content
Security Policy that disables scripts. No template marks user content as safe,
and no uploaded document is previewed. Tests deliberately place malicious-looking
text in reflected fields and stored filename metadata to verify that it remains
text in the generated HTML.

SQL injection is prevented by using SQLAlchemy ORM/Core operations with bound
parameters throughout the application. Input validation helps restrict values,
but parameter binding is the query-level protection. A test observes the actual
login query and verifies that the username is supplied separately from the SQL.

Broken access control is addressed by ownership checks on listing, download,
deletion confirmation and deletion. The upload owner is taken from the session.
Unknown and foreign file IDs receive the same 404 response, and storage is not
accessed before authorization. CSRF and authorization are tested independently:
the unauthorized user also attempts deletion with their own valid CSRF token.

Input tampering and client-side control bypass are addressed by validating on the
server, generating storage identifiers, bounding request sizes and ignoring
browser-supplied owner fields. AES-GCM rejects tampered contents or authenticated
metadata. Error messages and logs limit information disclosure by excluding raw
request data and exception text.

### Test method and results

On 11 November 2026, the complete suite ran **74 tests successfully**, with no
failures, errors or skips, on Linux with Python 3.12.14. This includes the 58
Checkpoint 2 tests and 16 new Checkpoint 3 cases. Temporary databases and files
kept test activity separate from the normal application's data.

The tests exercise Flask request handling with an HTTPS base URL. They do not
perform a real browser or network TLS handshake. The focused cases and observed
results include:

- Missing, forged and foreign-session CSRF tokens: 400 responses across all five
  forms, with the existing account and file unchanged.
- An injected `img/onerror` username and poisoned filename: escaped HTML with no
  injected element in the parsed response.
- Boolean/comment/`DROP TABLE` login payloads: 401 responses, no private access,
  and the users table still present.
- Bob using Alice's file ID and a valid Bob CSRF token: 404 responses for download,
  deletion confirmation and deletion; Alice retained access.
- Traversal paths, fake file types and excess size: server rejection without a
  saved invalid file.
- Modified ciphertext or keys: 503 responses without plaintext downloads.
- An unexpected exception containing private text: a generic 500 page and a log
  entry containing its exception class rather than its sensitive message.
- CRLF/forged log input and a simulated log-write failure: valid, redacted JSON
  events and no secret-bearing logging traceback.

The accompanying [security test matrix](checkpoint-3-security-tests.md) provides
the exact sample vectors, mitigations and test names. The [captured output](evidence/checkpoint-3-tests.txt)
records the execution result. New Windows and browser results will be added after
the student repeats the checks on the updated branch; previous Checkpoint 2
results are not counted as current verification.

### Limitations and remaining work

A complete server compromise could expose keys and decrypted content. Key and
ciphertext folders are separated but remain on the same host. Database metadata,
including filenames, is readable. PDF header/end-marker checks do not detect all
malicious PDFs. Downloads may be dangerous if opened in a vulnerable external
viewer. Memory handling does not control operating-system swap or crash dumps.

The local application has no account-wide storage quota, malware scanner, shared
rate-limit service or production deployment configuration. Abrupt upload crashes
can leave orphan files; automatic reconciliation is not implemented. Deletion
does not securely erase backups or previously downloaded copies. Logs have bounded
retention and are not tamper-resistant against a server administrator. Removing
raw exception detail also limits diagnosis; this is a deliberate privacy tradeoff.

Windows directory permissions rely on Python 3.13+ and filesystem ACLs. Existing
Windows ACLs are not automatically corrected, and skipped POSIX tests do not
establish that Windows permissions are correct. Passing the described tests is
evidence for the tested cases, not a claim that all vulnerabilities are absent.

## 4. Conclusion

The implemented system supports the planned local account and file-management
flows, with server-side encryption, secure sessions and per-user authorization.
Checkpoint 3 adds structured security logging, consistent error handling and
explicit attack demonstrations while preserving the submitted Checkpoint 2
version. All 74 automated tests pass in the recorded Linux environment.

The next work is to validate this branch on the student's Windows setup, capture
the CSRF and cross-account browser demonstrations, and check the draft against
the original report-format requirements before preparing the Moodle submission.

## References

- Course material: supplied `checkpoint 3 (1).txt`, Secure Web-Based File
  Encryption and Management System requirements.
- OWASP, [Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html),
  particularly “Which events to log”, “Data to exclude” and “Event collection”.
- Flask, [Handling Application Errors](https://flask.palletsprojects.com/en/stable/errorhandling/),
  particularly error handlers and unhandled exceptions.
- Flask-WTF, [CSRF Protection](https://flask-wtf.readthedocs.io/en/1.2.x/csrf/).
- SQLAlchemy, [Glossary: bound parameter](https://docs.sqlalchemy.org/en/20/glossary.html#term-bound-parameter).

Online references checked on 11 November 2026. Implementation details and test
results describe this repository, rather than claims that the references certify it.
