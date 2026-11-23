# Checkpoint 3 progress

Checkpoint record, November 2026. The [final test results](../tests/RESULTS.md) include the subsequent Windows source-address check.

The core application is implemented. This checkpoint adds private security
logging, generic error handling and tests for the main web attacks.

## Completed

- CSRF protection on registration, login, logout, upload and deletion.
- HTML escaping, a Content Security Policy and parameterized database queries.
- Server-side upload validation, encrypted storage and ownership checks.
- Structured security events with timestamps, source addresses and outcomes,
  without passwords or tokens.

## Verification

Automated tests passed in the development environment. Windows tests and browser
checks also succeeded, with POSIX permission checks skipped. A forged deletion
token was rejected without removing the file, and another account's download
attempt returned **File not found**. Both rejections appeared in the private log.

At this checkpoint, the source-address check had only been confirmed in development.
It later passed in the full Windows run linked above. Test details and supporting evidence are kept in
one place: [security tests](checkpoint-3-security-tests.md).

For setup and current limitations, see the [README](../README.md).
