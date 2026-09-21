# Secure File Manager

ICS0027 Web Application Security - Project 1, Checkpoint 1.

This repository contains the initial architecture and threat model for a secure web-based file manager. All features are planned.

Read the [short design document](docs/architecture.md).

## Scope and planned features

- Register, log in and log out.
- Upload, list, download and delete the user's own PDF and text files.
- Encrypt files on the server and check ownership before granting access.

File sharing and document previews are outside the initial scope.

## Planned routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | / | Welcome page |
| GET, POST | /register | Create an account |
| GET, POST | /login | Sign in |
| POST | /logout | End the session |
| GET | /files | List the user's files |
| POST | /files/upload | Upload a file |
| GET | /files/{file_id}/download | Download an owned file |
| POST | /files/{file_id}/delete | Delete an owned file |

## Running locally

The planned application will use Python 3.12, Flask and SQLite on the local computer, accessed through a browser over HTTPS.
