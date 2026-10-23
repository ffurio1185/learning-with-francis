# Local public-release verification

Checked on 23 October 2026. This is technical release-candidate evidence, not a
completed deployment or a legal/security certification.

## Earlier published c8ba21f preparation results

- Fresh Python 3.14.4 virtual environment installed Flask 3.1.3, Flask-Babel 4.0.0
  and Gunicorn 26.2.0 from PyPI. `pip check` found no broken dependencies.
  Gunicorn 26.2.2 was mentioned by upstream documentation but unavailable from
  PyPI during preparation; the available 26.2.0 release was installed and tested.
- **210 Python/SQLite tests passed**, with ResourceWarning treated as an error:
  the 194 approved application tests plus 16 focused production-boundary tests.
  Coverage includes Version 1 compatibility, all subjects and score bands,
  visitor isolation, duplicate submissions, status confirmation/reversal,
  German local timestamps, bilingual content and persisted results.
- **60 existing Chromium browser groups passed**: cover 7, language 6, interface 8,
  SQL language 6, other-subject language 14 and progress 19. Checks include mobile
  and enlarged text, keyboard interaction, reduced motion and no JavaScript.
  One timing-sensitive cover assertion failed under parallel test load; it passed
  when rerun alone without changing the approved cover code or test threshold.
- **6 additional production-browser groups passed**, using the actual startup
  script and Gunicorn on loopback: fresh setup/readiness; bilingual silent cover
  and secure cookies; four-subject practice/quiz flows; production CSP and personal
  confirmation; restart persistence with the same signing key; and a second
  same-name visitor with no activity and no-JavaScript confirmation protection.
  Final browser reports contain no unexpected page/server errors.
- Production checks enforce missing-secret/data/host failures; HTTPS-safe cookie
  settings; unchanged 12-hour session lifetime; revoked-visit replay rejection;
  eight concurrent distinct visits; consistent SQLite backup/restore; integrity
  and foreign-key checks; zero-activity setup; and non-destructive startup.
- Host validation initially conflicted with the original linked error template.
  A production-only generic 400 handler resolved the problem without changing
  existing application functions. Gunicorn's shutdown was bounded to 10 seconds
  and its unused control socket disabled after restart testing.
- Direct self-signed Gunicorn TLS in the first test harness caused connection
  stalls. Final browser tests use Render's actual HTTP-backend topology on trusted
  localhost, where Chromium permits Secure cookies. HTTPS cookie behavior is also
  checked with Flask's HTTPS test client. Render's real public TLS/proxy behavior
  remains a post-deployment check; it is not claimed as already verified.
- `node --check` passed for all four JavaScript files; `sh -n render-start.sh`
  passed. `render.yaml` parsed correctly and passed validation against Render's
  official JSON Schema. No authenticated Render API/resource operation occurred.

All functional tests use separate disposable SQLite databases. Their temporary
directories are removed by the tests. A distinct locally prepared fresh database
contains only four subjects/four topics and zero visits, attempts, answers, progress
or history rows. It is private verification data, not part of the publishing tree.

## Source and privacy verification

The candidate imports approved files, not development Git history. Its only prior
commit is the already published `dbeae6f`; the approved feature-branch commits and
audio commit are absent. Full object/history and prospective-file checks passed: all local Git blobs were
scanned, the omitted development commits were absent, and no recording/private
SQLite object was found. The exact publishing manifest contains 89 files. Repeat
these checks before any final commit/push. No audio, private SQLite databases,
visitor records, backups, real credentials or signing keys belong in the manifest.
Synthetic test keys, educational examples and the blank `.env.example` are not
production credentials or real visitor records.

SHA-256 comparisons confirmed all 153 protected source/classroom files unchanged,
including the original databases/backups and the existing uncommitted source-plan
update. The existing feature branch, its approved music implementation and local
Git configuration are preserved. Version 1 files and approved application code
match the reviewed source snapshot. Only the new production wrapper changes the
hosting boundary; it does not change grading, sessions, content or progress rules.

## Remaining live-release prerequisites

- Approved real operator/contact information and accessible Impressum/privacy
  notices; honest retention/rights-request information matching the application.
- Approval of the actual paid Render resources and backup arrangements, including
  backup retention and a workable operational recovery procedure.
- Approval of the exact release commit/push, then a separate deployment approval.
- Live HTTPS, provider host/health-check behavior, persistent-disk redeploy and
  operational backup verification, followed by Francis's personal review.

Automated browser tests use Chromium/emulated devices, not a formal screen-reader
or physical-device accessibility audit. Original records remain untouched. P2.6
stays open. Nothing has been committed, pushed, purchased or deployed by this work.


## Render Free adjustment verification — 23 October 2026

This later section supersedes the earlier paid-resource deployment prerequisites.
The published `c8ba21f` history remains unchanged; these are uncommitted local
changes for a Free demonstration, pending owner approval.

- **215 Python/SQLite tests passed**, with ResourceWarning treated as an error:
  the previous 210 plus five Free-demo checks. English/German notices are checked
  before name collection and across lessons/practice/quizzes/results/progress.
  Notices/language selection do not change stored activity. Invalid demo settings
  fail before storage creation. The original local factory does not enable the
  hosting-specific notice by default.
- **68 browser groups passed**: all 60 existing cover/language/interface/learning/
  progress groups plus eight actual-Gunicorn groups. The latter exercise original
  production security/scoring/confirmation and add bilingual notice layouts at
  320/375/1440px, enlarged text, and simulated storage replacement. No unexpected
  page/server errors occurred. A first new unit-test attempt assumed the default
  cookie name; using the configured name corrected the test without application
  changes. No original application regression required a fix.
- Real process restart with remaining storage preserves records and session.
  Switching to a fresh disposable instance directory creates metadata-only schema
  3; stale cookies return safely to name entry, and a same-name new visit has zero
  attempts and four Still Learning subjects. Old test records in the previous
  directory remain unchanged until automatic disposable-test cleanup.
- All test-owned database directories were removed. New synthetic activity is
  never copied into the release. SQLite integrity/foreign keys, dependency checks,
  shell/JavaScript syntax, German catalog compilation and the official Render JSON
  Schema passed. Explicit resource assertions require one Free Frankfurt service,
  no disk/additional services, demo mode, ephemeral data path and automatic deploys
  off. No Render account/resource API was called.
- The reviewed publishing manifest now lists **91 files**; its only new source
  files are the shared notice partial and focused Free-demo unit tests. Scans
  exclude private SQLite/audio/backups/secrets. Protected source/classroom hashes
  are checked before and after saving; Version 1 and approved learning logic are
  byte-for-byte unchanged. No Git refs, commits or existing staging are changed.

The notice is useful information, not a substitute for real Impressum/privacy
pages. Those details and separately approved push/deployment remain outstanding.
No paid backup or guaranteed recovery is required/promised for this disposable
demonstration. Render's real cold start, quotas, public TLS and loss of filesystem
can only be checked after deployment approval. P2.6 is not closed by these tests.
