# Threat model and security test plan

**Status:** Design-stage assessment for Checkpoint 1. This table describes intended
mitigations and future test evidence, not completed security assurance.

## Assets, actors and assumptions

Assets: plaintext file contents, per-file keys, account password hashes, active
sessions, ownership metadata, storage capacity and useful audit evidence.

Actors: an anonymous requester, an authenticated user attacking another account,
a person who obtains a database/ciphertext copy, and a network attacker. A fully
compromised application host is a documented limit: it can obtain keys and read
plaintext during processing. The lecturer and student are legitimate demo users,
not assumed immune from malformed requests.

The architecture and trust boundaries are in [the design](checkpoint-1.md).
All traffic from the browser is untrusted. Possession of a UUID is not permission.
The application does not execute documents or fetch user-provided URLs.

## Mapping approach

The assignment does not name an OWASP edition. This draft maps to
[OWASP Top 10:2025][top2025], with a [2021 cross-reference][top2021] below in case
the lectures use that edition. Category mappings are this project's analysis,
not an OWASP certification or a claim that every threat has only one category.
Confirm the lecturer's preferred edition before the lab.

Priority reflects plausible impact and reach in this proposed application:
**High** means account/file disclosure, tampering or destructive access;
**Medium** means bounded availability, observability or supporting-control risk.
These are qualitative planning priorities, not measured risk scores.

## Threat register

| ID / priority | Attack and boundary | OWASP 2025 | Planned mitigation | Evidence to collect |
| --- | --- | --- | --- | --- |
| T01 / High | Logged-in Bob replaces his file UUID with Alice's in a download or delete request; TB1/TB2. | A01 Broken Access Control | Every operation selects by file UUID **and authenticated owner UUID**; unknown/foreign files both return 404. | TEST-01: Alice owns a file; Bob cannot download/delete it; Alice can still download afterwards. |
| T02 / High | Request adds `owner_id`, `storage_path`, or bypasses hidden/disabled form controls; TB1. | A01; A06 Insecure Design | Allowlist accepted fields; derive owner from session; generate disk name on server; enforce quota and size on server. | TEST-02: tampered fields cannot change ownership or select another path, even with browser validation disabled. |
| T03 / High | Filename or account label contains HTML/JavaScript; TB1. | A05 Injection | Escape HTML output; quote attributes; no `safe` filter; disable scripts through CSP; never preview uploaded content. | TEST-03: `<img src=x onerror=alert(1)>` is rejected or displayed as text; no execution, including without relying solely on CSP. |
| T04 / High | Login or file lookup sends SQL syntax such as `' OR '1'='1`; TB1/TB2. | A05 Injection | Use SQLAlchemy bound values throughout; no interpolated raw SQL; constrained identifiers and normalized usernames. | TEST-04: no login bypass or cross-user results; inspect queries and verify rows unchanged. ORM use alone is not proof. |
| T05 / High | Attacker site submits a delete, upload or login form using a victim's cookies; TB1. | A01 Broken Access Control | CSRFProtect on all unsafe methods/forms, including login and logout; SameSite supplements token checks. | TEST-05: missing, incorrect and other-session tokens fail; valid token succeeds; GET cannot delete. |
| T06 / High | Attacker fixes an anonymous session ID or replays a session after logout/expiry; TB1. | A07 Authentication Failures | Regenerate ID at login; revoke previous server record; enforce idle and absolute timeouts; remove session on logout. | TEST-06: retain old cookie before login, after logout and beyond each timeout; replay must fail. |
| T07 / High | Login guessing or disclosure of password table; TB1/TB2. | A07; A04 Cryptographic Failures | Argon2id with salts, generic errors, dummy verification for nonexistent users, account/source throttling. | TEST-07: wrong logins fail; configured throttle triggers; database contains hashes rather than passwords. |
| T08 / High | Network observer reads or changes login/upload traffic; TB1. | A04 Cryptographic Failures | TLS and trusted local certificate; Secure cookies; no plaintext listener when accounts are enabled. | TEST-08: validated HTTPS handshake, secure cookie inspection and refusal of plaintext HTTP on the application port. |
| T09 / High | Ciphertext is copied, modified, truncated or swapped between file records; TB2/TB3. | A04; A08 Software or Data Integrity Failures | Per-file AES-GCM keys stored separately; version/file/owner binding; fail before releasing bytes. | TEST-09: binary round-trip and changed key, nonce, tag, body and context rejected. Prototype tests exist; storage integration remains planned. |
| T10 / High | Upload name uses `../`, absolute paths, backslashes, double extensions or executable content; TB1/TB2. | A01; A05; A02 Security Misconfiguration | Reject path syntax and invalid labels; UUID paths; TXT/PDF allowlist and basic content checks; private storage, attachment download, no execution/inclusion. | TEST-10: traversal, `.php`, `.html`, fake MIME and empty/oversized uploads fail without disk writes outside storage. An accepted PDF is not claimed malware-free. |
| T11 / Medium | Large bodies, too many form parts or simultaneous uploads exhaust memory/storage; TB1/TB2. | A06 Insecure Design | Bounded parser, 6 MiB request/5 MiB file cap, 8 form parts, 16 KiB non-file field limit, transactional 50 MiB user quota; bound concurrency. | TEST-11: below/above size limits, quota races and malformed forms; verify controlled rejection and no partial active file. |
| T12 / High | Plaintext survives multipart spooling; key or ciphertext survives a failed deletion; TB2/TB3. | A04; A10 Mishandling of Exceptional Conditions | Bounded in-memory upload stream; explicit upload/delete states; remove live key and content; cleanup/reconciliation; document disk/snapshot limits. | TEST-12: upload above spool threshold; inspect temporary storage; simulate disk/DB/key errors; deletion cannot falsely report success. |
| T13 / Medium | Host spoofing, debug output or exception exposes configuration; TB1. | A02; A10 | Trusted Host allowlist, no debug mode, generic errors, consistent failure responses. | TEST-13: malicious Host and missing/error routes; no internals reflected. Host/error scaffold tests exist. |
| T14 / High | Passwords, keys or bearer tokens enter logs/Git; a filename forges log lines; TB1/TB3. | A09 Security Logging and Alerting Failures; A02 | JSON allowlisted audit fields, correlation ID, no raw request dump; secrets outside source; inspect staged changes and captures. | TEST-14: synthetic marker secrets and CR/LF input; event remains structured; markers absent from logs, source and submission ZIP. |
| T15 / Medium | Modified or vulnerable dependency is installed on another machine. | A03 Software Supply Chain Failures | Pin tested dependencies, use the normal trusted package index, review update provenance and advisories before each checkpoint. | TEST-15: fresh environment install, dependency review record and full current test run; pins alone do not prove safety. |

## Weeks 1-4 coverage

The assignment specifically mentions HTML/JavaScript injection, input tampering
and client-side control bypass. T03 addresses injection; T01/T02/T10 cover request
and filename tampering; T02/T11 explicitly require controls to survive bypass of
browser validation. Exact lecture slides were not supplied, so additional topics
must be aligned with the actual classes rather than invented here.

## Cross-reference to the 2021 edition

| Used 2025 category | Closest relevant 2021 category for these threats |
| --- | --- |
| A01 Broken Access Control | A01 Broken Access Control |
| A02 Security Misconfiguration | A05 Security Misconfiguration |
| A03 Software Supply Chain Failures | A06 Vulnerable and Outdated Components; A08 Software and Data Integrity Failures |
| A04 Cryptographic Failures | A02 Cryptographic Failures |
| A05 Injection | A03 Injection |
| A06 Insecure Design | A04 Insecure Design |
| A07 Authentication Failures | A07 Identification and Authentication Failures |
| A08 Software or Data Integrity Failures | A08 Software and Data Integrity Failures |
| A09 Security Logging and Alerting Failures | A09 Security Logging and Monitoring Failures |
| A10 Mishandling of Exceptional Conditions | Context-dependent: A04 Insecure Design / A05 Security Misconfiguration; no direct one-to-one category |

SSRF from user-supplied URLs is excluded by the absence of remote-import features.
If that scope changes, revisit it explicitly rather than treating the mapping as
permanent.

## How to record results

Use two synthetic accounts, Alice and Bob, and synthetic files. For each TEST-ID
record the commit SHA, setup, exact request or pytest command, expected behavior,
observed behavior, sanitized evidence and pass/fail. A screenshot of an error alone
does not prove the file remained intact; check the legitimate flow afterwards.

Automated tests in this foundation cover a subset of TEST-09 and TEST-13, plus
prototype size limits. They do not establish TEST-01/02/11 merely because a
cryptographic owner check or in-memory limit passed. Keep future cases marked
**Not run** until their actual implementation is exercised.

Further references for implementation:

- [OWASP File Upload Cheat Sheet][uploads]
- [OWASP Session Management Cheat Sheet][session-guide]
- [Flask-WTF CSRF protection][csrf]
- [OWASP SQL Injection Prevention Cheat Sheet][sql]
- [OWASP Logging Cheat Sheet][logs]

[top2025]: https://owasp.org/Top10/2025/
[top2021]: https://owasp.org/Top10/2021/
[uploads]: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
[session-guide]: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
[csrf]: https://flask-wtf.readthedocs.io/en/1.2.x/csrf/
[sql]: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
[logs]: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
