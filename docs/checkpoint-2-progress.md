# Checkpoint 2 progress

**Project:** Secure Web-Based File Encryption and Management System

**Date:** 27 October 2026

**Status:** Core requirements implemented; the planned verification is complete.

## Implemented requirements

| Requirement | Implementation |
| --- | --- |
| Working web interface | Flask/Jinja pages for registration, login, logout, file upload, personal file lists, download and confirmed deletion. |
| Server-side encryption and decryption | AES-256-GCM with a fresh random key and nonce per upload. File metadata is authenticated with the ciphertext. The server checks ownership and authenticates the entire file before returning a download. |
| Authentication and sessions | Salted Argon2id password hashes; SQLite-backed sessions; Secure, HttpOnly and SameSite=Lax cookies; session ID rotation at login and invalidation at logout. Sessions expire after 15 minutes of inactivity or 2 hours in total. |
| Development TLS | `run.py` requires a local TLS certificate, serves HTTPS on the loopback interface and disables debug mode. The README explains certificate creation with mkcert. |
| Reproducible setup and incremental history | Pinned dependencies, Windows PowerShell setup instructions and separate commits for HTTPS, authentication, encrypted uploads, and download/deletion. |

The application accepts nonempty PDF and UTF-8 TXT files up to 5 MiB. SQLite
stores accounts, sessions and file metadata; encrypted contents and per-file
keys are kept in separate private directories outside Git. Forms use CSRF
protection, and sensitive endpoints have rate limits. Download and deletion
check ownership on the server, including when a user supplies a direct file URL.
Interrupted deletions can be retried by the owner.

## Verification

- **Linux:** all 58 automated tests passed. The suite covers authentication,
  session expiry and rotation, CSRF, ownership, upload validation, encrypted
  storage, tampering, downloads, deletion and simulated storage/database failures.
- **Windows, Python 3.13.2:** the student's terminal reported
  `Ran 58 tests in 15.119s` and `OK (skipped=1)`: 57 passed. The skipped test
  checks POSIX permission bits and is deliberately skipped on Windows; it does
  not validate Windows directory ACLs.
- **Windows browser:** the student confirmed TXT/PDF upload and download,
  cancellation and confirmation of deletion, denial of a second account's
  direct download URL, and successful PDF access after an application restart.
- **Fresh setup:** a new GitHub clone, new virtual environment, dependency
  installation and certificate generation were followed by successful HTTPS
  startup and a complete registration/login/upload/download/delete walkthrough.
  This used the same Windows PC with Python, Git and mkcert already installed.

The browser checks were reported by the student; document contents were checked
visually. Automated tests also verify downloads byte for byte. Full evidence
and the earlier development steps are in the
[development and verification log](checkpoint-2-development-log.md).

## Current limits

The application is a local development setup. The server holds the file keys,
so server compromise can expose file contents; metadata remains readable in
SQLite. PDF validation checks basic format markers and does not scan for malware.
Aggregate storage quotas, automated backup and automatic cleanup of upload
orphans after a hard crash are not implemented. Rate-limit counters are local
to one process. Deletion removes the application's files and records, without
providing secure erasure of backups or previously downloaded copies.

## Run and review

Follow the [README setup instructions](../README.md#running-locally). The
[commit history](https://github.com/jpaulobaptista2000-code/secure-file-manager/commits/main)
shows the implementation increments. The
[submission file](checkpoint-2-submission.txt) contains direct links for Moodle.
