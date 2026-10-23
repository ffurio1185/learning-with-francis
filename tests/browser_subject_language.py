"""L4 English/German browser flows; disposable current-schema only."""

from retention_support import learning_snapshot
import argparse
from contextlib import closing
import json
from pathlib import Path
import tempfile
from threading import Thread

from werkzeug.serving import make_server
from itsdangerous import URLSafeTimedSerializer
from learning_with_francis import create_app, db
from learning_with_francis.subjects import SUBJECTS

SLUGS = ('python', 'javascript', 'sap')
TITLES = {'python': 'Variablen und einfache Funktionen', 'javascript': 'Werte, DOM-Elemente und Ereignisse', 'sap': 'ERP-Grundlagen und Geschäftsprozessbeispiele'}
HEADINGS = {'python': '1. Werten einen Namen geben', 'javascript': '1. Werte und Variablenbindungen', 'sap': '1. Vernetzte Geschäftsinformationen'}


def run(report_dir):
    from playwright.sync_api import sync_playwright, expect
    report_dir.mkdir(parents=True, exist_ok=True)
    groups, errors = [], []
    with tempfile.TemporaryDirectory(prefix='l4-subject-browser-', dir='/tmp') as directory:
        path = Path(directory) / 'learning.db'; db.initialize_database(path)
        app = create_app({'TESTING': True, 'DATABASE': str(path), 'SECRET_KEY': 'disposable-l4-browser-key'})
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}'

        def observe(page):
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: errors.append(f'{response.status} {response.url}') if response.status >= 500 else None)
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' and 'Failed to load resource' not in message.text else None)

        def language(page, code):
            with page.expect_response(lambda r: r.request.method == 'POST' and r.url == base + '/preferences/language') as response:
                page.get_by_role('button', name='Deutsch' if code == 'de' else 'English', exact=True).click()
            assert response.value.status == 303
            expect(page.locator('html')).to_have_attribute('lang', code)

        def rows(sql, args=()):
            with closing(db.open_database(path)) as connection:
                return [tuple(row) for row in connection.execute(sql, args)]

        def fit(page):
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(reduced_motion='reduce', viewport={'width':1440, 'height':1000})
                    page = context.new_page(); observe(page)
                    page.goto(base + '/learn/')
                    page.get_by_label('Your name', exact=True).fill('Subject Learner')
                    page.get_by_label('Your name', exact=True).press('Enter')
                    urls = []
                    for slug in SLUGS:
                        subject = SUBJECTS[slug]; content = subject['content']
                        page.goto(base + f'/{slug}/')
                        language(page, 'en')
                        expect(page.get_by_role('heading', name=f'{subject["name"]}: {subject["title"]}', exact=True)).to_be_visible()
                        codes = page.locator('pre code').all_text_contents()
                        before = learning_snapshot(path); language(page, 'de')
                        expect(page.get_by_role('heading', name=f'{subject["name"]}: {TITLES[slug]}', exact=True)).to_be_visible()
                        expect(page.get_by_role('heading', name=HEADINGS[slug], exact=True)).to_be_visible()
                        expect(page.locator('.lesson-material')).to_have_attribute('lang', 'de')
                        expect(page.locator('.interface-scope')).to_have_count(0)
                        assert codes == page.locator('pre code').all_text_contents()
                        assert learning_snapshot(path) == before
                        page.screenshot(path=str(report_dir / f'{slug}-lesson-german-desktop.png'), full_page=True)
                        page.goto(base + '/progress/')
                        expect(page.locator(f'[data-subject="{slug}"] .topic-title')).to_have_text(TITLES[slug])
                        expect(page.locator(f'[data-subject="{slug}"] .saved-status')).to_have_text('Noch am Lernen')
                        groups.append(f'{slug}: English/German lesson, title and zero-activity status; literal code/examples unchanged; language switch does not write SQLite')

                        page.goto(base + f'/{slug}/practice')
                        for index, q in enumerate(content.PRACTICE):
                            expect(page.locator('#practice-progress')).to_have_text(f'Frage {index+1} von 10')
                            assert page.locator('.activity-form legend').inner_text() != q['prompt']
                            expect(page.locator('.activity-form fieldset')).to_have_count(1)
                            expect(page.locator('.answer-result')).to_have_count(0)
                            option = q['correct'] if index % 2 == 0 else next(k for k in q['choices'] if k != q['correct'])
                            page.locator(f'[name="{q["id"]}"][value="{option}"]').check()
                            if index == 3:
                                before = learning_snapshot(path); token = page.locator('[name="submission_token"]').input_value()
                                language(page, 'en')
                                expect(page.locator('#practice-progress')).to_have_text('Question 4 of 10')
                                expect(page.locator(f'[name="{q["id"]}"][value="{option}"]')).to_be_checked()
                                language(page, 'de')
                                # Practice signatures may receive a fresh timestamp; the visit/round/position must stay identical.
                                serializer = URLSafeTimedSerializer(app.secret_key, salt='sql-activity-submission')
                                assert serializer.loads(page.locator('[name="submission_token"]').input_value()) == serializer.loads(token)
                                assert learning_snapshot(path) == before
                            page.get_by_role('button', name='Antwort überprüfen', exact=True).click()
                            expect(page.locator('.answer-result strong')).to_have_text('Richtig' if index % 2 == 0 else 'Falsch')
                            expect(page.locator('#personal-feedback')).to_contain_text('richtig gelöst' if index % 2 == 0 else 'Lies die Erklärung')
                            expect(page.locator('.answer-result h2')).to_have_attribute('lang', 'de')
                            assert q['explanation'] not in page.locator('.answer-result').inner_text()
                            expect(page.get_by_text('Richtige Antwort:', exact=False)).to_be_visible()
                            before = learning_snapshot(path); page.reload(); assert learning_snapshot(path) == before
                            page.get_by_role('link', name='Nächste Frage' if index < 9 else 'Übung beenden', exact=True).click()
                        expect(page.get_by_role('heading', name='Übungsrunde abgeschlossen!', exact=True)).to_be_visible()
                        page.get_by_role('link', name='Erneut üben', exact=True).click()
                        expect(page.locator('#practice-progress')).to_have_text('Frage 1 von 10')
                        assert rows('SELECT COUNT(*), SUM(score) FROM learning_attempts WHERE topic_id=? AND activity_kind=?', (content.TOPIC_ID, 'practice')) == [(10, 5)]
                        groups.append(f'{slug}: all ten practice prompts, options and immediate explanations; correct/incorrect checks, drafts, Next/Finish/restart, unlimited rounds and no refresh duplicates')

                        for score in (0, 2, 3, 4, 5):
                            page.goto(base + f'/{slug}/quiz')
                            expect(page.locator('.activity-form fieldset')).to_have_count(5)
                            expect(page.locator('.answer-result')).to_have_count(0)
                            assert all(q['explanation'] not in page.content() for q in content.QUIZ)
                            for index, q in enumerate(content.QUIZ):
                                option = q['correct'] if index < score else next(k for k in q['choices'] if k != q['correct'])
                                page.locator(f'[name="{q["id"]}"][value="{option}"]').check()
                            if score == 3:
                                token = page.locator('[name="submission_token"]').input_value(); before = learning_snapshot(path)
                                language(page, 'en'); language(page, 'de')
                                assert page.locator('.activity-form input:checked').count() == 5
                                assert page.locator('[name="submission_token"]').input_value() == token
                                assert learning_snapshot(path) == before
                            page.locator('.activity-form input:checked').last.press('Enter')
                            expect(page.locator('#score')).to_contain_text(f'{score} von 5')
                            expect(page.locator('#personal-feedback')).to_contain_text('Übe weiter' if score <= 2 else 'Quiz bestanden' if score < 5 else 'Volle Punktzahl')
                            expect(page.locator('#personal-feedback')).to_contain_text('Subject Learner!')
                            expect(page.locator('.answer-result')).to_have_count(5)
                            expect(page.locator('.correct-answer')).to_have_count(score)
                            saved = learning_snapshot(path); page.reload(); assert learning_snapshot(path) == saved
                            expect(page.get_by_role('link', name='Erneut versuchen', exact=True)).to_be_visible()
                        url = page.url; urls.append(url); before = learning_snapshot(path)
                        language(page, 'en')
                        expect(page.locator('#personal-feedback')).to_contain_text('Congratulations, Subject Learner!')
                        expect(page.locator('.answer-result h2').first).to_have_text(content.QUIZ[0]['prompt'])
                        language(page, 'de'); assert learning_snapshot(path) == before
                        assert rows('SELECT prompt,explanation FROM learning_answers WHERE attempt_id=? ORDER BY position', (url.rsplit('/', 1)[1],)) == [(q['prompt'],q['explanation']) for q in content.QUIZ]
                        assert rows('SELECT score FROM learning_attempts WHERE topic_id=? AND activity_kind=? ORDER BY rowid', (content.TOPIC_ID, 'quiz')) == [(0,), (2,), (3,), (4,), (5,)]
                        assert rows('SELECT DISTINCT learning_status FROM topic_progress') == [('Still Learning',)]
                        groups.append(f'{slug}: five-question quiz, hidden answers until submission, low/pass/perfect feedback, retries, Enter submission, draft identity and read-only saved result translation; canonical records and no automatic completion')

                        for target in (base + f'/{slug}/', url, base + f'/{slug}/quiz'):
                            page.goto(target)
                            for width, height in ((320,700), (375,812), (768,1024), (844,390)):
                                page.set_viewport_size({'width':width,'height':height}); fit(page)
                            page.set_viewport_size({'width':375,'height':812})
                            page.add_style_tag(content=':root { font-size: 200%; }'); fit(page)
                        page.screenshot(path=str(report_dir / f'{slug}-quiz-german-mobile-enlarged.png'), full_page=True)
                        page.get_by_role('button', name='Deutsch', exact=True).focus()
                        expect(page.get_by_role('button', name='Deutsch', exact=True)).to_be_focused()
                        assert page.get_by_role('button', name='Deutsch', exact=True).evaluate('el => getComputedStyle(el).outlineStyle') == 'solid'
                        page.set_viewport_size({'width':1440,'height':1000})
                        groups.append(f'{slug}: German lesson/quiz/results fit desktop, phone, tablet, landscape and 200% text; keyboard focus retained')

                    page.goto(base + '/progress/')
                    expect(page.locator('#total-practice')).to_have_text('30')
                    expect(page.locator('#total-exercises')).to_have_text('15')
                    expect(page.locator('#total-quizzes')).to_have_text('15')
                    expect(page.locator('#status-history tbody tr')).to_have_count(4)
                    assert page.locator('time').count() > 4
                    groups.append('Cross-subject tracker totals are 30 practice, 15 correct exercises and 15 quiz attempts; all four statuses unchanged, dated history retained')

                    other_context = browser.new_context(java_script_enabled=False)
                    other = other_context.new_page(); observe(other)
                    other.goto(base + '/learn/')
                    other.get_by_label('Your name', exact=True).fill('Subject Learner')
                    other.get_by_label('Your name', exact=True).press('Enter')
                    other.goto(base + '/progress/')
                    expect(other.locator('#total-quizzes')).to_have_text('0')
                    expect(other.locator('#total-practice')).to_have_text('0')
                    for url in urls:
                        other.goto(url)
                        expect(other.get_by_role('heading', name='Request error 404', exact=True)).to_be_visible()
                    other.goto(base + '/python/quiz'); language(other, 'de')
                    for slug in SLUGS:
                        other.goto(base + f'/{slug}/quiz')
                        q = SUBJECTS[slug]['content'].QUIZ[0]
                        other.locator(f'[name="{q["id"]}"][value="{q["correct"]}"]').check()
                        before = learning_snapshot(path); language(other, 'en'); language(other, 'de')
                        expect(other.locator(f'[name="{q["id"]}"][value="{q["correct"]}"]')).to_be_checked()
                        assert learning_snapshot(path) == before
                        for q in SUBJECTS[slug]['content'].QUIZ:
                            other.locator(f'[name="{q["id"]}"][value="{q["correct"]}"]').check()
                        other.locator('.activity-form input:checked').last.press('Enter')
                        expect(other.locator('#personal-feedback')).to_contain_text('Herzlichen Glückwunsch, Subject Learner!')
                        other.goto(base + '/progress/')
                        row = other.locator(f'[data-subject="{slug}"]')
                        expect(row.locator('.saved-status')).to_have_text('Noch am Lernen')
                        row.locator('[name="new_status"]').select_option('Completed')
                        before = learning_snapshot(path); row.get_by_role('button',name='Speichern',exact=True).click()
                        expect(other.locator('.visit-error')).to_contain_text('Bitte bestätige')
                        assert learning_snapshot(path) == before
                        row.locator('[name="new_status"]').select_option('Completed')
                        row.locator('[name="user_confirmed"]').check()
                        row.get_by_role('button',name='Speichern',exact=True).click()
                        expect(row.locator('.saved-status')).to_contain_text('Abgeschlossen')
                        row.locator('[name="new_status"]').select_option('Needs Review')
                        row.get_by_role('button',name='Speichern',exact=True).click()
                        expect(row.locator('.saved-status')).to_have_text('Wiederholung nötig')
                    page.reload()
                    expect(page.locator('#total-quizzes')).to_have_text('15')
                    expect(page.locator('.saved-status',has_text='Noch am Lernen')).to_have_count(4)
                    groups.append('Separate same-name visitor has zero/private activity; all three German quizzes and draft switches work without JS, Python requires personal confirmation, reversal works and first visitor stays unchanged')
                    other_context.close(); context.close(); assert not errors, errors
                finally: browser.close()
        finally: server.shutdown(); thread.join(); server.server_close()
    assert not Path(directory).exists()
    report = {'passed_groups':groups,'errors':errors,'disposable_database_removed':True}
    (report_dir / 'subject-language-browser-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir',type=Path,required=True)
    run(parser.parse_args().report_dir)
