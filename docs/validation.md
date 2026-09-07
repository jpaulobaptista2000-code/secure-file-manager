# Checkpoint 1 validation record

**Observed on:** 7 September 2026, 23:24 UTC  
**Environment:** Linux, Python 3.12.13, isolated virtual environment  
**Scope:** The initial scaffold and in-memory cryptographic prototype.

## Observed results

| Check | Result |
| --- | --- |
| Install `requirements-dev.txt` in a second, newly created virtual environment | Passed; installed pinned packages successfully |
| `python -m pip check` | No broken requirements found |
| `python -m pytest -q` in that second environment | **21 passed in 0.12s** |
| `python -m secure_file_manager.crypto_demo` | Round-trip, tampering and changed-owner rejection passed |
| Generate local certificate and start the documented runner | Passed |
| Real `/health` request with certificate verification enabled and the generated certificate explicitly trusted by the test client | HTTP 200 and expected foundation status |
| TLS handshake | Negotiated TLS 1.3 |
| Plain HTTP request to the TLS port | Rejected |
| Rerun certificate generator while key/certificate exist | Refused to overwrite existing material |
| Git ignore checks for generated certificate and private key | Both excluded |

The HTTPS test used Python's `ssl.create_default_context(cafile=...)` and urllib,
not `verify=False` or a global TLS-verification bypass. Browser certificate trust
on the student's Windows laptop has **not** been configured or tested.

To reproduce the HTTPS health check while the local server is running:

```python
import ssl
import urllib.request

context = ssl.create_default_context(cafile="certs/localhost.pem")
with urllib.request.urlopen(
    "https://localhost:5443/health", context=context, timeout=5
) as response:
    print(response.status, response.read().decode())
```

## Test coverage

`tests/test_crypto.py` contains 13 test cases: binary recovery; rejection of changed
version, nonce, ciphertext, tag, key, owner and file identifier; truncated payload;
independent keys; zero/oversized input; and recovery at the 5 MiB limit.

`tests/test_app.py` contains 8 test cases: truthful health status; security headers
on three routes; Host rejection; generic missing-resource responses; unsupported
method rejection; and generic handling of an internal exception.

## Not yet verified or implemented

- User authentication, session cookies, rotation, expiry and logout revocation.
- Database storage and cross-user authorization through HTTP routes.
- Persistent key storage, upload parsing and secure deletion behavior.
- CSRF and SQL-injection defenses in the future account/file operations.
- Structured audit logging and dependency vulnerability scanning.
- Windows installation and a browser demonstration on the student's computer.
- GitHub Actions / CI; no CI workflow is included in this foundation.

Passing prototype tests does not establish that the planned application is secure.
The planned TEST-01 to TEST-15 cases are in [the threat model](threat-model.md).
Record new evidence as features are implemented, retaining the actual commit SHA.
