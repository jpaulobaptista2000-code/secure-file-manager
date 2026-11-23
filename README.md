# Secure File Manager

Final project for **ICS0027 Web Application Security**. Sign in, upload a PDF or text file, and download or delete it later. The server encrypts every file before saving it. Each account can see only its own files.

[Final report](Final_Report.pdf) · [Test results](tests/RESULTS.md) · [GitHub repository](https://github.com/jpaulobaptista2000-code/secure-file-manager)

## Running locally

These instructions are for Windows PowerShell, Python 3.13 and Chrome or Edge. The app uses SQLite, so you do not need to install a database server.

1. **Open the project folder.** If you have the Moodle ZIP, choose **Extract All**, then open a terminal in the folder containing `run.py` and this README. If you prefer Git, clone the repository instead:

   ```powershell
   git clone https://github.com/jpaulobaptista2000-code/secure-file-manager.git
   Set-Location secure-file-manager
   ```

2. **Install the Python dependencies.** If needed, install [Python 3.13 for Windows](https://www.python.org/downloads/windows/) with the Python launcher first.

   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

### Create the HTTPS certificate

3. **Install [mkcert](https://github.com/FiloSottile/mkcert)** if `mkcert -version` does not work. Reopen PowerShell in the project folder after installing it.

   ```powershell
   winget install --id FiloSottile.mkcert --exact --source winget
   ```

4. **Create the local certificate** once per installation. Accept the Windows trust prompt for your local development certificate authority. If this project folder already has a working certificate, keep it.

   ```powershell
   mkcert -install
   New-Item -ItemType Directory -Force certs | Out-Null
   mkcert -cert-file certs/localhost.pem -key-file certs/localhost-key.pem localhost 127.0.0.1 ::1
   ```

### Start and use the app

5. **Start the server** and leave PowerShell open:

   ```powershell
   .\.venv\Scripts\python.exe run.py
   ```

   Open **https://127.0.0.1:5000**. Use that same address throughout the session. Select **Create account** (username: 3–30 letters `a–z`, digits or underscores; password: 15–128 characters), then **Sign in**. In **My files**, choose a nonempty PDF or UTF-8 TXT up to 5 MiB and select **Upload and encrypt**. **Download** restores the original contents; **Delete** asks for confirmation.

Press **Ctrl+C** in PowerShell to stop. Next time, only step 5 is needed. Keep `instance/`: it holds your local accounts, file metadata, encrypted files and keys. The database is created on first launch. `certs/` and `instance/` are local and are not distributed.

## Run the tests

From the project folder, with the Python dependencies installed:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Tests create their own temporary accounts and files. They do not use your normal `instance/` data or require a running server. The [test record](tests/RESULTS.md) explains the two expected Windows skips.

The final application is on `main`. Earlier versions remain available: [architecture](https://github.com/jpaulobaptista2000-code/secure-file-manager/tree/checkpoint/01-foundation), [Checkpoint 2](https://github.com/jpaulobaptista2000-code/secure-file-manager/tree/ed158e3ecea6f5775d77f891fdb8ad417d9a9d80) and [Checkpoint 3](https://github.com/jpaulobaptista2000-code/secure-file-manager/tree/checkpoint-3).
