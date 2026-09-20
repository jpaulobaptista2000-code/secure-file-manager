# Secure File Manager

**ICS0027 Web Application Security | Project 1 | Checkpoint 1: architecture**

A planned web application where each user can upload, list, download and delete
their own encrypted files. The server encrypts file contents; HTTPS protects
communication between the browser and server.

## Current stage

This version contains **architecture and security design only**. The application,
installation scripts and tests are not included. All functionality below is planned.

## Presentation documents

1. [Architecture and security design](docs/architecture.md): component diagram,
   trust boundaries, technology choices, file lifecycle, encryption,
   authentication, sessions and TLS plan.
2. [Threat model](docs/threat-model.md): relevant attacks, proposed mitigations
   and the evidence to collect when the application is implemented.

## Scope

- Registration, login and logout.
- Upload, list, download and delete the authenticated user's own files.
- Server-side encryption with separate key storage.
- Server-side input validation, ownership checks and CSRF protection.

The proposed upload limits are TXT/PDF files of 1 byte to 5 MiB, with a 50 MiB
quota per user. Sharing, document previews and public hosting are outside the
initial scope. These limits are project design choices.

## Planned routes

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/` | Welcome page |
| GET | `/health` | Application health |
| GET, POST | `/register` | Create an account |
| GET, POST | `/login` | Authenticate |
| POST | `/logout` | End the session |
| GET | `/files` | List the current user's files |
| POST | `/files/upload` | Validate and encrypt a file |
| GET | `/files/<uuid>/download` | Check ownership, decrypt and download |
| POST | `/files/<uuid>/delete` | Check ownership and delete |

## Local setup plan

There is no runnable application in this architecture-only version. The planned
environment is Python 3.12, Flask and SQLite on the local computer, accessed
through a browser over HTTPS. Installation and run commands will be added with
the implementation. No public deployment is required for this design.

The academic requirements are from the lecturer's *Project.pdf*, sections 1-3,
2026/2027 edition. The lecturer's materials are not redistributed here.
