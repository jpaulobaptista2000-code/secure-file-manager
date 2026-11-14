# Checkpoint 3: Windows browser demonstration summary

**Environment:** student's Windows PC, Chrome, local HTTPS application

**Branch:** `checkpoint-3`

**Tested application implementation:** `4ef254099c14f778555181ce17b16885d387fd2c`

## Evidence source

The student performed the browser actions and confirmed the outcomes in the
project conversation. A screenshot showed a disposable text file's deletion
confirmation page alongside the running local HTTPS server. The student also
inspected the private security log and supplied the relevant output for review.

This public note records only the test procedure, application event types and
observed outcomes. Original runtime entries, exact event timestamps, account IDs,
request IDs and file identifiers are not included. Error-page outcomes were
reported in text; screenshots of the rejection pages and full HTTP captures were
not supplied.

## 1. Invalid CSRF token rejected; file preserved

The student uploaded a disposable TXT, opened its deletion confirmation page,
and changed the deletion form's hidden `csrf_token` value to `forged` using
browser developer tools. Submitting the form displayed **Please reopen the form**.
The student then confirmed that the file remained in **My files**, could still
be downloaded, and retained its original sentence.

Inspection of the private security log confirmed a `csrf_rejected` event for
the deletion POST with HTTP status **400**. The outcome is consistent with
rejecting the invalid token before file deletion.

## 2. Another account's direct download denied

The student copied the owner's Download link, opened a separate private browser
window and signed in with a different account. Opening the copied link produced
**File not found**.

Inspection of the private security log confirmed a `file_access_denied` event
for the download GET with HTTP status **404**. This demonstrates that possessing
the direct URL did not give the second account permission to download the file.

## 3. Security events available for inspection

In a second PowerShell window, the student read the last 100 lines of the
private security log and filtered for `csrf_rejected` and `file_access_denied`.
Both expected event types were present with the rejection statuses above.
The complete runtime log remains outside Git and is not served by a web route.

These manual checks establish the observed forged-token rejection, preserved
file, cross-account download denial and availability of the corresponding
security events. They do not constitute a complete penetration test, a Windows
ACL audit or browser execution tests for every XSS payload. The broader automated
tests are documented separately in the security test matrix.
