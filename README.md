# Secure File Manager

**ICS0027 Web Application Security | Project 1 | Checkpoint 1 draft**

A semester project for a web application that lets each user upload, list,
download and delete their own encrypted files. Encryption happens on the server;
HTTPS protects the connection between the browser and the server.

## Current status

This is an initial design and a small executable foundation. It is not yet a
working file manager, and Checkpoint 1 still requires the student's review and
in-class verification.

| Available now | Planned next |
| --- | --- |
| Architecture, threat model and checkpoint plan | Registration, login, logout and server-side sessions |
| Local HTTPS development server and health endpoint | Database, ownership checks and file operations |
| AES-256-GCM prototype with tamper-rejection tests | Persistent key storage and deletion workflow |
| CSP, host validation and generic HTTP errors | CSRF on forms, upload validation and structured audit logs |

## Start reading here

1. [Checkpoint 1 design](docs/checkpoint-1.md): scope, diagram, stack, encryption,
   authentication, routes and requirement mapping.
2. [Threat model](docs/threat-model.md): attacks, planned mitigations and tests.
3. [Checkpoint plan](docs/checkpoints.md): dates, evidence and remaining decisions.
4. [Learning guide](docs/learning-guide.md): explanations and presentation questions.
5. [Validation record](docs/validation.md): what was actually tested in this version.

The academic requirements are from the lecturer's *Project.pdf*, sections 1-3,
2026/2027 edition. The lecturer's PDF is not redistributed in this repository.

## Run locally

Prerequisites: Git, Python **3.12**, and internet access to install dependencies.
The commands start in a terminal on your computer. On Windows use PowerShell.

```text
git clone https://github.com/jpaulobaptista2000-code/secure-file-manager.git
cd secure-file-manager
git switch checkpoint/01-foundation
```

Windows, without changing PowerShell's execution policy:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/create_dev_cert.py
.\.venv\Scripts\python.exe -m secure_file_manager
```

Linux or macOS with Python 3.12 installed:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/create_dev_cert.py
.venv/bin/python -m secure_file_manager
```

Open **https://localhost:5443**. The initial page and `/health` should respond.
Stop the server with **Ctrl+C**. It binds to `127.0.0.1` only.

The certificate is self-signed and lasts seven days. The browser will initially
warn because it does not trust that certificate. For this localhost-only scaffold,
an exception is possible; do not interpret it as trusted server authentication.
Checkpoint 2 includes establishing local certificate trust and verifying the
connection without an exception. Never disable certificate verification globally.
To regenerate an expired certificate, remove only the two generated files inside
`certs/`, then rerun the generator. It deliberately refuses to overwrite them.

No database or secret configuration is needed for this scaffold. It cannot accept
uploads or user credentials. Private certificate keys are local and Git-ignored.
POSIX permissions are set by the generator; Windows access must be restricted
with NTFS permissions on the local project directory.

## Run the prototype and tests

Replace `python` below with the virtual environment's Python path used above:

```text
python -m secure_file_manager.crypto_demo
python -m pytest -q
```

The demo uses synthetic bytes in memory, never prints a key, and checks exact
recovery, ciphertext tampering and a different owner binding. It does **not**
demonstrate HTTP authorization or persistent encrypted storage.

## Planned application routes

| Method | Route | Purpose | Current state |
| --- | --- | --- | --- |
| GET | `/`, `/health` | Initial page and process health | Implemented |
| GET, POST | `/register` | Create account | Planned |
| GET, POST | `/login` | Authenticate | Planned |
| POST | `/logout` | Revoke session | Planned |
| GET | `/files` | List current user's files | Planned |
| POST | `/files/upload` | Validate and encrypt one file | Planned |
| GET | `/files/<uuid>/download` | Authorize, decrypt and download | Planned |
| POST | `/files/<uuid>/delete` | Authorize and delete | Planned |

All future state-changing forms, including login, require CSRF validation.
File access requires authentication and an owner check on the server.

## Development approach

Use real, incremental commits during the semester. This branch is the first
foundation; future checkpoint evidence must describe the work completed at that
time. Keep documents and source in English. Commit neither secrets nor uploaded
files, databases, certificates, real test credentials or sensitive attack captures.

The TLS runner uses Flask's development server. A production deployment is outside
this initial checkpoint. Runtime dependency versions are pinned to those validated
for this draft; pinning does not replace later dependency review.
