# Checkpoint 3: security tests and evidence

**Date:** 11 November 2026  
**Tested implementation:** `4ef254099c14f778555181ce17b16885d387fd2c`  
**Result:** 74 tests passed on Linux / Python 3.12.14; 0 failures, 0 errors, 0 skips.

The [captured test output](evidence/checkpoint-3-tests.txt) contains the test names,
environment, execution time and result. Tests use the real Flask application with
temporary SQLite, storage, keys and logs. Requests go through Flask's test client
with an HTTPS base URL. These are application-level tests, not browser execution,
an external penetration test, or a network TLS scan. No external target is used.

## Attack cases and observed results

All rows below passed in the recorded run. Payloads and fixtures are deliberately
limited to the local test application. HTTP codes describe the response to the
test, rather than proof that every possible variant of an attack is covered.

| ID / attack | Attempt and observed result | Mitigation and evidence |
| --- | --- | --- |
| C3-01 / CSRF | POST to all five form endpoints with no token, `forged`, or a different browser session's token. All 15 requests returned **400**. The account remained signed in and its file remained downloadable. | Global CSRFProtect, session-bound tokens; `test_csrf_missing_forged_and_foreign_tokens_block_every_post_form`. |
| C3-02 / cross-site request | Delete POST with the owner's valid token and `Referer: https://attacker.example/`. Returned **400**; download still returned **200**. | Flask-WTF's HTTPS same-origin Referer check, in addition to tokens; `test_cross_site_delete_with_valid_token_is_rejected`. This deliberately tests a forged request, not a browser stealing a token. |
| C3-03 / reflected XSS | Login username `"><img src=x onerror=alert(1)>`. Returned **401**. HTML parsing found no injected `img` or `script` element; the response contained escaped text. | Jinja escaping and `script-src 'none'`; `test_reflected_xss_is_text_not_an_html_element`. |
| C3-04 / stored XSS | A test fixture inserted `<img src=x onerror="alert(1)">.txt` directly into a filename database record. Both the list and delete-confirmation pages escaped it. | Output escaping remains effective even if stored data is unsafe; `test_stored_xss_is_escaped_on_both_filename_pages`. This fixture bypasses upload validation to test the separate output defence. |
| C3-05 / active file content | Uploaded a valid TXT containing `<script>alert("test")</script>`. Upload succeeded; list contained no file body. Download returned the exact bytes with attachment/octet-stream/nosniff headers. | No inline preview; `test_html_in_a_text_upload_is_only_downloaded_as_an_attachment`. The file is treated as data, not declared harmless for opening elsewhere. |
| C3-06 / SQL injection | Tried usernames `' OR '1'='1`, `admin'--`, and `'; DROP TABLE users;--`, plus a valid username with an SQL-like password. All returned **401**; private access remained denied and the users table remained intact. | Username validation, parameterized lookup and password hashing; `test_sql_injection_payloads_cannot_authenticate_or_remove_accounts`. |
| C3-07 / parameter binding | Captured a legitimate login query at the database-driver boundary. The statement contained a `?` placeholder, not `alice`; `alice` appeared in the separate parameters. | SQLAlchemy bound parameters; `test_real_login_query_sends_username_as_a_bound_parameter`. This supplements payload rejection, which alone would not prove parameterization. |
| C3-08 / IDOR and owner tampering | Bob used Alice's file ID in download, confirmation and deletion requests, including Bob's valid CSRF token. All returned **404**, logged denied access, and left Alice's download working. Bob could not list Alice's files or change upload ownership with `owner_id`. | Every file lookup is owner-scoped; `test_foreign_file_access_is_denied_and_recorded_without_disclosing_its_name`, existing ownership tests in `test_uploads.py` and `test_file_actions.py`. |
| C3-09 / upload bypass | Attempted `../outside.txt`, Windows paths, `.exe`, `.html`, empty/binary TXT, and fake PDF with `application/pdf`. Invalid uploads returned **400**. A file of 5 MiB passed; 5 MiB + 1 byte returned **413**. | Server validation, generated storage names, content checks and bounded memory; upload validation tests in `test_uploads.py`. PDF checks are basic, not antivirus. |
| C3-10 / ciphertext tampering | Modified the encrypted bytes, nonce, header, key, stored metadata or file length. Downloads returned **503**, without plaintext or attachment headers. Restoring the originals restored download. | AES-GCM authentication and size/format checks before sending data; tampering tests in `test_file_actions.py`. |
| C3-11 / error disclosure | Simulated a password-verification exception containing a private path and SQL text, with production-style exception handling. Returned a generic **500**, no leaked string or traceback, and no authenticated session. A later valid login worked. | Generic error handler, transaction rollback and allowlisted log fields; `test_unexpected_exception_returns_generic_500_and_redacted_json_log`. |
| C3-12 / log injection and secrets | Submitted a username containing CRLF and a forged JSON event, supplied a forged `X-Request-ID`, and used test credentials, filename, file body and query-string markers. The private log omitted these values and stayed valid JSON; the response used a new server-generated ID. | No raw input logging, JSON encoding and server-generated correlation IDs; structured-log and request-ID tests in `test_checkpoint3.py`. |
| C3-13 / logging failure and growth | Simulated a write/rotation failure containing sensitive error text. Login still returned **303**; stderr contained only a fixed warning. Separate rotation tests retained one current file and three backups. | Safe logging error handler and bounded rotation; logging-failure and rotation tests in `test_checkpoint3.py`. |
| C3-14 / session and request tampering | Replayed a logged-out or pre-login cookie, changed session timestamps, forged a cookie and exceeded login/file limits. Authentication stayed denied after expiry/revocation; excessive requests returned **429**. | Server sessions, ID rotation, idle/absolute expiry and rate limits; `test_auth.py` and `test_file_actions.py`. |
| C3-15 / storage failure recovery | Simulated partial writes, database failures and interrupted deletion. New failed uploads were cleaned up; interrupted deletion stayed unavailable and could be retried. | Rollback, exclusive file creation and durable deletion markers; failure tests in `test_uploads.py` and `test_file_actions.py`. |

## SQL and rendering source review

Application SQL was reviewed in `auth.py`, `security.py`, `file_routes.py` and
`encrypted_storage.py`. Selects, inserts, updates and deletes use SQLAlchemy
ORM/Core expressions with separately bound values. No raw SQL assembled from
request strings was found. SQLite's driver receives parameters; the application
does not claim to manage a separate cache of server-side prepared statements.

Templates use normal Jinja interpolation. No `|safe`, `Markup`, client-side
`innerHTML`, or CSRF exemptions were found in the application source. User
filenames are never used to build storage paths. Authorization is performed
before reading a file/key, and a browser-supplied owner cannot override the
authenticated account.

## Reproduce the automated demonstrations on Windows

From the project folder on branch `checkpoint-3`:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_checkpoint3 -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The first command runs 16 focused cases; the second runs all 74. On Windows,
the full suite is expected to skip two POSIX mode-bit checks because Windows
uses ACLs. The actual Windows result has not yet been recorded for this branch.
Tests use disposable data and do not delete the normal application's accounts or
uploads. A known Flask-Session `datetime.utcnow` deprecation warning may appear;
the captured Linux report omits that warning for readability.

## Browser demonstration to complete on Windows

These are instructions with expected outcomes, **not a claim of a completed
Checkpoint 3 browser test**. Use disposable accounts and a small test document.
Start `run.py` and use the same host, such as `https://127.0.0.1:5000`, throughout.

### 1. Demonstrate CSRF rejection

1. Sign in, upload a disposable TXT, and open its deletion confirmation page.
2. Open the browser's developer tools with F12 and select the Elements panel.
3. Find the form whose action ends in `/delete`. Inside that form, change the
   hidden input named `csrf_token` to have the value `forged`. Do not change the
   separate logout form.
4. Press **Delete file**. Expected result: a security-token error and **400** in
   the Network panel. The file must still appear and download from **My files**.
5. Record a screenshot of the rejection and the unchanged file. Reloading the
   form restores a valid token; the browser edit does not change project files.

### 2. Demonstrate per-user access control

1. As Alice, copy the test file's Download link and confirm it works.
2. In a separate private browser window, create/sign in as Bob. Confirm Bob's
   username is shown and Alice's file is absent from the list.
3. Paste Alice's link in Bob's window. Expected: **File not found / 404**.
4. Return to Alice's window and confirm her download still works. Record the
   two outcomes. The automated suite additionally covers Bob's deletion attempt
   with a valid token, so CSRF cannot mask a missing ownership check.

### 3. Inspect the associated security events

In another PowerShell window, from the project directory:

```powershell
Get-Content .\instance\logs\security.jsonl -Tail 10
```

Look for `csrf_rejected` and `file_access_denied`. The Network panel's response
header `X-Request-ID` can be matched to `request_id` in the JSON line. Record only
disposable demonstration data. The runtime log itself stays outside the repository;
it is not a public download and is not included in a submission by default.

## Scope limits

Passing tests establish the observed behavior for these cases; they do not prove
that the application has no vulnerabilities. Browser CSP execution, Windows ACLs,
multi-user load, malicious PDF analysis, dependency vulnerability scanning, public
deployment and remote/tamper-resistant logging are not established by this run.
The existing Checkpoint 2 browser and fresh-clone checks remain historical evidence,
not substitutes for verifying the new branch on Windows.
