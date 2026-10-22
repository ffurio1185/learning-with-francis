# Learning with Francis — project plan and approval history

**Author:** Francis Furio

**Current application:** approved Version 2.0 learning functionality, connected
progress tracker and Welcome Cover Page.

**Current task:** prepare the independent project for its first public commit.
Git initialization and local identity/remote configuration are authorised;
committing, pushing and deployment still require separate approval.

This public summary preserves the agreed goals, responsibilities, completed
milestones, verification results and accepted limitations. Temporary preview
locations, individual visit activity and internal troubleshooting logs are omitted.
It records earlier approvals without claiming that old checks were rerun for a
documentation change. [README.md](README.md) is the current local setup guide.

## Purpose and learning priorities

The project began as a small Personal Task Manager, became a Personal Learning
Progress Tracker in Version 1.0, and grew into Learning with Francis in Version 2.0.
The original tracker database work remains the foundation, not a separate feature
to rebuild. The independent application uses Python, Flask, SQLite, HTML, CSS and
plain JavaScript.

- **Python:** write small functions, open/close SQLite connections, read and save
  data, handle Flask requests, validate input and use transactions.
- **SQL:** design related tables and keys, practise JOINs, and calculate accurate
  counts with GROUP BY and COUNT, including topics with zero activity.
- **JavaScript:** select DOM elements, handle events, filter saved statuses and
  provide confirmation feedback without replacing Python validation.
- No separate learning-priorities file has been identified; these are the agreed priorities.

The initial Version 1 estimate was **10–15 learning hours**. The Phase 2 estimate
was **12–20 development hours**, with extra time for guided learning. These were
planning estimates, not a record of actual elapsed time.

## Learning responsibilities

Francis writes the Python, SQL and JavaScript learning work, with Codex providing
hints, questions, simple explanations and reviews. The preferred review unit is a
complete, bounded code block. Give exactly one next learning task, with its topic,
concrete action and verification criterion, then wait for an attempt or question.
A finished solution is appropriate only when explicitly delegated or when a small
boundary has been agreed; after working together, Francis runs and explains it.
Earlier explicit milestone takeovers are recorded as bounded exceptions, not
standing permission to write future learning code.

Codex may offer environment setup, basic HTML/CSS and other bounded supporting
work. Explain the proposed change, expected result and learning boundary; wait for
a decision unless the area was already explicitly delegated. Do not complete a
learning task during support or repairs. Planning entries alone do not authorise
implementation. Read-only/planning requests leave every file unchanged. See
[AGENTS.md](AGENTS.md) and the project-milestone skill for the current workflow.

## Understanding and visitor rules

- Subject understanding is **Still Learning**, **Needs Review** or **Completed**.
  A visitor may move in either direction.
- Completed requires a fresh, deliberate personal confirmation. Quiz scores,
  correct practice answers, completed exercises and project-milestone approval
  never supply that confirmation automatically.
- Returning to Still Learning or Needs Review clears the current confirmation,
  while earlier status history is retained. Status and history save together.
- A name is a greeting label. New visits get random IDs, four Still Learning
  subjects and zero activity, even when the same name is entered again.
- End Visit revokes access while retaining records. Start New Visit ends the old
  identity and returns to name entry. Refreshes, tabs and browser restarts can
  reuse the same cookie and do not necessarily start a new visit.
- Every progress/result query uses the active visit from the signed session.
  Same-name visitors cannot read or change each other's results.
- Public source contains curriculum and test definitions, never original databases,
  visitor records, backups, cookies or private signing keys.

## Version 1.0 — six milestones verified, completed and closed

| Milestone | Delivered result and evidence | Approval |
| --- | --- | --- |
| 1. Design related tables | Francis designed Tasks (`task_id`, `title`, `status`, `category_id`) and Categories (`category_id`, `category_name`), explained primary/foreign keys and the one-category-to-many-tasks relationship. | Verified from the learner's sketch and explanation. |
| 2. Create and query SQLite | Francis wrote the schema, three category inserts, one exercise and an INNER JOIN. The learner's SQLite run and independent in-memory checks returned `Practise JOINs` with SQL exactly once. | Verified for the original prototype; preserved rather than repeated. |
| 3. Python learning-progress core | Revised four-table database, six Python functions, confirmations, transactions and persistence were checked; Francis completed the practical learning review for all six functions. | Personally approved, verified, completed and closed. |
| 4. Flask browser interface | Topic/status forms, explicit unchecked confirmation, Python validation, 303 redirects, persistence after restart, populated/empty browser pages and learning review passed. Temporary verification cleanup was accepted. | Personally reviewed and approved; verified, completed and closed. |
| 5. JavaScript interactions | Saved-status filtering, All/default behavior, no-match message and unchecked-completion warning; Python protection still works without JavaScript. Nine browser test groups and personal review passed. | Personally approved; verified, completed and closed. |
| 6. Summaries and integration | JOIN/GROUP BY/COUNT summaries, zero counts, dated practice and status history; 12 Python/SQL tests, 11 browser groups and personal review passed. | Personally approved; verified, completed and closed. |

### Version 1 database and function evidence

The revised prototype uses Categories (understanding status/current confirmation),
Tasks (exercise completion), QuizAttempts (score summaries) and TopicStatusHistory.
The original JOIN, adding SAP, repeated dated exercise entries, invalid inputs,
foreign keys, confirmation rules, persistence and transaction rollback all passed.
A correct exercise or perfect quiz left understanding unchanged.

| Function | Accepted verification |
| --- | --- |
| `connect_database()` | Existing-file read/write connection and enabled foreign keys; missing-file rejection creates no empty database. |
| `list_topics()` | Correct topic ID/name/status tuples and an empty list when there are no topics. |
| `record_exercise()` | Five test groups passed: valid/trimmed titles including apostrophes, incomplete defaults, returned ID, blank/invalid-reference rejection, persistence and unchanged understanding. |
| `record_quiz_attempt()` | 22 tests passed: separate dated attempts, valid/zero/partial/perfect scores, IDs, invalid names/types/ranges/references and no automatic topic completion. |
| `change_topic_status()` | Seven groups passed: explicit boolean confirmation, reversible status changes, history/timestamps, fresh confirmation, invalid input and rollback on history failure. |
| `create_topic()` | Five groups passed: valid names, blank/duplicate rejection and atomic initial Still Learning history. No partial topic remains after a failed history insert. |

Francis explained how to call each function and what it returns, as well as
validation, rollback and personal confirmation. The later `get_learning_overview()`
helper adds read-only summaries/history without changing those guarantees.

**Accepted historical limitation:** the earlier manually created SQL topic lacked
an initial history entry. That history was preserved as recorded, not repaired
with invented dates. New-topic creation saves initial status/history atomically.
Version 1 recorded supplied quiz summaries; it did not contain interactive lessons
or automatic answer checking. Those features arrived in Phase 2.

## Phase 2 — approved scope and milestone evidence

The approved scope is one beginner topic per subject: SQL SELECT/WHERE, Python
variables/functions, JavaScript values/DOM/events and SAP ERP concepts. Each subject
has ten practice questions shown one at a time and a separate five-question quiz,
with unlimited retries. Practice reveals the correct answer and explanation after
each response; quizzes reveal them only after the complete submission. Python
calculates scores rather than trusting submitted totals.

| Milestone | Implemented result and observed checks | Status |
| --- | --- | --- |
| P2.1 — Separate foundation | Separate application and reproducible database setup; Version 1 protection; 26 Python/SQLite tests passed. Personal browser review confirmed the foundation page and all four subjects. | Verified, personally approved, completed and closed. |
| P2.2 — Temporary visitors | Random identities, personalized greetings, signed sessions, stable private key, fresh progress, End/New Visit and same-name isolation; 51 tests passed. The historical data upgrade was checked without losing records. Personal browser review passed. | Verified, personally approved, completed and closed. |
| P2.3 — SQL learning flow | SELECT/WHERE lesson, ten-question practice sequence, unchanged five-question quiz, immediate practice explanations, personalized scoring, unlimited retries and saved activity. 77 Python/SQLite tests and ten expanded-practice browser groups passed; personal review confirmed the full flow. | Verified, personally approved, completed and closed. |
| P2.4 — Other subjects | Python, JavaScript and SAP each gained a lesson, ten practice questions and five quiz questions using shared handlers. 90 Python/SQLite tests and 15 browser groups passed; personal review passed for all three subjects. | Verified, personally approved, completed and closed. |
| P2.5 — Connected tracker | All four subjects in My Progress, zero-inclusive counts, scores, dated activity/status history, filtering, reversible status changes and confirmation. Final evidence: 119 Python/SQLite tests and 19 browser groups, plus personal review. | Verified, personally approved, completed and closed. |
| P2.6 — Additional release verification/review | Separate planned final-release milestone; not implicitly started by existing regression checks, documentation work or repository preparation. | Open; not started. |

P2.3 practice originally had one question; the personally requested expansion to
ten questions was implemented before closure. P2.4 applied that reviewed structure
to the remaining subjects. No learner-written code is executed and no live SAP
system is contacted. Educational examples are not seeded visitor activity.

### Connected tracker guarantees accepted at P2.5 closure

- Actual checked answers, correctly completed practice entries, quiz attempts,
  scores and answer snapshots save with UTC dates in schema 3.
- Signed visit/subject/activity tokens and transaction checks prevent duplicate
  refreshes or repeated submissions from inflating counts; unlimited new attempts
  remain available. Quiz attempts are counted once per submission, not per answer.
- JOINs retain subjects without activity. GROUP BY and COUNT produce separate,
  zero-safe topic totals; filtering only changes visibility.
- Current understanding and status history remain independent of practice/quiz
  results. Completed needs personal confirmation, including without JavaScript.
- Europe/Berlin display uses timezone rules for winter/summer and date rollover;
  saved UTC records are not rewritten.
- Explicit visit controls and explanatory text prevent confusion between resuming
  a cookie and starting a genuinely fresh visit. Earlier results remain owned by
  the earlier visit. Lesson links stay blue after being visited and have visible
  keyboard focus. Local subject icons appear on home, subject cards and My Progress.

Francis personally reviewed visitor sessions, lessons, practice, quizzes, scoring,
progress tracking, status history, local timestamps, navigation and icons, and
explicitly approved P2.5 closure. Its final 119/19 test evidence and approval remain
preserved independently of the cover enhancement.

## Separate enhancement — Welcome Cover Page

**Status: verified, personally approved, completed and closed.** This is separate
from P2.5 and P2.6.

The cover always appears at `/`: a soft blue-and-white background, decorative
translucent 4U watermark, centered welcome title and blue ENTER link. Watermark/title
reveal, hover glow, click pulse and a 1.2-second zoom/fade lead to `/learn/`.
The cover does not create, end or replace a visit. An active visitor resumes the
same dashboard; a visitor without an active cookie sees name entry.

Keyboard focus, responsive layouts, touch input, readable contrast, reduced-motion
preferences and a JavaScript-disabled link were verified. Back/pageshow restores
a usable cover. All **125 Python/SQLite tests and 26 browser groups** passed
(19 learning/tracker groups plus seven cover groups). Francis personally reviewed
and approved the final design and animations. The implementation followed the
written design brief; no unavailable reference-image match is claimed.

## Approved source and independent preparation

| Original source commit | Approved snapshot |
| --- | --- |
| `70ca080` | Completed Version 1.0 progress tracker. |
| `1556cc9` | Completed P2.5 and its earlier Phase 2 dependencies. |
| `fe77b84e06ff82f54c28bb780a03196909f6a03a` | Approved Welcome Cover Page over the preserved learning application. |

Those commit IDs document the earlier development history; they are not existing
commits in this new repository. The independent folder was exported from the last
approved snapshot without copying any Git history, private data or teaching
materials. Version 1 source/test compatibility, approved P2.5 and the cover remain
preserved. The complete independent copy passed a fresh dependency installation,
125 Python/SQLite tests and 26 browser groups using disposable data. Reproducible
setup created schema 3 with four subjects/topics and no visitors or activity.

The first public-release preparation changes documentation only: public approval
summaries replace operational preview logs; learning rules and source attributions
remain. Francis Furio is the public author. The reviewed file set stays at 58 files.
Application code, assets, tests, dependencies and original data are unchanged.

## Current task and permission boundary

The authorised work is documentation cleanup and preparing a new Git repository
on `main` with the personal HTTPS origin and a repository-local GitHub noreply
email. This does not authorise a commit or push. Review the exact initial file set,
then wait for explicit approval before creating the first commit.

P2.6, new application features, database upgrades, deleting saved records and Render
deployment are outside this task. Future production work will need separate
configuration, storage decisions and verification. No account system, external
database migration or hosting setup is silently added.
