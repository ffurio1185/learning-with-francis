# Render Free public demonstration

## Scope and source

Published application: `c8ba21f` on personal
[GitHub main](https://github.com/ffurio1185/learning-with-francis).
The current local changes prepare Free hosting only; commit/push/deployment each
still require owner approval. Classroom and original development repositories,
original databases, backups and visitor records are outside this release.
The clean history contains no audio assets/player or music-bearing commits.
Do not merge the separate development history into this public release.

## Exact Free settings

| Setting | Value |
| --- | --- |
| Service | One Python Web Service, **Free**, Frankfurt |
| Source | `ffurio1185/learning-with-francis`, branch `main` |
| Build | `pip install -r requirements.txt` |
| Start | `sh render-start.sh` |
| Application | `wsgi:app` (not Version 1's root `app.py`) |
| Health | `/healthz` |
| Python | `3.14.4` |
| `LWF_DATA_DIR` | `/tmp/learning-with-francis` |
| `LWF_DEMO_MODE` | `1` |
| `LWF_SECRET_KEY` | Generate once in Render; keep stable and outside Git |
| Host validation | Render's `RENDER_EXTERNAL_HOSTNAME`; explicit `LWF_ALLOWED_HOSTS` only for additional exact domains |
| Automatic deployment | Off; review changes before manual deployment |
| Persistent disks, Postgres, paid workers/cron | **None** |

`render.yaml` configures these settings but creates nothing locally. The start
script privately creates schema 4 if absent, validates existing storage without
reset/upgrade, then runs one Gunicorn worker with four threads on Render's `$PORT`.
Only curriculum metadata is seeded; there are no demonstration visitors/results.
Never upload an existing database or signing key. HTTPS, Secure/HttpOnly/SameSite
cookies, host checks and production security headers remain required.

## Limitations and cost boundary

Render's Free service sleeps after 15 minutes idle; waking can take about a minute.
Its filesystem can be discarded on sleep, restart or redeployment, and Free cannot
attach a persistent disk. The workspace shares 750 Free instance hours per month.
Bandwidth/build allowances also apply: without a payment method, exhausted
allowances suspend service/builds; with a payment method, supplementary usage can
be billed. Use a Free workspace/service, avoid paid add-ons and review the current
usage dashboard. This configuration requests no paid resource; it is not a promise
of unlimited usage. Do not add a payment method or approve an upgrade automatically.
See [Render Free limitations](https://render.com/docs/free).

The bilingual notice says this is an evolving learning project with temporary
progress. It appears in the cover's About area, before nickname entry, and on
lessons, practice, quizzes/results and My Progress. No JavaScript is needed to
read it. The existing cover hero, animation and learning logic are unchanged.

The **12-hour** signed-cookie/form-token window remains, with cookies renewed
by successful learning requests. A separate **30-minute server-side inactivity
limit** (`LWF_VISIT_IDLE_SECONDS=1800`) controls access to visit data. End Visit and
Start New Visit delete the current visit's records transactionally. Startup and
later learning/visit requests remove expired visits before activity renewal.
A stable secret cannot recover deleted visits or lost temporary storage. Missing
or expired identities return safely to name entry; matching names never recover
or share progress. Cleanup can be delayed while Render sleeps. Browser closure,
background tabs, static/health checks and local answer selection are not learning
requests. See [the technical retention notes](TEMPORARY-VISITS.md).

Use a **fresh empty runtime database** for this candidate. Existing schema-3 files
are refused without modification; there is no silent migration. No original
visitor database or backup is upgraded or copied by this work.

There is no backup/recovery guarantee for this disposable demonstration and no
paid backup service to configure. Original local backups remain protected. Any
future durable hosting or backup workflow needs separate approval.

## Essential before public launch

The locally integrated legal documents are `/privacy/` (English/German) and
`/impressum/`. Francis has confirmed the operator/contact details and approved
local integration. The notices now describe the approved Option B deletion and
30-minute inactivity behavior, including delayed cleanup and temporary storage.
They are accessible before a visit and from the existing application pages.
See [the current legal review record](PRIVACY-REVIEW.md).

1. Confirm actual provider-account arrangements: Render's applicable processing
   agreement, transfer safeguards and log handling/retention. Keep the already
   approved Frankfurt/Free settings. Seven-day Hobby dashboard availability does
   not prove secure deletion of every provider copy. The account-specific iCloud
   processing/transfer arrangements also remain unverified.
2. Perform the separately approved final release review. No repeat operator,
   address, noncommercial-purpose or technical-retention approval is needed. Local
   legal integration is not a certification of provider compliance or permission
   to commit, push or deploy. No additional paid service is introduced.

3. With approval, push only the reviewed manifest to personal `origin/main`, then
   create the **Free** service with no disk/add-ons. Check the dashboard says Free
   before deploying. No purchase or resource creation is authorised yet.
4. After deployment approval, check public HTTPS, trusted hostname, health, both
   languages, a fresh visitor, all learning features and confirmation protection.
   Explain cold start and storage-loss behavior to reviewers. Obtain Francis's
   live review; local tests cannot verify Render's actual public service.

Legal references: [German DDG §5](https://www.gesetze-im-internet.de/ddg/__5.html)
(applies within its statutory scope), [German media-law information requirements](https://www.die-medienanstalten.de/aufgaben/aufsicht/impressumspflicht/), and [European Commission data-information obligations](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/obligations_en).
This checklist is not a legal compliance certification. Free educational hosting
alone does not settle Impressum or data-protection applicability.

Technical references checked 23 October 2026:
[Blueprint specification](https://render.com/docs/blueprint-spec),
[Flask deployment](https://render.com/docs/deploy-flask),
[Python runtime](https://render.com/docs/python-version).
Preserve the local third-party icon notices. The overall software-license decision
remains separate; no new external assets or services are added here.
