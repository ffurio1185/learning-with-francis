# Learning with Francis — project plan and approval history

## Project Overview — Learning with Francis

### Version 1 — Learning Progress Tracker

Version 1 established the foundation of Learning with Francis, helping learners
organize and track progress across SQL, Python, JavaScript and SAP. Learners
personally control their status: Still Learning, Needs Review or Completed.

### Version 2 — Interactive Learning Platform

Version 2 expanded the tracker with lessons, practice exercises, quizzes,
explanations, feedback, individual progress tracking, improved navigation, a
Welcome Cover Page and English–German language support.

### Future Development

Learning with Francis is an evolving educational application. Its creator intends
to explore future versions, additional subjects and features that improve the
learning experience.

**Author:** Francis Furio

**Current application:** approved Version 2.0 learning functionality, connected
progress tracker and Welcome Cover Page.

**Current status:** L1–L5 are verified, personally approved, completed and closed.
This public release candidate uses a separate clean history based on published
commit `dbeae6f`; the approved development branch remains preserved separately.
Francis accepted L5’s automated/browser verification and personally approved the
English/German experience and responsive correction. P2.6 local release preparation
is authorised and in progress; public deployment has not started. The public
candidate contains no audio. Earlier approvals authorised two scoped local commits: the approved
bilingual foundation, then the approved Overview/About/button enhancement.
No merge, push or deployment is authorised.

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

## English/German enhancement — five approved milestones

Published Version 2.0 is preserved on `main` at
`dbeae6f7549da79d0b0aab172e2efcde2e3aa1fe`. Development is separate on
`feature/english-german`. Francis explicitly delegated the bounded L1
implementation while retaining explanations and review of important Python and
JavaScript decisions. The earlier 58-file count records the first release, not
this enhancement's expanded source set.

| Milestone | Scope | Status |
| --- | --- | --- |
| L1 — Translation foundation | Flask-Babel catalogs, English/German cover controls, safe session preference and security checks. | Verified, personally approved, completed and closed. |
| L2 — Application interface | Translate navigation, visit forms, progress display and validation messages; language switching without losing activity. | Verified, personally approved, completed and closed. |
| L3 — SQL learning content | Translate SQL lesson, practice, quiz, explanations and feedback while preserving code and answer IDs. | Verified, personally approved, completed and closed. |
| L4 — Remaining content | Translate Python, JavaScript and SAP learning content. | Verified, personally approved, completed and closed. |
| L5 — Complete verification | Verify both languages, saved progress, accessibility and personal browser approval. | Verified, personally approved, completed and closed. |

### L1 implementation and observed verification

- Flask-Babel selects the locale per request from an allowlist (`en`, `de`).
  English is the default, independently of browser headers. English source text,
  German editable/compiled catalogs and `babel.cfg` provide reusable organization.
- The cover has US/English and German/Deutsch controls, readable labels,
  keyboard focus and selected indicators. Local SVG flags do not depend on emoji
  fonts. The blue-and-white background, 4U watermark, ENTER link and existing
  1.2-second entrance script remain; no JavaScript source changed.
- The native POST action `/preferences/language` requires one valid CSRF token
  and one allowed language. Missing, duplicate, forged and unsupported values are
  rejected. A fixed cover redirect prevents arbitrary external destinations.
  Normal escaping, signed/HttpOnly/SameSite cookies and no-store pages remain.
- Language selection accesses no database and creates no visit. Changing language
  preserves the active identity, answers, scores, timestamps and confirmation
  rules. Starting/ending visits clears identity and tokens but retains only a valid
  chosen language. New cookies default to English; tabs share their browser cookie.
- Fresh dependency installation succeeded in a disposable environment. All
  **143 Python/SQLite tests passed** (125 existing plus 18 L1 checks), including
  invalid/tampered requests, same-name visitors, preference persistence, saved
  activity, open quiz submission and catalog/source consistency.
- All **32 browser groups passed**: 19 existing learning/tracker groups, seven
  existing cover groups and six L1 groups. Checks cover both selections, local
  flags, keyboard controls, desktop/mobile/landscape, 200% text, disabled JavaScript,
  reduced motion, independent visitors and End/New Visit. No unexpected JavaScript
  or server errors remained. All test databases were disposable and removed.
- A subject-route collision found during verification was resolved by using
  `/preferences/language`; two new test-fixture mistakes were corrected. Final
  runs passed. No learning handlers, schemas or saved records needed repair.

**L1 personal approval:** Francis tested the cover in English and German and
approved the design, selection controls, layout and overall appearance. L1 is
verified, completed and closed with its 143 Python/SQLite tests and 32 browser
groups recorded above.

**L1 delivery boundary:** only the cover and its form errors were translated in L1.
Other screens remained English at L1 delivery; L2 now translates their interface.
Version 1, approved P2.5, original databases/backups and the classroom repository
remain protected. `main` still points to the published release; no changes have
been committed, pushed or merged. L2 is personally approved and closed. L3 is personally approved and closed; L4 is personally approved and closed. L5 verification is now authorised; P2.6, music, Render
and database upgrades have not started.


### L2 — application interface implementation and evidence

**Status: verified, personally approved, completed and closed.** Francis
authorised L2 after personally approving L1. Work stays on `feature/english-german`.

- English remains the default. The German catalog now covers 162 interface
  messages, including greetings, visit/name forms, navigation, status filters,
  counts, progress/history tables, confirmation controls, activity/result controls,
  empty states, validation, error pages and MEZ/MESZ timestamp labels.
- Status labels are translated for display only: saved values, form values,
  subject/question IDs, answer keys, grading and UTC storage remain canonical.
  Completed still requires explicit personal confirmation; results never supply it.
- Shared native language controls return to the same application page through a
  signed, visit-bound, time-limited local GET destination. CSRF checks reject forged
  or duplicated input; old-visit and foreign return tokens cannot change ownership.
- Small, ungraded name/answer drafts are carried through a one-time signed-session
  draft, restored only on the matching visit/page. Quiz submission identity and
  practice round/position survive a switch. Draft fields do not save scores,
  create attempts or change statuses. End/New Visit clears drafts and old tokens.
  Signed cookies are not encrypted; the short-lived draft can contain an entered
  name or selected option IDs, then is consumed after the language redirect.
- Form-associated language buttons follow the main submit button in document
  order. Enter still starts a visit or submits the learning form. Native language
  switching preserves drafts without JavaScript. With JavaScript, localized HTML
  supplies required-input and confirmation hints; no parallel JS catalog is used.
  Version 1’s original script is unchanged.
- German long-text wrapping and constrained filter width fix overflow at enlarged
  text sizes. Existing cover design/animation, blue links, icons, keyboard focus,
  table scrolling and mobile layouts remain. Time labels use MEZ/MESZ in German
  and CET/CEST in English with unchanged Europe/Berlin offsets and stored dates.
- **159 Python/SQLite tests passed**: the 143 L1/existing checks plus 16 L2 checks.
  Coverage includes default/German interfaces, validation, confirmation, zero
  activity, real results, all-subject quiz drafts, practice round continuation,
  duplicate protection, bounded/untrusted draft input, signed-return security,
  same-name isolation, End/New Visit and winter/summer offsets.
- **40 browser groups passed**: 19 existing learning/tracker, seven cover, six L1
  and eight L2 groups. Verified English/German selection, native name drafts,
  Enter-key submission, German filters and confirmation messages, saved statuses,
  all four quizzes, ten-question practice with continuation/restart, result
  refreshes, separate same-name visitors, no-JavaScript protection and mobile/
  landscape/200% text layouts. No unexpected JS/console/server errors remained.
- Every automated database was disposable schema 3 under `/tmp` and removed.
  Review uses a separate fresh disposable preview; original databases and the
  classroom repository are unchanged. No migration, commit, push or merge occurred.

**Scope deferred at L2 delivery:** lessons, topic titles, question/answer content,
explanations and personalized activity feedback remain English for L3/L4. English
material is marked appropriately on German pages. Without JavaScript, browser-native
validation follows the browser’s locale; Python validation messages remain
translated. L3–L5, P2.6, music and deployment were not started at L2 delivery.
Francis’s later personal review and approval, recorded below, closed L2.


**L2 personal approval:** Francis personally reviewed both language interfaces,
confirmed that switching, translated navigation, forms and progress tracking work
well, and approved L2. The 159 Python/SQLite tests and 40 browser groups above are
preserved as its verified delivery evidence. L2 is completed and closed. Francis
understands that learning-content translations belong to L3/L4 and has authorised
L3 implementation only. No commit, merge, push or deployment is authorised.


### L3 — SQL learning content implementation and evidence

**Status: verified, personally approved, completed and closed.**
Only L3 was authorised after L2 closure. Work remains on `feature/english-german`.

- SQL SELECT/WHERE lesson prose, examples' descriptions, subject/topic titles,
  ten practice prompts, descriptive options, five quiz prompts, explanations and
  personalized activity feedback now render in English or natural German.
  The full catalog contains 230 messages. English remains the default.
- Literal SQL queries, table/column names, quoted values, fictional sample rows,
  question/option IDs, correct-answer keys and content versions are unchanged.
  `N_` marks English source text for extraction and returns it unchanged.
- `sql_display.py` builds translated public question/view copies. Python grading
  and attempt saving continue using canonical English content. Unanswered forms
  contain no answer keys or explanations. Practice reveals feedback immediately;
  quizzes reveal answers only after the full submission.
- Low, passing and perfect SQL quiz feedback is personalized in the selected
  language. Practice feedback is also translated. Existing scores, dated history,
  counts, visitor ownership, confirmation protection and unlimited retries remain.
  A perfect result still never completes understanding automatically.
- Exact known saved answer snapshots translate at display time. Unknown or earlier
  prompt/choice/explanation wording stays in its original language with a notice.
  No historical text is replaced or invented; no database migration is required.
- Native language changes retain pending answers, quiz submission identity and
  practice round/position. Stored UTC dates and Berlin display rules are preserved.
  At L3 delivery SQL pages declared the content language; other subjects remained
  marked English until L4.
- **175 Python/SQLite tests passed**: 159 existing/L1/L2 checks plus 16 L3 checks.
  Verified all 15 questions, all six possible quiz scores, correct/incorrect
  practice, full rounds, retries, duplicate/forged submissions, language drafts,
  canonical saved snapshots, legacy fallback, escaped names, persistence,
  independent same-name visitors and no automatic completion.
- **46 browser groups passed**: 19 learning/tracker, seven cover, six L1, eight
  L2 and six L3 groups. L3 covers the German lesson and unchanged executable
  examples, all ten practice questions, all feedback bands, five-question quizzes,
  retries, live language changes, read-only result translation, accurate totals,
  desktop/mobile/landscape/200% text, keyboard submission, no-JavaScript use,
  confirmation protection and visitor isolation. No unexpected JS/server errors
  remained. One new browser assertion was corrected to reselect Completed after
  the existing server validation response restores the saved status.
- Automated checks used disposable schema 3 databases and removed them. The local
  review preview was refreshed with its existing disposable database and session
  key preserved; startup did not change either file. Original databases, backups,
  classroom files and Version 1 remain unchanged. No commit, merge, push or
  deployment occurred; `main` remains the published baseline.

**L3 personal approval:** Francis personally reviewed the SQL lesson, exercises,
quiz, questions, choices and German translations and officially approved L3.
The 175 passing Python/SQLite tests and 46 passing browser groups above remain
its delivery evidence. L3 is verified, completed and closed. Francis authorised
L4 for Python, JavaScript and SAP only; L5, P2.6, music, deployment and database
upgrades remain outside this work.


### L4 — remaining learning content implementation and evidence

**Status: verified, personally approved, completed and closed.**
Francis authorised L4 after personally approving and closing L3. Work remains on
`feature/english-german`; at L4 delivery L5 had not started.

- Python variables/functions, JavaScript values/DOM/events and SAP ERP lessons,
  descriptions and topic titles now support English and natural German. Each
  subject’s ten practice questions and five quiz questions include translated
  prompts, descriptive choices, explanations and personalized feedback. The
  shared catalog has 449 messages; English remains the default and fallback.
- The existing `sql_display.py` view layer now serves all four subjects. Its
  saved-answer lookup is scoped by topic and exact snapshot, because different
  subjects reuse question IDs. Known saved answers translate only when rendered;
  unknown historical wording stays in its original language with a notice.
- `N_` extraction markers return unchanged English. Executable code examples,
  technical choices, answer IDs/keys, content versions and stored English answer
  snapshots are unchanged. No database, migration, grading or session-rule change
  was needed. No new JavaScript or CSS was introduced for L4.
- Language switching preserves visitor identity, selected answers, quiz submission
  identity and practice round/position. Rendering saved results in either language
  does not write activity or status records. Correct answers never complete a topic;
  explicit personal confirmation is still required, and completion remains reversible.
- **193 Python/SQLite tests passed**: all 175 prior checks plus 18 L4 tests with
  subject/score subcases. Coverage includes all 45 new-subject questions, every
  possible quiz score, full practice rounds, correct/incorrect feedback, retries,
  duplicate/conflicting submissions, tampered input, escaped names, saved drafts,
  topic-scoped snapshot lookup, legacy fallback, restart persistence, accurate
  counts, same-name isolation, End/New Visit and confirmation protection.
- **60 browser groups passed**: 19 learning/tracker, seven cover, six L1, eight L2,
  six L3 and 14 L4 groups. New groups cover all three lessons, 30 practice questions,
  five-question quizzes and feedback bands, Next/Finish/restart, unlimited retries,
  draft-preserving switches, result refreshes, canonical saved activity, zero/private
  activity for a second same-name visitor, no-JavaScript quizzes/confirmation,
  reversible statuses, desktop/mobile/tablet/landscape/200% text and keyboard focus.
  No unexpected JavaScript, console or server errors remained.
- Two new browser assertions were corrected during verification: compare the
  practice token’s visit/round/position rather than its renewable signature time,
  and allow the existing completion timestamp beside the status label. These were
  test assumptions; no application behavior was changed to satisfy them.
- Every automated check used disposable schema 3 databases under `/tmp` and removed
  them. Hash checks confirmed all 68 protected classroom files (including original
  databases/backups), Version 1, schemas/migrations, SQL source and literal lesson
  examples unchanged. The review preview retains its disposable data and signing
  key. `main` remains `dbeae6f`; nothing is staged, committed, merged, pushed or deployed.

**L4 personal approval:** Francis personally reviewed Python, JavaScript, SQL
and SAP in German and approved the lessons, exercises, quizzes, answer choices
and feedback. Francis also switched between German and English while answering
questions and confirmed that question position and learning progress were
preserved. L4 is verified, personally approved, completed and closed. The existing
193 passing Python/SQLite tests and 60 passing browser groups remain its delivery
evidence; they were not rerun for this documentation-only closure.

**L5 scope approval:** Francis explicitly approved verification of both languages,
all four learning subjects, saved answers/progress, confirmation protection, visitor
isolation, persistence, error handling, accessibility, mobile/keyboard use and
no-JavaScript operation. The observed L5 results and remaining issue follow below.
P2.6 remains a separate, unstarted final-release verification/review milestone.
Music, hosting and database upgrades are outside this closure and require
separate authorisation. Personal confirmation before Completed remains mandatory.


### L5 — complete verification evidence and initial finding

**Status: verified, personally approved, completed and closed.** Francis
explicitly approved this scope after approving L4. Initial verification changed no
application files; the later authorised responsive correction is recorded below.
Francis has now accepted the verification results and completed his personal review.

- A fresh run of **193 Python/SQLite tests passed**, including preserved Version 1,
  all four subjects, grading, transactions/rollback, duplicates, forged input,
  same-name visit isolation, locale/session protection, saved drafts, status
  confirmation/reversal, persistence, error responses and Berlin winter/summer time.
- All **60 existing browser regression groups passed**: 19 learning/tracker,
  seven cover, six L1, eight L2, six L3 and 14 L4. Cover design/animation, English
  default, translated navigation/content, prompts/choices/explanations, score
  feedback, visible filters, zero activity, empty states and prior workflows passed.
- A supplementary **16-flow browser matrix** covered every subject in English and
  German with JavaScript enabled and disabled. Its **19 functional/check groups
  passed**, with layout failures tracked separately below. Each flow completed a
  lesson, all ten practice questions and a five-question quiz. It checked native
  language changes mid-answer, retained radio choices, current practice position,
  quiz submission identity, refresh idempotency, saved result translation, actual
  progress/history, keyboard entrance/name/radio/confirmation activation and labeled
  controls with unique IDs, headings, page languages and decorative-image alt text.
- The disposable matrix database independently contained 16 isolated same-name
  visits, **160 practice attempts, 80 correct practice completions, 16 quiz attempts
  and 240 saved answers** (160 practice plus 80 quiz answers). Canonical English
  snapshots, counts, SQLite integrity and foreign keys checked successfully.
- Correct answers and quiz scores left all understanding statuses unchanged.
  Completed without confirmation failed with and without JavaScript; deliberate
  confirmation succeeded. Returning to Needs Review cleared the current confirmation
  timestamp and preserved earlier history. Language changes did not change either.
- An actual test-server restart with the same disposable database/signing key
  preserved identity, language, scores, counts and status. Same-name browser
  contexts could not open each other’s results. End Visit invalidated restored old
  cookies; a fresh same-name visit had a new ID, zero activity and four initial
  status entries while all 176 earlier activity records remained in SQLite.
- Fresh Babel extraction matched all **449 catalog messages**; editable/compiled
  catalog consistency passed in the suite. All 32 Python files parsed; Node syntax
  checks passed for the four application scripts. No unexpected JavaScript,
  console, missing-static-resource or server errors were observed.

**Initial finding — English My Progress at 200% text (resolved by the approved correction below):**
The additional matrix recorded **8 reproducible layout failures**.
Measured cases (language, viewport width, document width, root text size):
- `en`: viewport **375px**, document **384px**, text **32px**.
These are whole-page horizontal overflows, separate from the intentionally
scrollable progress/history tables. They occurred on the English progress page
with enlarged text; functional saving and isolation checks still passed. The
German enlarged-text checks passed. The existing Phase 2 wrapping rule targets
German; this is a possible contributor, not a complete root-cause diagnosis.
Screenshots and measurements were retained outside the public source. No repair
was applied during that initial verification. Francis subsequently authorised
the narrow responsive correction below; its final enlarged-text checks pass.

**Verification boundaries and cleanup:** Automated browser checks used Chromium
with emulated desktop/phone/tablet/landscape sizes, keyboard and enlarged text;
they are not a formal WCAG certification or a physical-device/screen-reader/
Firefox/Safari audit. Without JavaScript, the client-side saved-status filter
stays disabled and all subjects remain visible; core server-backed learning,
language switching, results and confirmation controls work. Browser-native
validation uses the browser’s language when JavaScript is disabled. Unknown
historical wording retains its original-language fallback without rewriting records.

All automated databases were disposable schema 3 files under `/tmp` and removed,
including failed harness runs. The supplemental harness was corrected to match
the existing practice-round query string and the English “Practice complete!”
heading. A supplemental run was interrupted after Playwright stalled while
injecting enlarged-text CSS into a JavaScript-disabled page; direct test-only
text sizing avoided that automation wait. The no-JavaScript layout was measured
without the duplicate full-page screenshot. Application files were not changed.
The live review preview was checked
without restarting it, retaining its disposable records and signing key.
Hash comparisons confirmed application/source files, all 68 protected classroom
files, Version 1, original databases/backups and the review records unchanged.
During initial verification only this plan was edited. No music was downloaded
or implemented; its proposal
and licensing research are unchanged. P2.6 remains unstarted; no staging, commit,
merge, push, deployment or database upgrade occurred.

**Acceptance received:** Francis personally approved L5, including the corrected
responsive layout. His final review and closure are recorded below.


### L5 — approved progress-page responsive correction

**Status: correction verified and personally approved; L5 completed and closed.**
Francis authorised a narrow repair of the English My Progress overflow. No music,
P2.6, release or unrelated feature work was authorised or performed.

- **Confirmed cause at 375px/200% text:** the heading uses 64px text; the unbroken
  word “Progress” measured 319.41px and extended to x=384.41 within the narrower
  content area. The document became 384px wide. A heading-only DOM wrapping
  experiment reduced it to 375px; removing that experiment restored the failure.
- **Narrower-screen recheck:** at 320px/200% text, long English summary labels also
  imposed minimum-content widths, extending status cards to x=325.30 and the
  completed-exercise card to x=323.30. Wrapping the progress container reduced
  the document to 320px. This justified one inherited rule scoped to that page.
- **Final minimal change:** add `class="progress-page"` to the existing progress
  `<main>` and `.progress-page { overflow-wrap: anywhere; }` inside Phase 2’s
  existing `max-width: 40rem` media query. No text, translations, font sizes,
  colors, controls, table scrolling, Python, JavaScript or database code changed.
  The rule is inactive on normal desktop widths and never affects Version 1.
- **40 focused layout cases passed:** both languages, JavaScript on/off, widths
  320, 375, 768, 844 and 1440px, and 100%/200% text. Document width equals viewport
  width in every case. The originally failing 375px case now stays at 375px,
  and 320px also stays at 320px. Table regions retain their own horizontal scrolling.
- **Normal desktop design preserved:** English and German 1440px screenshots were
  pixel-identical to the pre-correction wrapping behavior. An earlier unrestricted
  progress rule changed English table allocation; restricting the final rule to
  small screens removed that difference before final regression verification.
- **Final regressions passed:** 193 Python/SQLite tests, all 60 existing browser
  groups and the 19 supplementary functional/check groups across 16 full bilingual
  subject flows with JavaScript on/off. The matrix now reports **zero layout
  failures**, resolving all eight original cases. Confirmation/reversal, saved
  choices/position, real results/history, visitor isolation, integrity, persistence,
  keyboard use and error protection remain verified. No unexpected JS/server errors.
- All checks used disposable schema 3 databases and removed them. Hash comparisons
  confirmed that original databases/backups, existing preview records/signing key,
  all 68 protected classroom files and Version 1 remain unchanged. Only the two
  named presentation files and this plan changed in this correction. The review
  preview is refreshed using the same disposable database/session configuration.
  Music proposal/licensing text, P2.6 and Git refs are unchanged; no staging,
  commit, merge, push, deployment or database upgrade occurred.

**Personal approval and closure:** Francis officially approved L5 after personally
confirming that My Progress displays correctly in English and German, language
switching preserves his entered name and selected answers, practice exercises work,
and learning status remains under his personal control without automatic completion.
He accepted the responsive correction and the recorded verification: **193 passing
Python/SQLite tests, 60 existing browser groups, 19 supplementary functional/check
groups and 40 focused layout cases with zero remaining layout failures**.

L5 is **verified, personally approved, completed and closed**. This documentation-only
closure does not rerun the accepted tests or change application files, databases,
backups or visitor records. The previously recorded Chromium/assistive-technology
verification limits and no-JavaScript filter fallback still apply. P2.6 and music
implementation remain unstarted; commits, merges, pushes and deployments require
separate explicit approval.


## Separate enhancement — Project Overview and bilingual cover introduction

**Status: completed, personally approved and closed.** Francis officially approved
the final Project Overview, English/German About introduction and creator credit,
ENTER/EINTRETEN lettering and overall appearance/functionality. This enhancement
is separate from the closed L5 milestone, P2.6 and the proposed music enhancement.

- Added the approved Project Overview before Purpose and learning priorities,
  introducing Versions 1 and 2 and future development. Existing goals, milestones,
  approvals and historical records are preserved without rewriting or reordering.
- Added the approved English/German About Learning with Francis introduction and
  Francis Furio’s creator credit below the existing full-height welcome area.
  A quiet “Discover the project” / “Mehr über das Projekt” native link and downward
  arrow make the introduction discoverable without extra JavaScript or animation.
- Reused the existing protected language controls and Babel catalog; six new German
  messages are translated, compiled and checked. The introduction appears only on
  the cover. No routes, visitor/session handlers, grading, status or database logic
  changed. The 1.2-second entrance, reduced-motion behavior and plain ENTER link
  remain intact. Normal English/German desktop hero geometry and content screenshots
  match the prior design exactly.
- Narrow phone and short landscape screens reserve footer space for the new scroll
  cue. Enlarged cover text wraps rather than clipping or overlapping the footer.
- **194 Python/SQLite tests passed**, including the new bilingual cover/no-database
  check and preserved Version 1, learning, session, language and progress tests.
  All **60 existing browser regression groups passed**. An additional **five focused
  browser groups passed**, including **40 layout cases**: both languages, JavaScript
  enabled/disabled, widths 320/375/768/844/1440px and 100%/200% text. Checks covered
  no horizontal overflow, non-overlapping controls/footer, keyboard focus and native
  anchor navigation, correct wording, cover-only content, unchanged active visits,
  SQLite integrity and foreign keys. No unexpected page/server errors were observed.
- Browser automation used Chromium and emulated viewports, not a formal accessibility
  certification or a physical-device/screen-reader audit. Test databases were
  disposable schema 3 files and removed; the separate review preview uses disposable
  data only. Hash checks confirmed Version 1, original databases/backups, existing
  visitor/preview records and all 68 protected classroom files remain unchanged.

### Final review adjustments — overview placement and ENTER lettering

Francis accepted the overall cover/About design and requested two final adjustments
before approval. The file beginning “Project plan: Personal Learning Application”
is the preserved classroom plan; it is unchanged. The independent project’s single
“Project Overview — Learning with Francis” now follows its main title immediately,
with Version 1, Version 2 and Future Development in that order. Existing content
and historical records are retained; no classroom text was copied or rewritten.

The ENTER/EINTRETEN lettering is visually enlarged by 12% and its arrow by 14%.
Static child-element scaling preserves the button’s outer dimensions, position,
font weight, colors, hover/focus behavior and entrance animation. The approved
About introduction, creator credit, cover template and translations are unchanged.

**Verification:** 194 Python/SQLite tests and 32 relevant existing browser groups
passed (seven cover, six language and 19 learning/progress groups). Four focused
bilingual/JavaScript-on-off groups passed, covering 40 viewport/text-size cases.
Before/after measurements confirmed identical button, title, watermark, cover
content and About geometry, unchanged button styling and About markup, and the
requested text/arrow enlargement. Keyboard entry, reduced-motion/no-JavaScript
navigation and no cover-triggered database writes also passed. Chromium/emulated
device verification retains the previously recorded accessibility boundaries.
Disposable test databases were removed; the existing disposable review preview
remains available without a restart or any changes to its saved visitor records.

Only this plan and the cover stylesheet changed for these final adjustments.
Protected Version 1/classroom files, original databases/backups, both existing
preview databases/signing keys, Git refs and staging are unchanged. L5 stays closed;
P2.6 and music remain unstarted. Francis subsequently reviewed and approved these
final adjustments.

**Personal approval and closure:** Francis accepted the final button appearance,
English/German introduction and creator credit, correctly placed Project Overview,
and overall functionality. The recorded implementation and verification evidence
above is accepted; the enhancement is **completed, approved and closed**. L5 remains
closed, with P2.6 and music implementation unstarted. Francis authorised a separate
local commit of the previously approved bilingual foundation, followed by a scoped
commit of this enhancement. Merging, pushing and deployment remain unauthorised.


## P2.6 — clean public release candidate

**Status: local technical preparation verified; open pending final publishing and
live-deployment approvals.** Francis authorised practical local release preparation
while preserving the current 12-hour session behavior. Earlier seven-day session
and retention suggestions are not final approvals and have not been implemented.

The candidate starts from published `dbeae6f` and carries approved files from
`37e712f` without importing later development Git history. The separate approved
local development repository, music implementation, original databases/backups and
visitor records remain unchanged. The public candidate has no audio assets/player,
private data or music-bearing commits. This boundary supersedes any earlier proposal
to merge the full development history. There is no force-push or history rewrite.

- All six Version 1 milestones, P2.1–P2.5, L1–L5, bilingual learning, subject icons,
  connected progress and the approved cover/About/button enhancement remain closed
  and functional. Temporary visitors retain private visit-owned records and must
  personally confirm Completed; scores never establish understanding automatically.
- New production-only files provide validated environment configuration, external
  stable signing keys, Secure/HttpOnly/SameSite cookies, trusted hosts, security
  headers, database readiness and Gunicorn. The approved local factory, 12-hour
  session/form-token behavior and existing application functions are unchanged.
- The runtime start script initialises a fresh schema-3 database on a private
  persistent mount, or validates an existing one without reset/upgrade. A fresh
  local database has four subjects/four topics and zero visitor/activity records.
  Render configuration proposes one Frankfurt web service, a 1 GB persistent disk
  and disabled automatic deployment. No live storage/resource has been created.
- Final checks: **210 Python/SQLite tests and 66 Chromium browser groups passed**,
  including real Gunicorn restart persistence, production security/confirmation,
  same-name isolation and no-JavaScript flows. JavaScript/shell syntax, dependency
  consistency and the official Render JSON Schema checks passed. See
  [verification details and resolved test issues](docs/RELEASE-VERIFICATION.md).
- Protected-file comparisons matched all 153 source/classroom files, including
  original databases/backups and the previous uncommitted source-plan update.
  Functional tests used disposable databases; original records were never used.

[Public release procedure](docs/PUBLIC-RELEASE.md) records the exact personal GitHub
repository and remaining deployment prerequisites. The complete proposed file list
is in [the publishing manifest](docs/PUBLISH-FILES.txt). The candidate remains
uncommitted for final review; no push, purchase, public deployment or publication
of operator details is authorised yet.

The next practical action is approval of the reviewed local release commit and its
normal push to personal `origin/main`. Public hosting then requires approved real
Impressum/privacy information, hosting costs and operational backup arrangements.
These are release prerequisites, not requests to rebuild completed learning work.
