# Public release candidate

This is a local, uncommitted release candidate. No push, resource purchase or
deployment is authorised by preparing it.

## Source and publishing destination

- Personal repository: https://github.com/ffurio1185/learning-with-francis
- Future destination: `origin/main`, after approval of the exact commit and push.
- Clean history starts at published `dbeae6f7549da79d0b0aab172e2efcde2e3aa1fe`.
- Approved application files come from snapshot `37e712f`, including bilingual
  L1–L5 functionality and the approved cover/About/button enhancement.
- No music-bearing commit is imported. Do not merge or push the other local
  feature branch into this release: its history is deliberately kept separate.
- There are no audio assets or players in this candidate. The original approved
  local music experience remains untouched in its own repository/branch.

## Prepared runtime

Render settings are in `render.yaml`: one paid web instance in Frankfurt, 1 GB
persistent disk mounted at `/var/data`, automatic deploys off. This file creates
nothing until the owner explicitly connects/applies it in Render.

Use `pip install -r requirements.txt` to build, then `sh render-start.sh` to start.
The start script validates or initialises the fresh schema-3 database at runtime,
then starts Gunicorn on `$PORT`. It never resets or upgrades an existing database.
Do not use `gunicorn app:app`: root `app.py` is the preserved Version 1 tracker.

The production entry point needs `LWF_DATA_DIR` and a stable random `LWF_SECRET_KEY`
outside Git. Render can generate the secret once; retain it across redeploys.
Host validation uses `RENDER_EXTERNAL_HOSTNAME` on Render; custom domains require
explicit comma-separated `LWF_ALLOWED_HOSTS`. Production cookies are Secure,
HttpOnly and SameSite=Lax. Render must provide HTTPS. No arbitrary proxy headers
are trusted by the application. `/healthz` checks the expected database.

The existing 12-hour session and signed form-token behavior is unchanged. This is
not a new absolute visit-age guarantee or a promise of cross-browser recovery.
Names do not retrieve old results. End/New Visit revokes previous access while
retaining records; closing a browser may restore a session. No automatic cleanup
or seven-day session setting has been introduced.

Only curriculum metadata is initialised: four subjects and four topics, with zero
visits, attempts, answers, progress rows or status-history rows. Actual activity
starts with a visitor's own new visit. Do not upload local or preview databases.
The real production disk will exist only after an authorised Render deployment.

## Required before public deployment

1. Supply and approve the real operator/contact details and English/German
   Impressum/privacy information, accessible before collecting visitor data.
   Do not put private correspondence, unnecessary contact details or secrets in Git.
2. Agree the public-data retention and privacy-request procedure; the earlier
   30-day/7-day/30-day suggestions were preliminary and are not implemented here.
   The current program retains old rows. Do not publish a notice claiming otherwise.
3. Approve the actual hosting/backup bill and processor terms. Current illustrative
   base is about US$7/month compute + US$0.25/month for a 1 GB disk, before tax,
   external backups and usage extras; US$10 is a target, not a guaranteed cap.
4. Arrange consistent, encrypted off-disk backups and a successful restore test.
   Use SQLite's online backup API, not an uncoordinated live-file copy. An unrelated
   Render cron service cannot mount the web service's private disk. Define an
   affordable schedule/destination before promising recovery times. Keep encryption
   keys separately and reapply deletions/revocations if recovering older data.

These are deployment prerequisites, not reasons to rebuild approved learning
features. Operator details and live-service decisions remain under Francis's
control. No legal compliance, completed backup service or live persistence is
claimed by this local technical preparation.

## Verification and publishing procedure

1. Review `docs/PUBLISH-FILES.txt` and the local verification report. Only these
   files are intended for the candidate commit. Databases, keys, visitor records,
   reports and environments stay outside the source tree or ignored.
2. With explicit authorisation, create a new release commit on the clean candidate
   branch using the repository-local noreply author identity. Review its full tree
   and every reachable commit/object. Never add the private feature branch or tags.
3. Recheck the live remote `main`. If it has changed from `dbeae6f`, stop and review
   instead of force-pushing. After approval, push the exact reviewed candidate commit
   to `refs/heads/main` without force. No push is authorised yet.
4. Only after deployment approval, apply Render settings, configure secrets and
   initialise fresh production storage. Confirm HTTPS, cookie behavior and health.
5. Verify a fictional new visit, all subjects, bilingual forms, scoring, personal
   completion confirmation and persistence through a controlled service restart
   and redeploy. Check real backup success/restore and obtain Francis's live review.

Source references checked during preparation:
[Render Flask](https://render.com/docs/deploy-flask),
[disks](https://render.com/docs/disks),
[Blueprint fields](https://render.com/docs/blueprint-spec),
[Python runtime](https://render.com/docs/python-version),
[pricing](https://render.com/pricing), and
[Flask configuration](https://flask.palletsprojects.com/en/stable/config/).

The application's own software-license choice remains separate from the existing
third-party icon notices. Public repository availability alone is not a software
license. Preserve those notices in any release.
