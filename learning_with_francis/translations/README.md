# Translation maintenance

L1 translates the cover; L2 translates the shared interface and errors; L3 adds
the SQL lesson, questions, explanations, topic titles and personalized feedback.
L4 extends the same approach to Python, JavaScript and SAP.
English is the original
message text and fallback, so no duplicate English catalog is necessary. German
translations are in `de/LC_MESSAGES/messages.po`; `messages.mo` is the compiled
runtime asset. Include both when reviewing or releasing a translation change.
The `.pot` file lists extracted source messages, without user data or credentials.
All four subjects support both languages after L4 implementation. L5 remains a
separate final verification milestone, not started by milestone regression checks.

From the project root, after installing `requirements.txt`:

```sh
.venv/bin/pybabel extract -F babel.cfg --project 'Learning with Francis' --copyright-holder 'Francis Furio' -o learning_with_francis/translations/messages.pot .
.venv/bin/pybabel update -i learning_with_francis/translations/messages.pot -d learning_with_francis/translations
# Edit/review German msgstr entries, resolving any fuzzy (uncertain) translations.
.venv/bin/pybabel compile -d learning_with_francis/translations
```

Restart the local development server after catalog changes. Run the Python suite;
its catalog check rejects missing/fuzzy translations or out-of-date compiled text.
Browser checks also verify actual translated output and language selection.

Use `gettext("Message")` in Python and `{{ _('Message') }}` in Jinja templates.
Use named placeholders for variable text and `ngettext` for quantities when needed;
do not translate identifiers, SQL/Python/JavaScript syntax or stored status values.
Jinja keeps normal HTML escaping. Do not mark user-controlled text as safe HTML.

A future language can have its own catalog, then join the explicit supported-locale
list after review. Locale strings from requests are never used as file paths.
Native POST controls avoid JavaScript state or a second language cookie.


L2 templates call `status_label` for display but retain canonical form values and
data attributes. The Version 2 progress script reads its confirmation message from
escaped `data-confirmation-message` HTML. The original Version 1 script is unchanged.
Required-input hints use the same HTML-driven approach. No second JavaScript
translation dictionary is needed.

Shared language controls include signed return tokens. Native language buttons
belong to the current name/activity form and use `formaction`/`formnovalidate`.
The language handler accepts only bounded draft fields, never submitted scores;
quiz tokens are revalidated by the existing handler before use. A one-time draft
is restored only for its visit and destination. No database migration is needed.


SQL uses Babel's standard `N_` extraction marker in `sql_content.py`; L4 adds
the same marker to `subjects.py`. This local
identity function returns English source strings and never translates stored or
graded data. `sql_display.py` calls gettext only for view copies. Technical query
choices and identifiers are not marked as prose. Keep question IDs, answer keys,
content versions and SQL example values stable during translation review.

The result view matches the topic as well as an exact known
prompt/choices/explanation snapshot; question IDs repeat between subjects. It
translates matching snapshots only;
unknown historical wording falls back to English with an explanatory notice.
Never change saved snapshots merely to make a translation appear. Personalized
feedback for all subjects uses named placeholders and normal Jinja escaping.
