---
name: project-milestone
description: Guide Learning with Francis milestone work, verify progress, and offer one learning task or bounded supporting task while respecting the learner's coding responsibilities.
---

# Project milestone

Use this skill to start, resume, or review Learning with Francis milestone work. Read [AGENTS.md](../../../AGENTS.md) and [PROJECT-PLAN.md](../../../PROJECT-PLAN.md) for current priorities, responsibilities, approvals and verification criteria. Version 1 milestones, P2.1-P2.5 and the cover are closed; identify the current authorised task rather than restarting them. Skill invocation does not authorise unrelated work.

## Workflow

1. **Find the current step.** Read the plan, learning instructions, and relevant files. Compare actual results with the recorded milestone and current step, including after interruptions. Read a separate topic-priorities file if one is identified. External learning materials are optional references, not a project dependency; leave them unchanged.

2. **Check the evidence.** Inspect Git status and relevant changes. Use the current step's agreed criteria, suitable project commands, and manual checks. Inspect untracked files directly; ordinary Git diffs omit their contents. Distinguish verified results, failed checks, and checks not run. For the learner's work, ask them to run the result and explain it. If verification is unavailable, state the missing evidence without claiming success.

3. **Help with difficulties.** Describe the observed error with concrete evidence and simple English. Start with a small hint, explanation, review, or smaller step, then wait for an attempt or question. The learner writes Python, SQL, and JavaScript, including database connections, queries, Flask request handling, DOM changes, and events. Do not automatically write, complete, replace, or repair that code. If needed, agree on a small boundary before solving a step together; afterwards, have the learner run it and explain it.

4. **Control progress.** Stay on the current step while required checks fail or remain unverified. During authorised milestone work, record observed evidence and update the existing status and current-step fields in `PROJECT-PLAN.md`. Use open, in progress, or verified; mark a milestone verified only when all its criteria have observed evidence. Respect requests limited to particular files. For read-only or planning-only requests, do not edit any files, including the plan. Agree on scope or responsibility changes before implementing them.

5. **Check supporting work.** Before the next task, check whether the plan calls for bounded work outside the learner's Python, SQL, and JavaScript learning areas. Proactively offer supporting work when due, such as environment setup or basic HTML/CSS.

6. **Explain the offer.** Describe the proposed implementation, expected result, and boundary with learning work. Ask whether Codex should take it on or the learner wants to do it, then wait for the decision. An existing explicit delegation for that area is sufficient; do not ask again. A plan entry alone is not delegation.

7. **Respect responsibility.** Perform only delegated supporting work, verify it, and explain the result and relevant diff. If the learner chooses the work, record that responsibility during authorised progress updates. Clarify overlap before implementation. Do not complete learning tasks during supporting work or repairs.

8. **Give one learning task.** Once ready for the learner's next task, state exactly one topic, concrete action, and verification criterion. Wait for their attempt or question. Do not pair a pending supporting-work decision with another task.

## When no result exists

Recheck the actual project and find the first unverified step within the authorised scope. Give one task with a topic, concrete action and verification criterion. Do not restart the completed table design or assume a planned milestone is authorised. If evidence is unavailable, state what is missing and do not claim success.
