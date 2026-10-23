# Legal documents — final local integration

Francis approved the confirmed operator/contact details and final local integration
of the German Datenschutzerklärung, English Privacy Policy and German Impressum.
No repeat identity, address, noncommercial-purpose, Frankfurt/Free or Option B
approval is required. Option B's 252 Python/SQLite tests and 83 browser groups are
accepted. No commit, push, merge or deployment is authorised.

## Integrated documents and verified scope

- `/privacy/` uses the existing English/German language preference. `/impressum/`
  adds the confirmed provider details, with readable English/German presentation.
  A shared contact partial keeps the confirmed details consistent without copying
  them into this research record. Both pages are public within the local app,
  database independent, linked before name entry and on existing application pages.
- The notices describe nicknames/random visit ownership, submitted answers/scores,
  statuses/confirmations, the signed (not encrypted) session cookie, and temporary
  SQLite. End/new visit deletion and transaction boundaries follow approved code.
  Thirty minutes is an inactivity/access cutoff; cleanup occurs at startup/later
  learning or visit requests and may be delayed during Render sleep. Browser close
  is not a reliable deletion event. The cookie's renewed 12-hour signature window
  is distinct from inactivity and form-token limits. No automatic email deletion,
  provider-log deletion or physical-storage erasure is promised.
- The legal basis is the documented Article 6(1)(f) GDPR assessment: voluntary
  educational service/security, limited visit-owned data, no account/advertising
  profile, explicit deletion and idle expiry, with visitor rights and safeguards.
  Necessary session/security and requested-language storage are assessed separately
  under §25(2)(2) TDDDG. Personal completion confirmation is never privacy consent.
  This records an operator-facing assessment, not a regulator's compliance ruling.
- Contact correspondence is outside SQLite; the notice states its purpose and
  retention criteria, the need for manual mailbox management and the confirmed
  iCloud mailbox's possible international processing. No automatic mail workflow
  or new service is created. No commercial tax/register details or extra identity
  requirements are invented for the simple educational Impressum.

## Only genuine external facts still unverified

1. **Render account:** applicability of the processing agreement to the actual Free
   account, the operative transfer safeguards and provider logging/retention. Render
   publishes a DPA incorporating transfer mechanisms and a subprocessor list; this
   is not evidence that an account was inspected or that every subprocessor handles
   every visit. Frankfurt is already confirmed and is not being reopened. No EU-only
   processing claim or guaranteed seven-day erasure of every provider copy is made.
2. **Mailbox account:** the confirmed iCloud address's account-specific provider
   terms and applicable processing/transfer arrangements have not been inspected.
   The application cannot determine provider retention or delete mail/backups.

These are account-level facts, not requests to supply previously confirmed personal
information. They are identified in the local notice and must be checked before
public launch. Published provider documents are sources, not proof of account
acceptance or an independent registry check. No new paid product is recommended.

## Current sources

Checked official Render DPA, security/subprocessor and logging text during this
integration. Render's DPA describes DPF where applicable and SCC fallback; its logs
page describes seven-day Hobby dashboard availability. Neither resolves all actual
account-level processing or retention. Apple publishes international-processing
information. Use these primary sources and retain applicable account evidence:

- [Render DPA](https://render.com/dpa), [terms](https://render.com/terms),
  [security/subprocessors](https://render.com/security),
  [logging](https://render.com/docs/logging), [Free storage](https://render.com/docs/free).
- [Apple privacy](https://www.apple.com/legal/privacy/en-ww/).
- [GDPR legal grounds — Commission](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/legal-grounds-processing-data_en),
  [necessary storage — §25 TDDDG](https://www.gesetze-im-internet.de/ttdsg/BJNR198210021.html),
  [§5 DDG](https://www.gesetze-im-internet.de/ddg/__5.html),
  [media-authority Impressum guidance](https://medienanstalt-rlp.de/fileadmin/dateien/medienvielfalt/Medienregulierung/Merkblaetter_intern/Leitfaden_Impressum.pdf),
  [Lower Saxony complaints](https://www.lfd.niedersachsen.de/beschwerde).

Final observed integration tests are recorded in PROJECT-PLAN.md. The earlier draft
record below is retained as history; its pending-identity and retained-ended-data
statements have been superseded and do not describe the integrated notice.

---

## Historical privacy-draft preparation record (superseded)

# Privacy Policy draft — operator review required

Prepared 23 October 2026 for the separate public-release application. The bilingual
page is `/privacy/`, using the existing English/German session language controls.
It is available without starting a visit or opening a learning database. It is a
review draft, not a claim of completed legal compliance or approval to publish.

## Details still needed from Francis

- Confirm the responsible operator/controller's full legal name. The existing
  creator credit is not treated as confirmation of legal identity.
- Approve a serviceable postal address for public display; no private address is
  inferred from local files or published. DCI is the training context, not an
  assumed operator or substitute contact address.
- Supply and approve a public email for contact/privacy requests.
- Review the proposed legitimate-interest basis and balancing of visitors' rights,
  actual retention criteria and a practical rights/deletion-request procedure.
- Review the applicable Render processing agreement, transfers/subprocessors and
  actual service/log settings before a public launch. No contract acceptance or
  claim of EU-only processing is made by implementing the page.

No invented identity, address, email or working request channel is presented.
The page explicitly identifies the pending items. No cookie-consent banner,
registration, data deletion, accounts or new learning behavior is introduced.
The Impressum remains a separate unfinished page; this task implements privacy only.

## Application facts checked

The Version 2 factory, visitor handlers, schema/migrations, grading, session/language
code and production configuration were inspected. Visit-owned SQLite rows store
nicknames, random identifiers, visit dates, answers, scores, status changes and
personal confirmations. A signed browser cookie carries visit/language/security
information and possible temporary drafts. Its signature is not encryption.
The existing 12-hour signature-age limit does not delete SQLite rows. End Visit
revokes access but retains rows; same-name visitors cannot recover earlier visits.
The application has no advertising/analytics tracker or external media embed.
Connection data processed by the hosting provider is distinct from the app schema,
which has no visitor IP-address field.

Free hosting uses ephemeral SQLite and can lose records. There is no guaranteed
retention, erasure time, secure-deletion guarantee, automated record cleanup or
promised recovery service. The draft says this explicitly. It does not claim that
ending a visit, closing a browser, 12-hour expiry or host restart securely deletes
all application/provider data. It does not introduce a seven-day or 30-day rule.

## Sources checked

- [GDPR information duties — European Commission](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/obligations_en).
- [Legal grounds and legitimate interests — European Commission](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/legal-grounds-processing-data_en?prefLang=ro).
- [Individual rights — European Commission](https://commission.europa.eu/law/law-topic/data-protection/information-individuals_en?prefLang=sk).
- [Necessary-device-storage exception, TDDDG §25](https://www.gesetze-im-internet.de/ttdsg/__25.html).
- [Render Free limitations](https://render.com/docs/free), [logging](https://render.com/docs/logging), [privacy](https://render.com/privacy) and [data-processing addendum](https://render.com/dpa).

Some direct Commission requests were rate-limited, and Render's legal landing
pages returned only their surrounding page text to the browser tool. Published
official search excerpts supplied the substantive Render DPA/Commission evidence.
No live Render account, data-processing contract or deployment settings were
inspected/changed. Provider terms and actual retention/transfer arrangements
remain operator review items; the draft does not assert that they are settled.

## Implementation and verification

The privacy template and shared navigation link reuse Babel and the existing
styles. The language-navigation allowlist includes only the new internal privacy
endpoint; CSRF, signature, ownership and external-redirect protections remain.
Links appear on the cover below its existing introduction, before name entry,
and on learning/results/progress/error pages. No cover hero, animation, question,
grading, status or database code was changed. The new route reads no database.

**225 Python/SQLite tests passed**, comprising the existing 215 and ten focused
privacy checks. The new cases cover default English/German rendering, absent
storage, page links before collection, no database writes, saved answers/statuses,
identity/isolation, End Visit, CSRF, redirect protection and production headers.
**73 Chromium browser groups passed**: all 68 existing groups plus five focused
privacy groups, including 16 English/German layout cases at 320/375/768/1440px
and 100%/200% text. Keyboard links/focus, no-JavaScript forms, stored quiz answers,
translated results, same-name isolation and Python completion protection passed.
There were no unexpected browser/server errors. Disposable databases were removed.
One initial new test used a URL that Flask redirects to its canonical trailing
slash; the test was corrected to check the actual 404 page. The cover test's
expected interactive-control count was updated solely for the added privacy link.
Python syntax and translation catalog checks passed. This is technical/browser
verification, not legal certification or a physical-device/screen-reader audit.
No commit, push, deployment, public contact disclosure or protected-record change
is authorised by this draft preparation.
