# Secure File Manager

ICS0027 Web Application Security - Project 1.

Checkpoint 2, step 2: local HTTPS, account registration, login, logout and
SQLite-backed sessions are implemented. File uploads, encryption and file
management are still planned. This is not yet the complete Checkpoint 2 submission.

Read the [short design document](docs/architecture.md).
The design document describes the planned system; the
[progress note](docs/checkpoint-2-progress.md) records implementation progress.

## Scope and planned features

- Register, log in and log out (implemented).
- Upload, list, download and delete the user's own PDF and text files.
- Encrypt files on the server and check ownership before granting access.

File sharing and document previews are outside the initial scope.

## Routes and implementation status

| Method | Route | Purpose |
| --- | --- | --- |
| GET | / | Welcome page (implemented) |
| GET, POST | /register | Create an account (implemented) |
| GET, POST | /login | Sign in (implemented) |
| POST | /logout | End the session (implemented) |
| GET | /files | Protected account page; actual file listing is still planned |
| POST | /files/upload | Upload a file (planned) |
| GET | /files/{file_id}/download | Download an owned file (planned) |
| POST | /files/{file_id}/delete | Delete an owned file (planned) |

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

On first startup, the application automatically creates its SQLite database and
a random application secret in `instance/`. No separate database installation or
initialization command is needed.

### Updating an existing step 1 installation

Stop the server with Ctrl+C, and run the following in the project folder. Check
`git status` first; preserve any local source-code changes before pulling.

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Keep your existing `.venv` and `certs/` folders. The new dependencies are installed
into the existing environment, and the local certificate is reused.

### Try registration and login

1. Open https://localhost:5000 and choose **Create account**.
2. Choose a username with 3–30 letters (a–z), numbers or underscores. Usernames
   are case-insensitive. Choose a password with 15–128 characters; spaces and
   Unicode are accepted, and passwords are never silently trimmed or truncated.
3. Registration takes you to **Sign in**. An incorrect password should be rejected.
4. Sign in with the correct password. The protected page should welcome you by
   username. File-management controls will be added in the next stage.
5. Choose **Sign out**, then try https://localhost:5000/files directly. You should
   be sent to the sign-in page. The same applies in a separate private window.
6. Restart the server and sign in again: your account should still exist.

Use the same hostname throughout the demonstration. `localhost` and `127.0.0.1`
are different cookie hosts, so each has a separate browser session.

### Authentication and local data

- Passwords are salted Argon2id hashes produced by `argon2-cffi`.
- Flask-Session keeps session data in SQLite. The cookie contains a random
  identifier, with `Secure`, `HttpOnly` and `SameSite=Lax` flags.
- Authentication expires after 15 minutes of inactivity or 2 hours in total,
  enforced on the server. Login replaces the session ID; logout deletes the
  server session. Browser-side edits cannot grant authentication.
- Flask-WTF checks CSRF tokens on every POST, including registration, login and
  logout. Same-origin HTTPS referrers are retained for its additional check.
- Flask-Limiter allows 5 POST submissions per minute per client IP on each of
  `/login` and `/register`, including successful submissions. This local version
  keeps rate-limit counters in memory; they reset when the server restarts and
  are not shared between server processes. A deployed version would need shared
  persistent rate-limit storage.
- The current form request limit is 16 KiB. The upload stage will define separate
  file limits. Dynamic pages use `Cache-Control: no-store`.

`instance/file_manager.sqlite3` holds accounts and sessions. `instance/secret.key`
is a randomly generated application secret used to sign CSRF tokens; it is not
a file-encryption key. Keep the instance folder between restarts. It is private,
excluded from Git and not served by the website. Expired database sessions are
cleaned up periodically during requests.

### Automated authentication checks

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests create a separate temporary database and leave your accounts alone.
They cover password hashing, invalid credentials, form validation, CSRF,
rate limiting, session rotation, expiry, logout replay and protected access.

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
| A security-token error appears | Reopen the form to get a fresh token, use the same hostname, and submit again. |
| Too many attempts (429) | Wait a minute before submitting the login or registration form again. |

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
| `app.py` | Configures the application, sessions, request checks and protected page. |
| `auth.py` | Handles registration, login and logout. |
| `models.py` | Defines the user record stored in SQLite. |
| `security.py` | Handles password checks, the local secret and session expiry/rotation. |
| `extensions.py` | Connects the database, session, CSRF and rate-limit libraries. |
| `templates/` | Defines the home page, forms and protected account page. |
| `static/style.css` | Defines its appearance. |
| `requirements.txt` | Lists the Python dependencies for installation. |
| `.gitignore` | Keeps generated files and local secrets out of commits. |

## Next steps

1. Add validated uploads and server-side AES-256-GCM encryption.
2. Add ownership-checked listing, download/decryption and deletion.
3. Test the file-security boundaries and complete the Checkpoint 2 progress note.

Keep one meaningful commit for each completed increment.

## Setup references

- [Flask installation and virtual environments](https://flask.palletsprojects.com/en/stable/installation/)
- [Werkzeug development server and TLS](https://werkzeug.palletsprojects.com/en/stable/serving/)
- [mkcert documentation](https://github.com/FiloSottile/mkcert)
- [Argon2 password hashing](https://argon2-cffi.readthedocs.io/en/stable/howto.html)
- [Flask-Session security](https://flask-session.readthedocs.io/en/latest/security.html)
- [Flask-WTF CSRF protection](https://flask-wtf.readthedocs.io/en/stable/csrf/)
- [Flask-Limiter](https://flask-limiter.readthedocs.io/en/stable/)
