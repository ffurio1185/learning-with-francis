# Temporary visit retention — Option B

Implementation is locally verified and approved by Francis, with the accepted
252 Python/SQLite tests and 83 browser groups. Legal notices have subsequently
been integrated locally under separate approval; see docs/PRIVACY-REVIEW.md.
No commit, push, merge or deployment is authorised by these approvals.

## Active visits and deletion

The signed session selects a random visit ID; a nickname is never an ownership
key. End Visit deletes learning answers, attempts/scores, status history,
progress/confirmation timestamps and the visitor row, children first within one
SQLite transaction. Only that visit ID is used. Start New Visit does the same
before returning to name entry. A direct valid name submission replacing an active
visit deletes the old identity and creates the new visit/progress/history in one
transaction. Invalid forms do not delete an active visit. Failure rolls back the
whole operation, and the browser session is cleared only after a successful commit.
The chosen display language survives; old identity, CSRF and answer drafts do not.
Shared subjects/topics/questions and the database file itself remain in place.

## Inactivity

Schema 4 adds an indexed UTC last_activity_at field. Fresh visits start with the
server time. Default VISIT_IDLE_SECONDS is 1800; production reads the positive
whole-number LWF_VISIT_IDLE_SECONDS environment value (maximum one year).
The 30-minute interval is an **inactivity limit**, not a maximum learning duration.

Startup cleans ended/expired visits in an existing supported runtime database.
Before home/learning/progress/visit requests, cleanup deletes records whose last
activity is at or before the cutoff. Expiry is checked before renewing activity.
After a successful learning response (2xx/3xx), the still-active visitor's timestamp
and cookie signature are renewed. Lessons, practice/quiz forms/results, My Progress
and the learning home qualify. Invalid answers, CSRF failures, foreign results and
unknown routes do not. Cover, privacy, language-preference POSTs, static assets and
health checks do not; a successful learning GET following a language change does.
Reading a page, selecting an answer or using client-side filters without a server
request does not reset inactivity. No heartbeat, scheduler or background worker
is added. Cookies keep their existing 12-hour signature-age window, refreshed on
successful learning requests so that continuous activity can continue past 12 hours.
An open signed activity form still has its independent existing 12-hour token limit.

Writes recheck visit access inside their existing transactions. Activity renewal
is serialized and cannot revive deleted/expired data or move the timestamp
backwards. An old cookie, result URL or duplicate POST cannot recreate a visit.
Private responses retain no-store headers. Browser history may retain already
seen information outside the application's control; server records cannot be
recovered by Back navigation. The application cannot erase screenshots, provider
logs, third-party backups or all browser-managed storage.

## Storage, startup and protection

init-db/production prepare create fresh schema 4 only when the selected file is
absent. Existing schema 3 is refused unchanged; there is no implicit upgrade or
reset. The explicit upgrade utility has a new transactional migration and backup
suffix, tested only with newly generated disposable legacy data. Do not run it
against original/development visitor databases. Starting the new application on
an upgraded file applies the new deletion policy, including ended legacy visits.
SQLite foreign_keys and secure_delete are enabled on runtime connections. This
reduces ordinary deleted-content remnants in SQLite pages, but is **not** a promise
of secure erasure of hosting storage, snapshots, logs or external copies.

Render Free can sleep or discard temporary files. With no executing process or
qualifying request there is no exact-minute deletion guarantee: expired records
may remain until startup or a subsequent learning/visit request. Expired identities
are still refused before renewal. A normal restart preserves only still-active
visits when files remain; instance replacement can lose all progress earlier.
A closed/reopened browser may restore the same visit before it expires. Use
End Visit before handing the browser to another learner. Progress recovery after
ending/expiry is intentionally unavailable. No personal production records are
backed up by this feature.

## Verification

See PROJECT-PLAN.md for the final observed test totals and approval state.
`python -B -m unittest discover -s tests -v` includes focused clock-controlled
retention tests as well as Version 1 and four-subject bilingual regressions.
`tests/browser_temporary_visits.py --report-dir /tmp/<report-directory>` adds real
Chromium checks using a disposable database and loopback server. External
Playwright/Chromium are test tools, not application dependencies.
All saved data checks use disposable files. Semantic snapshots compare schema and
all learning records except the intentionally renewed last_activity_at field;
focused tests separately verify exactly which requests can change that field.
Legal documents must be reviewed against this behavior after technical approval.
