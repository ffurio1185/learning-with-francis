# Learning with Francis

A beginner-friendly learning application for SQL, Python, JavaScript and SAP.
Read a short lesson, practise with immediate feedback, take a quiz, and track your
understanding at your own pace. No account, registration or password is required.

**Published application:** Version 2.0 at `c8ba21f`, including the approved bilingual
English/German experience (L1–L5), connected progress tracker, subject icons, and
Welcome Cover Page/About enhancement. Local Render Free demonstration changes are
prepared for review; they have not been committed, pushed or deployed.
This candidate contains no background audio. The approved local development
repository is preserved separately.

See [Public release preparation](docs/PUBLIC-RELEASE.md), the
[exact publishing manifest](docs/PUBLISH-FILES.txt), and
[verification evidence](docs/RELEASE-VERIFICATION.md).

## What you can do

- Enter through the animated blue-and-white welcome cover, with its 4U watermark.
- Start a temporary visit with a name and a personalized greeting.
- Learn SQL SELECT/WHERE, Python variables/functions, JavaScript values/DOM/events,
  and introductory SAP ERP concepts.
- Answer ten multiple-choice practice questions per subject, one at a time, with
  immediate feedback, the correct answer and an explanation.
- Take a separate five-question quiz per subject. Scores, answer explanations and
  personalized feedback appear after submission. Practice and quiz retries are unlimited.
- Open My Progress to see all four subjects, including subjects with zero activity.
- Filter subjects by Still Learning, Needs Review or Completed.
- Review actual practice counts, correct exercise completions, quiz scores, and
  dated activity and status-change histories.
- Change a learning status in either direction. **Completed always requires your
  personal confirmation of understanding. Scores never complete a topic automatically.**
- Read timestamps in Europe/Berlin local time, including daylight saving time;
  database timestamps remain UTC.

The interface supports desktop/mobile layouts, keyboard navigation and visible
focus. The welcome animation respects reduced-motion preferences. Its ENTER link
and the learning forms remain usable without JavaScript; progress filtering and
inline confirmation hints are JavaScript enhancements, backed by Python validation.

## Technology

| Layer | Tools |
| --- | --- |
| Application and grading | Python, Flask and Jinja templates |
| Storage | SQLite, parameterized SQL and transactions |
| Browser | HTML, CSS and plain JavaScript |
| Verification | Python unittest, SQLite checks and optional Chromium/Playwright checks |

The approved snapshot uses `Flask==3.1.3`; L1 adds `Flask-Babel==4.0.0`. Python 3.14.4 on Ubuntu/WSL is the
verified development environment. The system must provide timezone data for
`Europe/Berlin`. Browser verification tools are optional and separate from runtime
requirements.

## Run locally

From this project's root directory on Linux/WSL, create a **new** virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Initialize a new local Version 2 database and check it:

```sh
.venv/bin/python -B -m flask --app learning_with_francis:create_app init-db
.venv/bin/python -B -m flask --app learning_with_francis:create_app check-db
```

Initialization creates `instance/learning_with_francis.db` from the committed
schema and migrations, producing schema version 3. It adds four subjects and four
topic definitions, with **no visitors, answers, scores or activity history**.
Starting a visit subsequently creates that visit's four initial Still Learning
status records. Those initial entries are not practice or quiz activity.

The factory creates a private random `instance/session-signing-key` on first
startup and reuses it. Keep this key private and stable. The database and key are
local runtime files and must never be committed or distributed.

Start the local development server:

```sh
.venv/bin/python -B -m flask --app learning_with_francis:create_app run --host 127.0.0.1 --port 5008
```

Open <http://127.0.0.1:5008/> for the cover, then choose **ENTER** to reach `/learn/`.
Enter your name, choose a subject, and use **My Progress** to review your activity.
Use another available port if 5008 is already in use. This command is for local
development, not a public production server.

**Important:** root `app.py` is the preserved Version 1 application. Use the
`learning_with_francis:create_app` entry point above for Version 2.

## Free public demonstration

The prepared Render configuration uses **Free** compute in Frankfurt, with no
persistent disk or additional database service. SQLite lives in a private runtime
directory outside the source tree. Storage can disappear when the instance sleeps,
restarts or is redeployed. A bilingual notice explains this before name entry and
on learning/progress pages. Do not rely on the demonstration to retain results.
The original local setup above does not enable this hosting-specific notice.

See [the Free setup and launch requirements](docs/PUBLIC-RELEASE.md).

## Temporary visits and privacy

A name is a greeting label, never an identifier. Every new visit receives a random
ID and fresh progress. Identical names do not recover or share earlier results.
The signed session cookie selects the current visit; progress and result queries
are restricted to that visit. Submitted scores are ignored: Python calculates
scores from its own answer key. Form protection and duplicate-submission checks
prevent invalid submissions and refreshes from inventing extra attempts.

Tabs in the same browser profile share a visit. Refreshing or reopening a browser
may resume its cookie, so closing the browser is **not** an End Visit action.
Use **End Visit** before handing the browser to someone else. **Start New Visit**
ends the active identity and returns to name entry for a fresh visit. Separate
browser profiles can be used to compare independent visitors.

Names, answers, scores and dates are retained in the local database after a visit
ends, while that ended visit loses browser access. There is no account recovery,
cross-device progress or automatic deletion feature. No original learner records,
preview databases, backups or private signing keys are included in this snapshot.

## Project layout

```text
learning_with_francis/     Version 2 Flask factory, handlers, content and templates
  schema.sql              Curriculum schema and four subject/topic definitions
  migrations/             Visitor and activity schema migrations
static/                   Shared styles, scripts, cover assets and subject icons
tests/                    Python/SQLite checks and optional browser drivers
  fixtures/               Schema-only Version 1 test fixture
app.py, database.py        Preserved Version 1 application and database functions
templates/topics.html     Preserved Version 1 page
PROJECT-PLAN.md           Public milestone history, approvals and current scope
AGENTS.md, .agents/       Current project-specific learning guidance
requirements.txt          Application dependencies
babel.cfg                 Translation extraction configuration
```

The application runs independently of its original development repository and
external teaching materials. No earlier database, browser session or retained
preview is required. The [implementation notes](learning_with_francis/README.md)
explain the internals and content references; this root README is the independent
setup guide. [PROJECT-PLAN.md](PROJECT-PLAN.md) preserves public milestone approvals
and verification results without private operational logs.

## Verification

Run the Python and SQLite regression suite:

```sh
.venv/bin/python -B -W error::ResourceWarning -m unittest discover -s tests -v
```

The original published source had 125 tests; bilingual/content checks and later
cover verification brought the application suite to 194. This Free demonstration
candidate adds 16 production-boundary and five Free-storage/notice tests, for
**215 tests**. They cover both versions, database setup,
transactions, grading, repeated practice, visitor isolation, confirmation
protection, saved history, timezone display and cover routing. Tests generate
schema 3 data and signing keys in disposable `/tmp` directories. Version 1 tests
create their own database from `tests/fixtures/version1-schema.sql`; no original
database is required.

The L1 driver `tests/browser_language.py` adds six language/accessibility groups.
L2 adds eight groups in `tests/browser_interface_language.py` for native language
forms, drafts, German progress controls, validation and isolation. L3 adds six
SQL-language groups in `tests/browser_sql_language.py`. L4 adds 14 groups in
`tests/browser_subject_language.py` for the remaining content (60 groups total).

Optional existing real-browser drivers are `tests/browser_phase2_progress.py` (19 groups)
and `tests/browser_welcome_cover.py` (seven groups). They require separately
installed Playwright and Chromium, start their own loopback server, and remove
their disposable test databases. With those tools available, run:

```sh
python -B tests/browser_phase2_progress.py --report-dir /tmp/francis-progress-checks
python -B tests/browser_welcome_cover.py --report-dir /tmp/francis-cover-checks
python -B tests/browser_language.py --report-dir /tmp/francis-language-checks
python -B tests/browser_interface_language.py --report-dir /tmp/francis-interface-checks
python -B tests/browser_sql_language.py --report-dir /tmp/francis-sql-language-checks
python -B tests/browser_subject_language.py --report-dir /tmp/francis-subject-language-checks
```

Use the Python environment containing Flask and Playwright for these optional
commands. Reports and screenshots should stay outside the publishable source.

## English/German support — L1 to L4

Choose **English** (US flag) or **Deutsch** (German flag) on the cover or application
pages. English is the default for a new browser cookie; browser headers do not
change it automatically. The protected language POST returns to the same interface
page. The cover's animation is unchanged. All four subjects now support both
languages: lesson prose, ten practice questions each, five quiz questions each,
explanations, topic titles and personalized feedback. Code examples and technical
identifiers retain their original syntax. Pages declare their content language.

The language code is kept in the signed session, separately from visit identity.
It survives navigation, End Visit and Start New Visit. Visit changes still clear
identity and activity tokens. Tabs share a cookie; closing a browser does not
reliably end a visit or clear a restored language preference.

Language buttons on the name, practice and quiz forms use native HTML form
submission, including without JavaScript. They bypass required-answer checks for
that display change only. Small, allowed draft fields are carried through a
one-time signed-session draft and restored on the matching page for the same visit.
Drafts may briefly contain the entered name or selected option IDs; signed cookies
are not encrypted. No scores, results or understanding are saved by a language
change. A pending quiz keeps its submission token; a practice round keeps its
position. Normal submission still runs all existing Python validation and grading.
End/New Visit drops drafts. Confirmation boxes always start unchecked.

Return destinations are signed, visit-bound, time-limited and restricted to local
application GET routes. CSRF protection, escaping, HttpOnly/SameSite cookies and
no-store pages remain. Future HTTPS deployment must enable Secure cookies.
Browser-native messages with JavaScript disabled follow the browser's own locale;
the application's Python errors are translated. With JavaScript, required-input
and confirmation hints use the selected interface language.

Status labels translate to „Noch am Lernen“, „Wiederholung nötig“ and „Abgeschlossen“.
Database values and form identifiers remain the original English codes; switching
languages never writes progress. UTC storage is unchanged. German timestamps show
MEZ/MESZ, with the same Europe/Berlin rules and machine-readable offsets.

Flask-Babel uses English source/fallback text and German editable/compiled catalogs
in `learning_with_francis/translations/de/LC_MESSAGES/`. Both `.po` and `.mo` are
supplied so a clean checkout works. See
[translation maintenance](learning_with_francis/translations/README.md).

### Learning content and saved results (L3–L4)

English remains the canonical source for all four subjects. `N_` marks wording for translation but
returns the original English string. `sql_display.py` creates translated view
copies; Python still grades with the original IDs and answer keys. Saved-answer
translation is scoped by topic as well as exact wording. SQL commands,
table/column names, quoted values and sample rows are unchanged. Quiz keys and
explanations remain hidden until submission; practice reveals them immediately
after checking an answer.

New attempts in either language retain canonical English answer snapshots in
SQLite. Exact known saved snapshots can be displayed in either language without
rewriting them. Earlier or unknown wording stays in its original language with a
notice rather than being guessed or replaced. Display changes do not alter scores,
dates, counts, understanding or historical records. Existing content versions and
submission tokens remain compatible. No database migration is needed.

## Version 1 compatibility and project history

Version 1.0 introduced the personal learning tracker. Version 2 adds visitor-owned
learning, practice, quizzes and the connected tracker (approved P2.5), followed by
the separately approved Welcome Cover Page. Both implementations and the complete
regression suite are preserved here. Their databases are separate and incompatible;
Version 2 does not read, import or change Version 1 records. Version 1 requires its
own database to run manually; the tests construct one automatically.

The approved source milestones are `70ca080` (Version 1), `1556cc9` (P2.5), and
`fe77b84` (Welcome Cover Page). These identify approved snapshots in the original
development history, which is not copied into this independent repository. P2.6
and future public deployment work remain separate from the approved snapshot.

## Scope and deployment status

This is a small learning project. It does not execute learner-written Python,
JavaScript or SQL, connect to a real SAP system, provide accounts, or promise
cross-device recovery. SQL tables shown in lessons are educational examples,
not recorded visitor progress.

Local production preparation is available through `wsgi:app`, Gunicorn and
`render.yaml`. Live Render deployment has **not** occurred. The supported start
script initialises a fresh schema-3 database under a private persistent mount and
validates existing databases without resetting or upgrading them. Production needs
an external stable secret and HTTPS; the approved 12-hour session behavior remains.

Before deployment, approve the real Impressum/privacy information, data-retention
and backup arrangements, and actual hosting costs. No original or preview database
should be uploaded. Follow [the release procedure](docs/PUBLIC-RELEASE.md); the
configuration file does not itself buy services or authorise deployment.

## Credits and third-party assets

Created by Francis Furio as a Python, SQL and JavaScript learning project.
Lessons and questions are independently prepared; the package README records
content references. External course materials are not included or required.
Subject icons retain their existing attribution and licence notices under
`static/subject-icons/`. Their use identifies learning subjects and does not imply
endorsement. A project-level licence has not yet been selected; do not assume the
third-party icon licences apply to the entire application.
