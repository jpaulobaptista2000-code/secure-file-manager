# Checkpoint 3: progress note

**Secure Web-Based File Encryption and Management System**\
**Updated:** 15 November 2026\
**Branch:** `checkpoint-3`\
**Latest tested implementation:** `079a7656fcc5923eddfe5ff4224e192c98d25048`

The core application is implemented. This checkpoint builds on the submitted
Checkpoint 2 version (`ed158e3`) retained on `main`.

## Requirements and evidence

| Requirement | Implementation and verification |
| --- | --- |
| CSRF on every state-changing form | Registration, login, logout, upload and deletion reject missing, forged and foreign-session tokens. A foreign HTTPS Referer is rejected even with a valid token. The Windows browser demonstration confirmed rejection without deleting the file. |
| XSS defences | Jinja escapes displayed input; CSP disables scripts; uploads are downloaded as attachments. Tests parse reflected/stored payload responses and find no injected elements. |
| Input validation and secure file handling | Server validation, PDF/TXT allowlist, basic format checks, 5 MiB limit, path rejection and generated storage IDs. Encryption, tamper detection and failure recovery remain tested. |
| SQL injection prevention | SQLAlchemy bound parameters throughout. Malicious login inputs fail; inspection of the real login query verifies separate parameters. No interpolated raw application SQL was found during source review. |
| Per-user access control | Ownership is determined from the server session. Other users cannot list, download or delete a file. Automated tests and the Windows browser download attempt confirmed denial. |
| Secure errors and logging | Generic errors; private rotating JSON events with timestamp, event, account ID when known, validated source address and outcome/status where relevant. Logs exclude secrets and raw error messages. |
| Security cases and results | [Case matrix](checkpoint-3-security-tests.md), [latest Linux output](evidence/checkpoint-3-final-tests.txt), [Windows summary](evidence/checkpoint-3-windows-tests.txt), and [browser evidence](evidence/checkpoint-3-windows-browser.md). |
| Draft report | [Introduction, Implementation, Security Analysis and Conclusion](checkpoint-3-report-draft.md), with standalone setup instructions and references. |

## Changes and requirement review

The new `audit.py` module uses Python's standard logging library. Logs remain
under the private `instance/logs/` directory, outside Git and web routes. Account,
file and key formats are unchanged. Error handling avoids disclosing raw exception
messages and SQL parameters.

The supplied Project.pdf has now been checked: Section 1.3 (p. 5) specifies the
four report sections, and Section 3.4.3 (pp. 11–12) lists Checkpoint 3 evidence.
Section 3.2 (p. 10) also requires a source address in structured logs. The field
was added using the validated connection IP, without trusting client-supplied
forwarding headers. A focused test covers IPv4, IPv6, missing/invalid addresses
and forged headers. The suite now contains 75 tests, including 17 Checkpoint 3 cases.

## Recorded verification

- **Linux, 14 November:** 75 tests passed in 16.536 seconds, with no failures,
  errors or skips, on Python 3.12.14. This includes the source-address addition.
  Tests use disposable data and Flask's test client, not a real browser or TLS
  network handshake. The earlier 74-test run is retained separately.
- **Windows, 14 November, student-provided summary:** 74 tests in 17.378 seconds,
  `OK (skipped=2)`: 72 passes and two POSIX permission checks skipped. This run
  preceded the source-address addition and does not verify Windows ACLs.
- **Windows browser, 14 November:** a forged deletion token was rejected, the
  test file remained downloadable with its original contents, and another
  account received File not found from the owner's download link. Private-log
  inspection confirmed `csrf_rejected` / 400 and `file_access_denied` / 404.
  Original runtime entries and private identifiers are not published.

## Remaining work

1. After pulling the branch on Windows, run the one added source-address test
   shown in the security-test document. Its Linux result is already recorded.
2. Review and upload the checkpoint report to Moodle, and bring the running
   application and commit history for the lab demonstration. Nothing has been
   submitted to Moodle by this repository update.

The report states the local-development limitations, including server-side key
access, basic PDF validation, bounded local logs and the absence of storage
quotas, production hosting and dependency vulnerability scanning. The final
project submission remains separate from this checkpoint.
