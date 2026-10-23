# Learning with Francis — implementation notes

See the [root README](../README.md) for features, independent installation,
startup and testing. This document explains the approved implementation; it does
not require another repository, original databases or retained preview resources.

## Entry points and templates

`create_app()` in `__init__.py` creates Version 2. `/` always shows the separate
welcome cover; `/learn/` is the existing `index` endpoint for name entry or the
active visitor's home page. ENTER preserves the active visit rather than creating
or ending one. `cover.html`, `static/cover.css` and `static/cover.js` provide the
1.2-second entrance with normal-link, keyboard, reduced-motion and Back-navigation
support. Root `app.py` remains the separate Version 1 entry point.

The shared learning handlers select SQL, Python, JavaScript or SAP content per
request. Learning templates reuse the same navigation, visit controls and result
format. Local subject icons use decorative empty alt text beside visible subject
names. `static/style.css` and `static/topics.js` are shared with the preserved
tracker; `static/phase2.css` keeps navigation links blue, including visited links,
without changing progress or removing keyboard focus.

## Reproducible schema 4 setup

`schema.sql` defines four subjects and their initial topics. The migrations add
visitor/progress/history tables, learning-attempt/answer tables, and an indexed
UTC last_activity_at timestamp for temporary visits. `init-db`
creates a missing database once; repeated setup validates a supported database
without resetting it. Request handling does not silently initialize or upgrade
files. `check-db` verifies the application marker, schema version and catalogue.

New setup produces schema 4 with no visits or activity. The explicit `upgrade-db`
command exists for supported older Phase 2 schemas: it creates a non-overwritten
backup, preserves earlier fields and rolls back on failure. **Do not run upgrades
on protected/original databases.** Starting this application on a newly upgraded
disposable database deletes ended/inactive visits under the new retention policy.
No existing private
database is distributed with this source. Version 1 and unrelated databases are
rejected rather than overwritten. Foreign keys are enabled on each connection;
connections are local to a request or command and are closed afterwards.

## Temporary visit boundary

`visitors.py` validates names and creates a random visit ID. Starting a visit
saves its name, identity, four Still Learning progress rows and four initial
history rows atomically. Initial status history records a starting point, not
practice activity. Matching names never retrieve earlier identities or progress.

The signed HttpOnly/SameSite session cookie carries a visit ID, not progress or
the greeting name. `security.py` stores a stable private signing key outside source
control and binds forms to a session with CSRF tokens that rotate at visit changes.
The cookie has a 12-hour signature-age limit; browser restoration may retain it.
End Visit deletes the visit and all of its learning records atomically.
Start New Visit performs the same deletion before name entry; direct replacement
also deletes the previous identity within the new-visit transaction. A configurable
30-minute inactivity check runs before learning requests and at app startup;
successful learning requests renew last_activity_at and the cookie signature.
Public cover/privacy/static/health and rejected requests do not renew learning
activity. Closing a browser is not a reliable deletion event; sleeping Render
instances perform cleanup only when execution resumes. See
[the retention specification](../docs/TEMPORARY-VISITS.md).
No account recovery or visit-selection screen is provided.

Private HTML uses no-store cache headers. All learning and progress queries use
the active identity from the verified session; posted/query-string owner IDs are
not used to select another visitor's records. Ended or different visits cannot
read or modify results. Two tabs in one browser profile share a visit; separate
profiles provide independent visitors. Public HTTPS configuration remains future
work; the current cookie Secure flag is set for local HTTP development.

## Lessons, practice and quizzes

`sql_content.py` contains the SQL lesson question sets; `subjects.py` provides the
other three subjects and the shared catalogue. Questions have stable IDs, choices,
server-side answer keys and explanations. Learners do not execute submitted code.
SQL examples are fictional educational tables, not stored visitor activity.

Each subject has ten practice questions, shown one at a time. After checking an
answer, the page immediately shows correctness, the correct answer and an
explanation. Next Question advances through the round; Finish Practice after the
tenth response shows completion and Start Practicing Again. Incorrect responses
do not prevent a visitor from finishing a practice round. A correctly answered
practice entry counts as a completed exercise; an incorrect one still counts as
practice. Repeating practice creates separate dated activity, with no attempt limit.

Each quiz contains five questions and reveals answers only after the whole form
is submitted. Python validates exactly one listed choice per question and computes
the score itself. Browser-supplied scores, totals and owner IDs are ignored.
Feedback uses the visitor's name: encourage review for 0-2/5, congratulate a pass
for 3-4/5 and celebrate a perfect 5/5. Try Again permits unlimited quiz attempts.
No result supplies confirmation of understanding or changes topic status.

## Saved activity and duplicate protection

Scores and individual answer snapshots save atomically in `learning_attempts`
and `learning_answers`. Snapshot data preserves prompts, choices, selected/correct
options and explanations. Results are restricted to the owning visit and subject.
Successful submissions redirect with HTTP 303; refreshing the result saves nothing.

Signed quiz tokens bind a random submission ID to the visit, activity, content
version and subject, with a 12-hour expiry. Practice binds a random round ID and
question position. A unique database submission ID and transaction make repeated
or simultaneous identical submissions reuse one result; conflicting reuse returns
HTTP 409. Invalid, expired or cross-visit/subject tokens save nothing. SQLite finds
the next unanswered practice question, so refreshing does not skip questions or
invent activity. Earlier single-question results retain their saved snapshots.

## Connected progress and history

`progress.py` builds My Progress for every subject, including those with no
activity. A LEFT JOIN retains zero-activity subjects; GROUP BY gives one topic
summary and COUNT counts attempts directly rather than joining quiz-answer rows.
A five-answer quiz therefore counts as one attempt. Correct practice retries are
separate completed exercise entries. Summary totals are independent of filtering.

Dated activity links open owned results; status history records initial states
and subsequent changes. `static/topics.js` filters the saved status and warns
before unconfirmed completion, without checking the checkbox automatically.
Python independently requires the exact single submitted value `yes` for
Completed, validates CSRF/ownership/status, and saves status/history together.
Moving back clears the current confirmation while retaining earlier history.
Repeating an unchanged status does not invent a new event. Quizzes and exercises
never write an understanding status or confirm it on the visitor's behalf.

`display_time.py` interprets offset-free SQLite timestamps as UTC, then uses
`zoneinfo` with Europe/Berlin for display. `_time.html` renders the German-local
text and an ISO datetime with the correct CET/CEST offset. This applies to visit
starts, activity, results, confirmations and status history; stored UTC dates
and their ordering are unchanged.

## Verification and approved state

Version 1 regressions build synthetic data from the schema-only fixture at
`tests/fixtures/version1-schema.sql`; no original database is needed. Setup,
migration, session isolation, same-name visitors, grading, retries, duplicate and
concurrent submissions, snapshots, rollback, confirmations, timezone transitions
and restart persistence are covered by Python/SQLite tests. The approved standalone
source passed all 125 tests and 26 real-browser groups (19 learning/tracker plus
seven cover groups), followed by the recorded personal approvals.

The browser drivers create their own disposable databases and loopback servers.
Browser tools are optional verification dependencies outside application runtime
requirements. The root README documents commands and the project plan preserves
milestone evidence. P2.1-P2.5 and the separate cover are verified, approved and
closed. P2.6 and Render deployment remain unstarted. No database migration or
production configuration is introduced by this documentation preparation.

## Content references and attribution

Lessons, questions and explanations were independently prepared in simple English.
The original learning process consulted beginner material about Python variables
and functions and JavaScript values, DOM and events. Those external teaching
materials are not bundled or needed to run the application. SAP concepts and
simplified business scenarios were checked against these public references:

- [SAP: What is ERP?](https://www.sap.com/australia/products/erp/what-is-erp.html)
- [SAP Learning: procurement and master data](https://learning.sap.com/courses/exploring-end-to-end-business-processes-in-sap/identifying-the-areas-in-procurement_f5d58dec-c7fa-4a42-92aa-546934e4d244)
- [SAP Learning: master and transactional data](https://learning.sap.com/courses/sap-ariba-integration-sap-ariba-integration-points/understanding-sap-ariba-procurement-master-data)
- [SAP Learning: purchasing and reconciliation](https://learning.sap.com/courses/configuring-additional-settings-in-financial-accounting-in-sap-s-4hana/understanding-purchasing-mm-integration)

The SAP lesson is a conceptual introduction, not a live SAP connection or a fixed
workflow for every configuration. The Python and JavaScript examples are code to
read; visitors do not submit or execute arbitrary code.

Subject logos and their notices are retained in
[the subject-icon documentation](../static/subject-icons/README.md). Francis Furio
is the project author; third-party notices are not replaced by a project-wide
licence. Runtime credentials and saved visitor data are never documentation assets.


## Bilingual development (L1–L4)

The independent feature branch adds Flask-Babel and English/German interfaces;
the approved published source remains on `main`. L1–L3 have personal approval.
L4 extends the SQL approach to Python, JavaScript and SAP lessons, practice, quiz
questions, explanations and feedback, and awaits personal review. See the root
README and translation maintenance notes.

Language changes preserve visit identity and saved activity. The signed cookie
can carry a small one-time name/answer draft during a native language switch; it
is not encrypted and contains no scores or answer keys. The draft is consumed on
the matching page and discarded at visit boundaries. Existing owner checks,
transactions, grading and explicit completion confirmation remain in force.


L3/L4 share view helpers and extraction markers without changing canonical question
objects, grading, executable examples, content-version IDs or saved snapshots.
Lookups include the topic, because different subjects reuse question IDs. Known
snapshots translate only at render time. Unknown historical wording retains its
original text. No migrations, accounts or new activity features are introduced.
