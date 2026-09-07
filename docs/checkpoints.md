# Semester checkpoints and evidence

Dates and assessment rules below are taken from the supplied *Project.pdf*,
sections 1, 2 and 3. They have not been independently checked against Moodle.

| Milestone | Assignment deadline | Contribution to course result |
| --- | --- | --- |
| Personal Git username submitted in Moodle | End of Week 2 | Mandatory |
| Checkpoint 1: threat model and architecture | 21 September 2026 | 5% |
| Checkpoint 2: core implementation | 26 October 2026 | 5% |
| Checkpoint 3: near-final application | 16 November 2026 | 5% |
| Final code/report ZIP in Moodle, repository updated | 30 November 2026, before presentation session | Required |
| In-class presentation | 30 November / 7 December 2026 | 15% |

The initial Moodle repository-link text file is separate from the final ZIP.
Checkpoints are verified in that week's lab; having files on GitHub alone does
not complete verification. Late work is not graded without an agreed extension.

## Checkpoint 1 review checklist

- [x] Define project scope and planned routes.
- [x] Draft architecture with browser, application, database, storage and trust boundaries.
- [x] Map threats to OWASP and the attack classes explicitly named in the assignment.
- [x] Justify framework, database, cryptographic library and development TLS approach.
- [x] Specify cookie flags, expiry and session fixation prevention.
- [x] Provide README, reproducible scaffold and prototype tests.
- [ ] Student reviews and explains the architecture in their own words.
- [ ] Student runs the foundation on their own laptop; this environment is not their laptop.
- [ ] Confirm whether ICS0022 reuse is mandatory and whether the planned deletion guarantee is sufficient.
- [ ] Confirm the OWASP edition used in lectures and align the mapping if needed.
- [ ] Review the branch, retain meaningful commits and bring the documents/history to the lab.

## Incremental work before Checkpoint 2

| Order | Small deliverable | Acceptance evidence |
| --- | --- | --- |
| 1 | Database and configuration | Users/file/session schema; independent private paths; missing secrets fail closed. |
| 2 | Registration, login and logout | Salted hashes; CSRF; cookie rotation; logout replay rejection; timeout tests. |
| 3 | Upload validation and encryption | Bounded parsing; no plaintext temp files; ciphertext/key separation; rollback on failure. |
| 4 | List, download and delete | Alice/Bob isolation on every operation; authenticated decryption; deletion cleanup. |
| 5 | Reproducible HTTPS demo | Certificate trust established, clean environment setup succeeds, core flows shown. |

Implement ownership checks, CSRF and basic input validation alongside the relevant
routes even though their fuller demonstration is assessed at Checkpoint 3.
Do not first create intentionally exposed account/file operations to add security later.

## Before Checkpoint 3

Finish the complete threat-register test set, harden error/logging behavior, review
dependencies and prepare a draft report. Capture failed attacks and successful
authorized controls. Record failure-injection results for storage/deletion.

The report must cover Introduction, Implementation, Security Analysis and
Conclusion. Follow the TalTech School of IT writing/formatting guidance specified
by the lecturer; the Markdown design notes are not yet the final formatted report.

## Evidence and commit discipline

Commit when a meaningful design, implementation or test change is made. Suggested
future messages describe real work, such as `Implement session rotation and logout
revocation` or `Add cross-user download regression tests`. Do not backdate commits
or fabricate progress. The checkpoint history is evidence of development over the
semester; the initial foundation is only one stage.

Maintain an evidence note for each checkpoint with the actual commit SHA, test
command, results and remaining issues. Review staged filenames before pushing;
the public repository must contain synthetic examples only.

## Final presentation preparation

The approximately ten-minute presentation must explain the objective, show live
features and security measures, describe key implementation choices, discuss
challenges, and support a question-and-answer session.

The final-presentation rubric allocates 40% to technical correctness/security
analysis, 25% to demo quality/reproducibility, 25% to the report/references and 10%
to delivery/answers. These are proportions of the final presentation assessment,
not additional percentage points on top of the course weighting.

Prepare a reliable sequence: login, upload, show stored ciphertext, recover the
file, attempt cross-user access, reject a CSRF attempt, delete and verify cleanup.
Use a short subset in the live slot and retain other tests as supporting evidence.
