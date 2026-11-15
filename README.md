# Secure File Manager

A student project for ICS0027 Web Application Security. Users can register, sign
in, upload, download and delete their own PDF and TXT files. File contents are
encrypted on the server.

Current work is on **`checkpoint-3`**. The earlier Checkpoint 2 version is retained
on `main`, and Checkpoint 1 is on `checkpoint/01-foundation`.

## Documentation

- [Checkpoint 1: architecture and threat model](docs/architecture.md)
- [Checkpoint 2: implemented features and verification](docs/checkpoint-2-progress.md)
- [Checkpoint 3: current progress](docs/checkpoint-3-progress.md)
- [Security tests, attack examples and evidence](docs/checkpoint-3-security-tests.md)

## Running locally

Use **Windows PowerShell**, **Python 3.13 or newer**, **Git** and **mkcert**.
If Python or Git is missing, install it from [python.org](https://www.python.org/downloads/windows/)
or [git-scm.com](https://git-scm.com/download/win).

### 1. Install mkcert

```powershell
winget install --id FiloSottile.mkcert --exact --source winget
```

Reopen PowerShell and check that `py -3 --version`, `git --version` and
`mkcert -version` work.

### 2. Download the project and install dependencies

```powershell
Set-Location $env:USERPROFILE
New-Item -ItemType Directory -Force Projects | Out-Null
Set-Location Projects
git clone --branch checkpoint-3 https://github.com/jpaulobaptista2000-code/secure-file-manager.git
Set-Location secure-file-manager
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

These commands are for a new copy. For an existing installation, use the update
instructions below. No virtual-environment activation is needed.

### 3. Create the HTTPS certificate

```powershell
mkcert -install
New-Item -ItemType Directory -Force certs | Out-Null
mkcert -cert-file certs/localhost.pem -key-file certs/localhost-key.pem localhost 127.0.0.1 ::1
```

Approve the Windows certificate prompt. Generate certificates locally and keep
private keys out of Git. See the [mkcert documentation](https://github.com/FiloSottile/mkcert)
if installation fails.

### 4. Start the application

```powershell
.\.venv\Scripts\python.exe run.py
```

Keep PowerShell open and visit **https://127.0.0.1:5000** in Chrome or Edge.
Register with a username of 3–30 letters, numbers or underscores and a password
of 15–128 characters. Sign in and upload a nonempty PDF or UTF-8 TXT file up to
**5 MiB**. Use **My files** to download or delete it.

Stop with **Ctrl+C**. To restart, run the same command from the project folder.
The database is created automatically. Keep `instance/`: it contains the accounts,
encrypted files, keys and private logs. Use the same hostname throughout a session.

### Updating an existing installation

Stop the server and open PowerShell in the project folder. Check `git status`
and preserve any local edits before updating.

```powershell
git fetch origin
git switch checkpoint-3
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

If the local branch does not exist, use `git switch --track origin/checkpoint-3`.
Keep the existing `.venv/`, `certs/` and `instance/` folders.

## Security and tests

- Argon2id password hashing and server-side sessions with secure cookies,
  session-ID rotation, logout invalidation and expiry.
- Ownership checks on every file operation, CSRF protection, escaped HTML and
  parameterized database queries.
- AES-256-GCM encryption, server-side upload validation, request limits and HTTPS.
- Generic errors and private structured logs without passwords, cookies or tokens.

Run the automated tests from the project folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests use temporary data. Windows skips POSIX permission checks; those skips do
not verify Windows ACLs. See the [security test record](docs/checkpoint-3-security-tests.md)
for results, browser demonstrations and the remaining Windows logging check.

This is a local development application. The server holds the encryption keys,
PDF checks are not malware scanning, and deletion does not erase backups or
previous downloads. Public hosting, account storage quotas and remote logging
are outside the current scope.

## Code overview

| File or folder | Purpose |
| --- | --- |
| `run.py`, `app.py` | Start HTTPS and configure Flask. |
| `auth.py`, `security.py` | Accounts, passwords and sessions. |
| `models.py`, `extensions.py` | Database models and Flask extensions. |
| `file_routes.py`, `upload_request.py` | File operations and upload validation. |
| `encrypted_storage.py` | Encryption, private storage and deletion. |
| `audit.py` | Private security logging. |
| `templates/`, `static/` | Web pages and styling. |
| `tests/` | Automated functionality and security checks. |
| `requirements.txt` | Python dependencies. |

## Common setup issues

| Problem | Action |
| --- | --- |
| A command is not recognized | Install the tool and reopen PowerShell. |
| Certificate warning | Run `mkcert -install`, restart the browser and use the address above. |
| Port 5000 is in use | Stop the other server with Ctrl+C. |
| Security-token error | Reopen the form and use the same hostname. |
| Too many attempts | Wait a minute before retrying. |
| TXT upload rejected | Save it as UTF-8 and check the size. |
| Download or deletion unavailable | Keep the local data; check storage permissions. A pending deletion can be retried. |
