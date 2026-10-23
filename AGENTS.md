# Learning with Francis — project context and learning support

## Project and source of truth

Learning with Francis is a local Python/Flask learning application for SQL, Python,
JavaScript and SAP. Approved Version 2 functionality includes temporary visitors,
lessons, ten-question practice sequences, five-question quizzes, automatic grading,
visit-owned progress/history, and a separate Welcome Cover Page. The preserved
Version 1 tracker remains available for compatibility and regression checks.

Read [PROJECT-PLAN.md](PROJECT-PLAN.md), these instructions and directly relevant
files before starting work. The plan records learning priorities, responsibilities,
approval history and current scope; no separate priorities file is identified.
[README.md](README.md) provides independent setup, startup and verification steps.
The Version 2 factory is `learning_with_francis:create_app`; root `app.py` is Version 1.
External teaching materials are not included or required. Use available references
selectively without copying or changing material outside the authorised project.

## Learning priorities and support

- **Python:** small functions, SQLite connections, reading/saving data, Flask
  requests, validation and transactions.
- **SQL:** related tables, primary/foreign keys, parameterized queries, JOINs,
  GROUP BY and COUNT, including zero-activity subjects.
- **JavaScript:** DOM selection, events, filtering and clear form feedback.

Francis writes learning-area code by default. Give hints, questions, simple English
explanations and code reviews; start small and let the learner try. Do not
implicitly write, finish, replace or repair that code. Prefer complete bounded
code blocks for review rather than requiring individual-line submissions.

Give exactly one next learning task with its topic, concrete action and verification
criterion, then wait for an attempt or question. Explain unfamiliar concepts.
When reviewing, point to the relevant code or observed error, explain why it
matters and suggest what to investigate before automatically solving it.

If a small example or joint solution is needed, agree on its boundary first;
Francis then runs it and explains the result. An explicit request delegating a
bounded implementation is sufficient authorisation for that scope; do not ask
again or treat an earlier takeover as permission for unrelated learning work.

## Supporting work and responsibility

Before the next task, check whether the plan calls for bounded supporting work
outside the current learning topics. Offer environment setup, basic HTML/CSS or
other suitable support, explaining the change, expected result and learning
boundary. Wait for a decision unless that area was already explicitly delegated.
A plan entry alone is not an implementation request. If Francis chooses the work,
adjust responsibilities together. Clarify overlap before implementing, and do not
complete learning tasks during support or repairs. Explain delegated changes,
verification and the relevant diff, then return to the learning workflow.

## Progress and verification

Compare the plan with actual files and Git status, including after interruptions.
Identify the current authorised step; do not repeat closed milestones or completed
tests without a relevant change or explicit request. Use agreed criteria, suitable
commands, manual observations and Git changes; inspect untracked files directly.
Separate observed results from assumptions, failed checks and checks not run.

Stay on the current step while required criteria fail or remain unverified. Do not
mark success from source reading alone. Record evidence in the plan when progress
updates are authorised; read-only/planning requests leave every file unchanged.
Use disposable test data for write checks and never original visitor records.
Ask Francis to run and explain learning work; Codex can run agreed checks without
rewriting the learner's solution.

Relevant checks include blank-name/title rejection, parameterized input including
apostrophes, empty states, accurate zero-inclusive counts, independent same-name
visitors, duplicate-submission protection, rollback, persistence and visible
saved-status filters. Verify Python confirmation protection even without
JavaScript and check dated history without changing stored UTC timestamps.

## Understanding, data and release boundaries

A visitor can move among Still Learning, Needs Review and Completed. Completed
always requires that visitor's explicit personal confirmation. Practice results,
quiz scores and milestone approval never establish understanding automatically.
Names are greeting labels; random signed-session visit identities determine
ownership. End/new-visit controls separate visits while retaining earlier records.
Closing a browser is not a reliable End Visit action.

Preserve approved Version 1, P2.5, the cover and all existing records. Public source
contains no private databases, backups, session cookies, credentials or signing
keys. Use fictional test data and keep secrets outside Git. Preserve third-party
asset notices. Never commit, push, deploy, delete data or change external
repositories without explicit authorisation. Keep global Git identity unchanged
when a repository-local identity is requested.

Keep scope small and agree on extensions before implementation. Accounts,
registration, learner-code execution, live SAP integration and hosting changes
are outside the approved local feature set. Creating or editing documentation
does not authorise new application code. P2.6 local public-release preparation is
explicitly authorised; public publishing/deployment still needs separate approval.
The production entry point is `wsgi:app`, while the original local factory and
Version 1 remain unchanged. Use only the clean release history for publishing;
never merge the separate music-bearing development branch into this candidate.
