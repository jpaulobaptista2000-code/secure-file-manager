# Secure File Manager

ICS0027 Web Application Security - Project 1.

Checkpoint 2, step 4: local HTTPS, accounts, server-side sessions, validated
uploads, AES-256-GCM encryption, personal file lists, authenticated downloads
and confirmed deletion are implemented. The student has confirmed the Windows
TXT/PDF flows, rejection of another account's direct download link and PDF access
after restarting the application. The Windows test suite passed with one expected
POSIX-only skip. Fresh-setup verification and submission review are still pending.

Read the [short design document](docs/architecture.md).
The design document describes the planned system; the
[progress note](docs/checkpoint-2-progress.md) records implementation progress.

## Scope and implemented features

- Register, log in and log out (implemented).
- Upload and list the user's own PDF and text files (implemented).
- Encrypt file contents on the server (implemented).
- Download/decrypt and delete owned files (implemented).

File sharing and document previews are outside the initial scope.

## Routes and implementation status

| Method | Route | Purpose |
| --- | --- | --- |
| GET | / | Welcome page (implemented) |
| GET, POST | /register | Create an account (implemented) |
| GET, POST | /login | Sign in (implemented) |
| POST | /logout | End the session (implemented) |
| GET | /files | Upload form and owner-filtered, paginated file list (implemented) |
| POST | /files/upload | Validate, encrypt and save one file (implemented) |
| GET | /files/{file_id}/download | Authenticate/decrypt and download an owned file (implemented) |
| GET | /files/{file_id}/confirm-delete | Show the owner's deletion confirmation (implemented) |
| POST | /files/{file_id}/delete | Delete an owned file after a CSRF check (implemented) |

## Running locally

These instructions use Windows PowerShell and a local HTTPS certificate. The
application runs on your computer; GitHub stores its source code and history.

### 1. Check the prerequisites

Use Python 3.13 or newer on Windows, Git, and mkcert. Python 3.13 supports
creating private directories with Windows access controls. In PowerShell, check:

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
browser connection; separate file-encryption keys are generated on each upload.

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

On first startup, the application automatically creates its SQLite database,
a random application secret, and private `storage/` and `keys/` folders inside
`instance/`. No separate database installation or initialization command is needed.
Upgrading adds any missing file-metadata/deletion-marker tables and keeps
existing accounts, keys and encrypted files. No database reset is needed.

### Updating an existing installation

Stop the server with Ctrl+C, and run the following in the project folder. Check
`git status` first; preserve any local source-code changes before pulling.

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Keep your existing `.venv`, `certs/` and `instance/` folders. The new dependencies
are installed into the existing environment, and the local certificate and
account database are reused. Do not delete the instance folder when updating.

### Try registration and login

1. Open https://localhost:5000 and choose **Create account**.
2. Choose a username with 3–30 letters (a–z), numbers or underscores. Usernames
   are case-insensitive. Choose a password with 15–128 characters; spaces and
   Unicode are accepted, and passwords are never silently trimmed or truncated.
3. Registration takes you to **Sign in**. An incorrect password should be rejected.
4. Sign in with the correct password. The protected page should welcome you by
   username and show an upload form and your file list.
5. Choose **Sign out**, then try https://localhost:5000/files directly. You should
   be sent to the sign-in page. The same applies in a separate private window.
6. Restart the server and sign in again: your account should still exist.

Use the same hostname throughout the demonstration. `localhost` and `127.0.0.1`
are different cookie hosts, so each has a separate browser session.

### Try an encrypted upload

1. Sign in. Create a small test file in Windows Notepad, save it as `teste.txt`
   using UTF-8 encoding, and put a sentence in it.
2. In **My files**, select it and choose **Upload and encrypt**.
3. The success message and an **Encrypted** row should appear. Names are
   normalized for safety: spaces become underscores and accented characters
   may be simplified.
4. Refresh the page or restart the application. The file should remain listed.
5. Sign in with a second test account (or use a private window). The first
   account's filenames should not appear.

One nonempty PDF or UTF-8 TXT file is accepted per request, up to **5 MiB**
(5,242,880 bytes). Uploading the same filename twice creates two independent
files. Use the **Download** and **Delete** controls beside each file.

### Try download and deletion

1. Sign in to the account that uploaded `teste.txt`. Choose **Download**, open
   the saved copy and compare its contents with the original.
2. Copy that file's Download link. In a private browser window, sign in with
   the second account and paste the link. It must show **File not found**.
   Signing out altogether must redirect the same link to **Sign in**.
3. Return to the owner account and choose **Delete**. Check the filename on the
   confirmation page. Choosing **Cancel** must leave the file available.
4. Choose **Delete** again, then **Delete file**. The success message should
   appear and the row should disappear. The old download link must no longer work.
5. Repeat with a small test PDF. Restart the server before downloading it to
   confirm that its account, metadata, contents and key persist.

Use disposable test documents for this walkthrough. Deletion cannot be undone
through the application; it does not erase existing downloads, backups or old
disk blocks.

### How file storage works

- Flask obtains the owner from the authenticated server session. An `owner_id`
  supplied in the browser cannot change ownership. Every list query filters
  by this owner, including pagination (20 files per page).
- The server checks the extension, size and content: TXT must decode as UTF-8
  without binary control characters; PDFs must have an expected header and
  end marker. Browser MIME types are not trusted. The PDF check is basic format
  validation, **not** a full parser, antivirus scan or guarantee of safe content.
- Uploads are kept in bounded memory before encryption, using a custom Flask
  request stream so larger files are not spooled into plaintext temporary files.
  This does not control operating-system swap or memory dumps.
- `cryptography` generates a fresh random 256-bit key and a 12-byte nonce for
  each file. AES-GCM encrypts and authenticates the contents. The file ID,
  owner, normalized name, media type and size are authenticated as additional
  data, so changing this metadata makes authenticated decryption fail.
- `instance/storage/<random-id>.enc` contains `SFM1`, the nonce, ciphertext and
  a 16-byte authentication tag. `instance/keys/<random-id>.key` holds the
  separate 32-byte key. Exclusive file creation prevents overwrite collisions.
- SQLite stores metadata (including readable filenames and owners), not file
  contents or encryption keys. Neither private folder has a web route, and all
  of `instance/` is excluded from Git. The website does not preview uploads.
- New storage directories use mode `0700`. On Windows with Python 3.13+, this
  restricts them to the current Windows user and administrators; files inherit
  the folder ACLs. On POSIX systems the directories use `0700` and files `0600`.
  Keep these folders private; existing Windows ACLs are not reset on restart.

The server can decrypt the files because it holds the keys. This is server-side
encryption, not end-to-end encryption. Loss of a file's key means loss of access
to its contents; retain the database, encrypted files and keys together in any
private backup. Do not commit them or share them with a submission.

Handled write/database failures roll back the new record and remove files
created by that upload. A hard process crash can still leave orphan files;
automatic reconciliation is not implemented. This local version has per-file
size limits and an upload rate limit, but no total account-storage quota.

### Download and deletion security

- Every download, deletion confirmation and deletion POST selects the file by
  both its identifier and the authenticated account ID. Unknown and foreign
  file identifiers receive the same 404 response, before accessing storage.
  Query parameters and form fields cannot choose the owner or storage path.
- Downloads check the stored format, key length and bounded file size, then
  authenticate the whole file with AES-GCM before returning any plaintext.
  Missing files/keys or failed authentication return a generic error without
  an attachment. Decrypted data stays in memory; no plaintext temporary file
  is created by the download handler.
- Downloads use `Content-Disposition: attachment`, `application/octet-stream`,
  `X-Content-Type-Options: nosniff` and `Cache-Control: no-store`. Conditional
  and range responses are disabled; successful requests return the full file.
- The confirmation page is a read-only GET. The actual deletion is a CSRF-
  protected POST and checks ownership again. It first commits a deletion marker
  to SQLite, which blocks subsequent downloads. It then removes the key and
  ciphertext, and finally removes the metadata and marker.
- If deletion is interrupted after the marker is committed, **Deletion pending**
  and **Retry delete** appear in the owner's list. Retrying tolerates already
  missing files, so cleanup can finish after a restart or a handled disk/database
  failure. A failed initial marker commit leaves the file intact. Automatic
  background retries are not implemented. A download already in flight may finish.

### Authentication and local data

- Passwords are salted Argon2id hashes produced by `argon2-cffi`.
- Flask-Session keeps session data in SQLite. The cookie contains a random
  identifier, with `Secure`, `HttpOnly` and `SameSite=Lax` flags.
- Authentication expires after 15 minutes of inactivity or 2 hours in total,
  enforced on the server. Login replaces the session ID; logout deletes the
  server session. Browser-side edits cannot grant authentication.
- Flask-WTF checks CSRF tokens on every POST, including registration, login,
  logout, uploads and deletion. Same-origin HTTPS referrers are retained for its additional check.
- Flask-Limiter allows 5 POST submissions per minute per client IP on each of
  `/login` and `/register`, including successful submissions. This local version
  keeps rate-limit counters in memory; they reset when the server restarts and
  are not shared between server processes. A deployed version would need shared
  persistent rate-limit storage.
- Uploads allow 10 POST submissions per minute per account, using the same
  in-memory rate-limit store. Authenticated upload requests allow 5 MiB plus
  64 KiB of multipart overhead, with at most 8 form parts and a 128 KiB field
  memory limit. Each individual file remains limited to 5 MiB. Other requests
  retain the 16 KiB limit. Dynamic pages use `Cache-Control: no-store`.
- Downloads allow 30 requests per minute per account; deletion POSTs allow 10.
  These use the same in-memory limiter and also count failed authorized requests.

`instance/file_manager.sqlite3` holds accounts, sessions, file metadata and pending
deletion markers. `instance/secret.key`
is a randomly generated application secret used to sign CSRF tokens; it is not
a file-encryption key. Keep the instance folder between restarts. It is private,
excluded from Git and not served by the website. Expired database sessions are
cleaned up periodically during requests.

### Automated security checks

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests use temporary databases and storage, leaving your accounts and files
alone. They cover authentication, sessions, CSRF, ownership, type/size/path
validation, rate limits, encrypted storage, byte-for-byte downloads, tampering,
pagination, cross-account URL access, CSRF-protected deletion and recovery from
simulated disk/database failures. Expected failure tests may print error log
lines; the final unittest result indicates whether the checks passed.

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
| Too many attempts (429) | Wait a minute before retrying the action. |
| Request too large (413) during upload | Choose one file no larger than 5 MiB and reopen the upload form. |
| TXT encoding rejected | Save the document as UTF-8 in Notepad and retry. |
| Storage permissions error on Windows | Use Python 3.13+ and keep the project under your own user profile on a filesystem with Windows ACLs, such as NTFS. |
| File not found (404) | Check that you are signed in as the owner. Deleted files and files pending deletion cannot be downloaded. |
| Download unavailable (503) | The ciphertext/key is missing, unreadable or failed authentication. Keep the existing data; restore a consistent private backup if available. |
| Deletion incomplete (503) | Return to My files and retry deletion after resolving the storage/database problem. A pending file remains blocked from download. |

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
| `models.py` | Defines users, file metadata and deletion markers in SQLite. |
| `security.py` | Handles password checks, the local secret and session expiry/rotation. |
| `file_routes.py` | Validates uploads and checks ownership for listing, download and deletion. |
| `encrypted_storage.py` | Manages private folders, authenticated encryption/decryption and retryable deletion. |
| `upload_request.py` | Keeps size-limited uploads in memory before encryption. |
| `extensions.py` | Connects the database, session, CSRF and rate-limit libraries. |
| `templates/` | Defines the home page, forms and protected account page. |
| `static/style.css` | Defines its appearance. |
| `requirements.txt` | Lists the Python dependencies for installation. |
| `.gitignore` | Keeps generated files and local secrets out of commits. |

## Next steps

1. Verify setup from a fresh clone and virtual environment on Windows.
2. Review the Checkpoint 2 progress note and submission links.

Keep one meaningful commit for each completed increment.

## Setup references

- [Flask installation and virtual environments](https://flask.palletsprojects.com/en/stable/installation/)
- [Werkzeug development server and TLS](https://werkzeug.palletsprojects.com/en/stable/serving/)
- [mkcert documentation](https://github.com/FiloSottile/mkcert)
- [Argon2 password hashing](https://argon2-cffi.readthedocs.io/en/stable/howto.html)
- [Flask-Session security](https://flask-session.readthedocs.io/en/latest/security.html)
- [Flask-WTF CSRF protection](https://flask-wtf.readthedocs.io/en/stable/csrf/)
- [Flask-Limiter](https://flask-limiter.readthedocs.io/en/stable/)
- [Flask file uploads](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
- [cryptography AES-GCM](https://cryptography.io/en/latest/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM)
- [OWASP file-upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [Python 3.13 directory permissions](https://docs.python.org/3.13/library/os.html#os.mkdir)
- [OWASP object-level authorization](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)
- [Flask download responses](https://flask.palletsprojects.com/en/stable/api/#flask.send_file)
