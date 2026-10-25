# Secure File Manager

ICS0027 Web Application Security - Project 1.

Checkpoint 2, step 1: the Flask home page and local HTTPS startup are implemented.
Authentication, database storage and file encryption are still planned. This is
not yet the complete Checkpoint 2 submission.

Read the [short design document](docs/architecture.md).
The design document describes the planned system; the
[progress note](docs/checkpoint-2-progress.md) records implementation progress.

## Scope and planned features

- Register, log in and log out.
- Upload, list, download and delete the user's own PDF and text files.
- Encrypt files on the server and check ownership before granting access.

File sharing and document previews are outside the initial scope.

## Planned routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | / | Welcome page (implemented) |
| GET, POST | /register | Create an account |
| GET, POST | /login | Sign in |
| POST | /logout | End the session |
| GET | /files | List the user's files |
| POST | /files/upload | Upload a file |
| GET | /files/{file_id}/download | Download an owned file |
| POST | /files/{file_id}/delete | Delete an owned file |

## Running locally

These instructions use Windows PowerShell and a local HTTPS certificate. The
application runs on your computer; GitHub stores its source code and history.

### 1. Check the prerequisites

Use Python 3.12 or newer, Git, and mkcert. In PowerShell, check:

```powershell
py -3 --version
git --version
winget --version
```

If Python or Git is missing, install it from
[Python for Windows](https://www.python.org/downloads/windows/) or
[Git for Windows](https://git-scm.com/download/win), then reopen PowerShell.
With WinGet available, install mkcert:

```powershell
winget install --id FiloSottile.mkcert --exact --source winget
```

Reopen PowerShell after installation and run `mkcert -version`.
If WinGet is unavailable, use the Windows installation options in the
[official mkcert documentation](https://github.com/FiloSottile/mkcert#windows).

### 2. Get the project

Run these commands once to create a new local copy:

```powershell
Set-Location $env:USERPROFILE
New-Item -ItemType Directory -Force Projects | Out-Null
Set-Location Projects
git clone https://github.com/jpaulobaptista2000-code/secure-file-manager.git
Set-Location secure-file-manager
```

If you already cloned the repository, open PowerShell in that folder instead.
Run `git status` first. If the working tree is clean, use `git pull --ff-only`
to get the latest version. Preserve any local changes before updating.

### 3. Install the Python dependencies

From the folder containing `requirements.txt`:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The `.venv` folder keeps this project's Python packages separate from other
projects. These commands use its Python executable directly, so no environment
activation or PowerShell execution-policy changes are needed.

### 4. Create the HTTPS certificate

Run these commands from the same project folder:

```powershell
mkcert -install
New-Item -ItemType Directory -Force certs | Out-Null
mkcert -cert-file certs/localhost.pem -key-file certs/localhost-key.pem localhost 127.0.0.1 ::1
```

`mkcert -install` creates a local certificate authority and adds it to the
computer's trusted certificates. Review any Windows confirmation prompt. This
lets your browser trust the development certificate. Use Edge or Chrome for the
first demonstration, and restart the browser after installing the authority.

Generate these files on each computer. The TLS private key and mkcert's
`rootCA-key.pem` must stay private; do not upload or share them. The `certs/`
folder and key files are excluded from Git. These certificates protect the
browser connection; file-encryption keys will be added in a later step.

### 5. Start and open the application

```powershell
.\.venv\Scripts\python.exe run.py
```

Leave PowerShell open and visit **https://localhost:5000** in your browser.
You should see the Secure File Manager home page without a certificate warning.
If localhost does not connect, try **https://127.0.0.1:5000**.

Stop the server with **Ctrl+C**. To start it again, open PowerShell in the project
folder and repeat the same `run.py` command. Restart it after editing Python
files; automatic reloading is disabled.

The server listens only on `127.0.0.1:5000`, uses TLS 1.2 or newer, and keeps the
interactive debugger disabled. This is Flask's local development server, not a
public hosting setup. The documented startup refuses to run without TLS files.

### Troubleshooting

| Symptom | What to check |
| --- | --- |
| `py` or `git` is not recognized | Install the missing tool and reopen PowerShell. |
| `mkcert` is not recognized | Reopen PowerShell; if the command is still missing, follow the PATH check below. |
| Missing TLS files | Complete step 4 in the project folder. |
| Browser certificate warning | Check `mkcert -install`, restart the browser, and use `localhost` or `127.0.0.1`. Fix the trust problem before the demonstration. |
| Port 5000 already in use | Stop an earlier project server with Ctrl+C, then start this one. |
| Connection fails | Keep the server terminal open and include `https://` in the address. |
| `GET /favicon.ico` returns 404 | The optional browser-tab icon has not been added. This does not prevent the page or HTTPS from working. |

If mkcert is installed but PowerShell cannot find it, first confirm the installation:

```powershell
winget list --id FiloSottile.mkcert --exact
```

If mkcert appears in the list, reload the saved system and user PATH values into
the current PowerShell session, then check the version again:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
mkcert -version
```

PATH is the list of directories used to find commands. This refresh resolved the
command lookup problem during the Windows setup on 26 October 2026.

### How the files fit together

| File | Role |
| --- | --- |
| `run.py` | Loads the local TLS certificate and starts the server. |
| `app.py` | Creates the Flask application and handles the home-page request. |
| `templates/index.html` | Defines the content of the page. |
| `static/style.css` | Defines its appearance. |
| `requirements.txt` | Lists the Python dependencies for installation. |
| `.gitignore` | Keeps generated files and local secrets out of commits. |

## Next steps

1. Add SQLite, registration, login, logout and server-side sessions.
2. Add validated uploads and server-side AES-256-GCM encryption.
3. Add ownership-checked listing, download/decryption and deletion.
4. Test the security boundaries and complete the Checkpoint 2 progress note.

Keep one meaningful commit for each completed increment.

## Setup references

- [Flask installation and virtual environments](https://flask.palletsprojects.com/en/stable/installation/)
- [Werkzeug development server and TLS](https://werkzeug.palletsprojects.com/en/stable/serving/)
- [mkcert documentation](https://github.com/FiloSottile/mkcert)
