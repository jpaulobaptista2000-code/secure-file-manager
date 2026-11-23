# Final verification · 23 November 2026

| Environment | Result |
| --- | --- |
| Linux, Python 3.12 | All 75 tests passed with the dependencies from `requirements.txt`. |
| Student’s Windows PC, Python 3.13 | 75 tests ran: 73 passed, 2 skipped, no failures. This includes the check that security logs use the connection’s source address. |

The two Windows skips check Unix file permissions on the storage and log folders. They do not test Windows access control lists. The `datetime.utcnow()` warnings came from Flask-Session and did not fail the tests.

## What was checked

- `test_auth.py`: account creation, password verification, session expiry, rotation and logout.
- `test_uploads.py`: file validation, per-file encryption and owner-only lists.
- `test_file_actions.py`: original bytes on download, refusal to release damaged data, removal of the stored file and key, and retry after interrupted deletion.
- `test_checkpoint3.py`: form tokens, output escaping, bound database queries, ownership and private security logging.

**Windows browser checks (14 November):** a deletion with an invalid form token returned 400 and the original file still downloaded. The same download link in a second, signed-in account returned 404. Both denials appeared in the private log.

**Final HTTPS check (23 November):** starting the app from a clean extracted copy, a client that verified the local certificate could register, sign in, upload a TXT, download the same bytes, confirm deletion and sign out. These checks describe this local application; there was no public deployment.
