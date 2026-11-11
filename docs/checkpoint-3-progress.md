# Checkpoint 3: progress note

**Secure Web-Based File Encryption and Management System**  
**Date:** 11 November 2026  
**Branch:** `checkpoint-3`  
**Implementation tested:** `4ef254099c14f778555181ce17b16885d387fd2c`

The core application is implemented. This checkpoint builds on the submitted
Checkpoint 2 version (`ed158e3`) without changing that version on `main`.

## Requirements and evidence

| Requirement | Implementation and verification |
| --- | --- |
| CSRF on every state-changing form | Flask-WTF checks registration, login, logout, upload and deletion. Missing, forged and another session's tokens return 400. A deletion request with a valid token but a foreign HTTPS Referer also returns 400, leaving the file available. |
| XSS defences | Jinja escapes displayed input; CSP disables scripts; uploads are downloaded as attachments. Tests parse reflected/stored payload responses and find no injected HTML elements. |
| Input validation and secure file handling | Server-side username/password checks, PDF/TXT allowlist, UTF-8/PDF format checks, 5 MiB limit, path rejection and generated storage IDs. Existing encryption, tamper-detection and failure-recovery tests still pass. |
| SQL injection prevention | Application queries use SQLAlchemy bound parameters. Malicious login inputs fail; a test captures the real login SQL and confirms the username is passed separately from the SQL text. Source review found no interpolated raw application SQL. |
| Per-user access control | Ownership comes from the server session. Bob cannot list, download, confirm deletion or delete Alice's files; direct file operations return 404. |
| Secure errors and structured logging | Added private rotating JSON logs, server-generated request IDs, fixed event codes, generic HTTP/500 responses and redaction of raw exception messages. Tests cover disclosure, log injection attempts and logging failures. |
| Security cases and results | [Test matrix and demonstrations](checkpoint-3-security-tests.md), with [captured output](evidence/checkpoint-3-tests.txt). |
| Draft report | [Introduction, Implementation, Security Analysis and Conclusion](checkpoint-3-report-draft.md). |

## Changes in this checkpoint

The new `audit.py` module uses Python's standard logging library, so no additional
packages are needed. Logs are stored under `instance/logs/`, outside Git and web
routes. Existing accounts and encrypted files keep their format and database
schema. The application records operational failures without exposing their
original text to the user or the security log.

Sixteen tests were added to make the checkpoint's attack demonstrations explicit
and check logging/error handling. The complete suite now contains 74 tests.

## Results and remaining checks

On 11 November 2026, **74 tests passed on Linux with Python 3.12.14**, with no
failures, errors or skips. They used temporary databases, files and logs. Flask's
test client exercised request handling with an HTTPS base URL; this run did not
exercise a browser or a network TLS handshake.

The following are still pending:

1. Run the updated suite and browser demonstrations on the student's Windows PC.
   Two POSIX permission checks are expected to skip there; this is not an ACL audit.
2. Check the report against any additional length/format requirements in
   Section 1.3 of the original `Project.pdf`. That file is not present in the
   current workspace. The draft follows the four sections named in the supplied
   Checkpoint 3 brief.
3. Review the draft, add the student's own demonstration evidence, and prepare
   the final Moodle upload. Nothing has been submitted to Moodle by this update.

Earlier Windows/HTTPS results belong to Checkpoint 2 and are not presented as
new Checkpoint 3 results. Public hosting, antivirus scanning, account-wide storage
quotas, external key management and tamper-resistant remote logging remain outside
the implemented local demonstration scope.
