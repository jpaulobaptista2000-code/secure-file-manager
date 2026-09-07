# Understanding the project before writing more code

## What are we building?

A private file cabinet accessed through a browser. Each account has its own list
of files. The application decides who may access each file and transforms the
contents into ciphertext before storing them.

## What does each part do?

| Term | Meaning in this project |
| --- | --- |
| Browser / frontend | Shows pages and sends requests; the user can change those requests. |
| Backend / Flask | Python program that receives requests, checks rules and returns responses. |
| Route | An address plus HTTP method, such as `POST /files/upload`, handled by a function. |
| Database | Stores accounts, sessions and information about files, such as the owner. |
| File storage | Holds encrypted file contents. It is separate from the database. |
| Key store | Holds the secret needed to decrypt each file. It is separate from ciphertext. |
| Git | Records successive versions of source and documents. |
| GitHub | Hosts that history so the lecturer can inspect it. A repository is not a running application. |
| Branch | A line of work that can be reviewed before joining the main version. |
| Pull request | A comparison and discussion of proposed branch changes. |
| Virtual environment | A project-specific Python installation area for its libraries. |
| Trust boundary | A point where data crosses into a component with different permissions or trust. |

## Follow one upload

1. Alice's browser sends the file over HTTPS.
2. Flask checks that Alice has a valid session and a valid form token.
3. The server checks the filename, content and limits.
4. The server generates the file's identifier and encryption key.
5. It stores ciphertext privately and the key separately.
6. The database records that this file belongs to Alice.

When Bob guesses the identifier, the owner check must reject his request before
any decryption. Encrypting data does not automatically enforce who may use it.

## Three protections that solve different problems

**TLS** protects the network connection. The server receives the original upload
after terminating TLS.

**Password hashing** lets the server verify a login without storing a recoverable
copy of the login password. It is not how we preserve downloadable file contents.

**File encryption** lets the server recover the original bytes when an authorized
user downloads. It needs a secret key. In this project the server holds that key,
so a server compromise is outside the protection provided by encryption at rest.

## Questions to practise answering

- Why does hiding a delete button fail to provide authorization?
- Where is the plaintext present during upload and download?
- What information is visible if someone copies only the database?
- Why are file UUIDs useful if they do not grant permission?
- How does a session cookie differ from a password or file key?
- What does a CSRF token stop, and why is HTTPS insufficient for that attack?
- What does AES-GCM's authentication tag add to encryption?
- Why does deleting a filename from disk not prove physical erasure?
- Which features actually work in this first commit, and which are still design?

## First practical exercise

Follow the README and open `/health`. Find the Python function that produces the
JSON. Then run `python -m secure_file_manager.crypto_demo` and read `crypto.py`.
Identify the three inputs that bind ciphertext to its context: format version,
file identifier and owner identifier. Finally read the tests that change each
input and explain why decryption is rejected.

The goal for Checkpoint 1 is to understand and justify the plan. It is not to
memorize library names or present planned protections as already implemented.
