"""L2 browser verification: disposable current-schema, native bilingual forms and progress."""

from retention_support import learning_snapshot

import argparse
from contextlib import closing
import json
from pathlib import Path
import tempfile
from threading import Thread

from werkzeug.serving import make_server
from learning_with_francis import create_app, db
from learning_with_francis.subjects import SUBJECTS


def run(report_dir):
    from playwright.sync_api import sync_playwright, expect
    report_dir.mkdir(parents=True, exist_ok=True)
    groups, errors = [], []
    with tempfile.TemporaryDirectory(prefix='l2-interface-browser-', dir='/tmp') as directory:
        path = Path(directory) / 'learning.db'
        db.initialize_database(path)
        app = create_app({'TESTING': True, 'DATABASE': str(path), 'SECRET_KEY': 'disposable-l2-browser-key'})
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'

        def observe(page):
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: errors.append(f'{response.status} {response.url}')
                    if response.status >= 500 else None)
            page.on('console', lambda message: errors.append(message.text)
                    if message.type == 'error' and 'Failed to load resource' not in message.text else None)

        def language(page, code):
            with page.expect_response(lambda response: response.url == base+'/preferences/language'
                                      and response.request.method == 'POST') as posted:
                page.get_by_role('button', name='Deutsch' if code=='de' else 'English', exact=True).click()
            assert posted.value.status == 303
            expect(page.locator('html')).to_have_attribute('lang', code)

        def rows(sql, args=()):
            with closing(db.open_database(path)) as connection:
                return [tuple(row) for row in connection.execute(sql, args)]

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(reduced_motion='reduce', viewport={'width': 1440,'height': 1000})
                    page = context.new_page();observe(page)
                    page.goto(base+'/learn/')
                    expect(page.get_by_label('Your name', exact=True)).to_be_visible()
                    page.get_by_label('Your name', exact=True).fill('Interface Learner')
                    before = learning_snapshot(path)
                    language(page, 'de')
                    expect(page.get_by_label('Dein Name', exact=True)).to_have_value('Interface Learner')
                    expect(page.get_by_role('heading', name='Beginne deinen Lernbesuch',exact=True)).to_be_visible()
                    assert learning_snapshot(path) == before
                    groups.append('English default; German welcome, native language form and pending name preserved without visitor/activity writes')

                    page.get_by_label('Dein Name', exact=True).fill('')
                    page.get_by_label('Dein Name', exact=True).press('Enter')
                    assert page.get_by_label('Dein Name', exact=True).evaluate('el => el.validationMessage') == 'Bitte gib deinen Namen ein.'
                    page.get_by_label('Dein Name', exact=True).fill('Interface Learner')
                    page.get_by_label('Dein Name', exact=True).press('Enter')
                    expect(page.get_by_role('heading', name='Willkommen bei Learning with Francis, Interface Learner!')).to_be_visible()
                    page.get_by_role('link', name='Mein Fortschritt', exact=True).click()
                    expect(page.get_by_role('heading', name='Mein Fortschritt', exact=True)).to_be_visible()
                    expect(page.locator('#total-practice')).to_have_text('0')
                    expect(page.locator('#total-quizzes')).to_have_text('0')
                    expect(page.locator('#status-history tbody tr')).to_have_count(4)
                    assert all('Besuch begonnen' in row.inner_text() for row in page.locator('#status-history tbody tr').all())
                    groups.append('German required-name validation, personalized greeting, zero counts, four initial history entries and progress navigation')

                    filter_control=page.locator('#topic-filter')
                    for status in ('Completed','Needs Review'):
                        filter_control.select_option(status)
                        expect(page.locator('#filter-empty-message')).to_have_text('Keine Themen entsprechen diesem Filter')
                        expect(page.locator('#filter-empty-message')).to_be_visible()
                    filter_control.select_option('Still Learning')
                    expect(page.locator('.topic-row:visible')).to_have_count(4)
                    filter_control.select_option('All')
                    row=page.locator('[data-subject="sql"]')
                    row.locator('[name="new_status"]').select_option('Completed')
                    before=learning_snapshot(path)
                    row.get_by_role('button',name='Speichern',exact=True).click()
                    expect(row.locator('.confirmation-error')).to_have_text('Bitte bestätige, dass du dieses Thema verstanden hast.')
                    assert learning_snapshot(path)==before
                    expect(row.locator('[name="user_confirmed"]')).not_to_be_checked()
                    row.locator('[name="user_confirmed"]').check()
                    row.get_by_role('button',name='Speichern',exact=True).click()
                    expect(row.locator('.saved-status')).to_contain_text('Abgeschlossen')
                    expect(row.locator('.saved-status')).to_contain_text('Bestätigt')
                    expect(row.locator('[name="user_confirmed"]')).not_to_be_checked()
                    row.locator('[name="new_status"]').select_option('Needs Review')
                    row.get_by_role('button',name='Speichern',exact=True).click()
                    expect(row.locator('.saved-status')).to_have_text('Wiederholung nötig')
                    expect(page.locator('#status-history tbody tr')).to_have_count(6)
                    groups.append('All translated filters, no-match message, JS confirmation warning, explicit completion and reversible status history')

                    saved=learning_snapshot(path)
                    language(page,'en')
                    expect(row.locator('.saved-status')).to_have_text('Needs Review')
                    language(page,'de')
                    assert learning_snapshot(path)==saved
                    for width,height in ((320,700),(375,812),(768,1024),(844,390),(1440,1000)):
                        page.set_viewport_size({'width':width,'height':height})
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
                        expect(page.get_by_role('button', name='Deutsch', exact=True)).to_be_visible()
                    page.set_viewport_size({'width':375,'height':812})
                    page.add_style_tag(content=':root { font-size: 200%; }')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    page.screenshot(path=str(report_dir/'german-progress-mobile-enlarged.png'),full_page=True)
                    page.reload()
                    page.set_viewport_size({'width':1440,'height':1000})
                    page.screenshot(path=str(report_dir/'german-progress-desktop.png'),full_page=True)
                    page.keyboard.press('Tab')
                    expect(page.get_by_role('button',name='English',exact=True)).to_be_focused()
                    assert page.get_by_role('button',name='English',exact=True).evaluate('el => getComputedStyle(el).outlineStyle')=='solid'
                    assert learning_snapshot(path)==saved
                    groups.append('Saved status/history survive switching both ways; German desktop/mobile/landscape/200% text and keyboard focus remain usable')

                    for slug,subject in SUBJECTS.items():
                        page.goto(base+f'/{slug}/quiz')
                        questions=subject['content'].QUIZ
                        token=page.locator('.activity-form [name="submission_token"]').input_value()
                        for q in questions[:2]: page.locator(f'[name="{q["id"]}"][value="{q["correct"]}"]').check()
                        before=learning_snapshot(path)
                        language(page,'en')
                        expect(page).to_have_url(base+f'/{slug}/quiz')
                        for q in questions[:2]: expect(page.locator(f'[name="{q["id"]}"][value="{q["correct"]}"]')).to_be_checked()
                        assert page.locator('.activity-form [name="submission_token"]').input_value()==token
                        language(page,'de')
                        assert learning_snapshot(path)==before
                        for q in questions: page.locator(f'[name="{q["id"]}"][value="{q["correct"]}"]').check()
                        page.locator('.activity-form input[type=radio]:checked').last.press('Enter')
                        expect(page.locator('#score')).to_contain_text('5 von 5')
                        expect(page.get_by_text('Richtige Antwort:',exact=False).first).to_be_visible()
                        result_url=page.url
                        saved=learning_snapshot(path)
                        language(page,'en')
                        expect(page).to_have_url(result_url)
                        expect(page.locator('#score')).to_contain_text('5 out of 5')
                        language(page,'de')
                        assert learning_snapshot(path)==saved
                    assert rows("SELECT COUNT(*) FROM learning_attempts WHERE activity_kind='quiz'")==[(4,)]
                    assert set(rows("SELECT DISTINCT learning_status FROM topic_progress"))=={('Needs Review',),('Still Learning',)}
                    groups.append('All four subject quiz drafts survive both languages with the same token; one real saved attempt per quiz, translated score/results and unchanged understanding')

                    page.goto(base+'/sql/practice')
                    for position,q in enumerate(SUBJECTS['sql']['content'].PRACTICE):
                        expect(page.locator('#practice-progress')).to_have_text(f'Frage {position+1} von 10')
                        option=q['correct'] if position!=1 else next(k for k in q['choices'] if k!=q['correct'])
                        page.locator(f'[name="{q["id"]}"][value="{option}"]').check()
                        if position==1:
                            saved=learning_snapshot(path)
                            language(page,'en')
                            expect(page.locator('#practice-progress')).to_have_text('Question 2 of 10')
                            expect(page.locator(f'[name="{q["id"]}"][value="{option}"]')).to_be_checked()
                            language(page,'de')
                            assert learning_snapshot(path)==saved
                        page.get_by_role('button',name='Antwort überprüfen',exact=True).click()
                        expect(page.get_by_text('Richtige Antwort:',exact=False)).to_be_visible()
                        expect(page.locator('.answer-result strong')).to_have_text('Falsch' if position==1 else 'Richtig')
                        saved=learning_snapshot(path);page.reload();assert learning_snapshot(path)==saved
                        page.get_by_role('link',name='Nächste Frage' if position<9 else 'Übung beenden',exact=True).click()
                    expect(page.get_by_role('heading',name='Übungsrunde abgeschlossen!',exact=True)).to_be_visible()
                    page.get_by_role('link',name='Erneut üben',exact=True).click()
                    expect(page.locator('#practice-progress')).to_have_text('Frage 1 von 10')
                    assert rows("SELECT COUNT(*) FROM learning_attempts WHERE activity_kind='practice'")==[(10,)]
                    groups.append('Ten-question practice, immediate correct/incorrect results, draft/round preservation, Next/Finish/restart controls and no refresh duplicates')

                    other_context=browser.new_context(java_script_enabled=False)
                    other=other_context.new_page();observe(other)
                    other.goto(base+'/learn/')
                    language(other,'de')
                    other.get_by_label('Dein Name',exact=True).fill('Interface Learner')
                    other.get_by_label('Dein Name',exact=True).press('Enter')
                    other.goto(base+'/progress/')
                    expect(other.locator('#total-quizzes')).to_have_text('0')
                    expect(other.locator('#total-practice')).to_have_text('0')
                    expect(other.locator('#status-history tbody tr')).to_have_count(4)
                    other_row=other.locator('[data-subject="sql"]')
                    other_row.locator('[name="new_status"]').select_option('Completed')
                    before=learning_snapshot(path)
                    other_row.get_by_role('button',name='Speichern',exact=True).click()
                    expect(other.locator('.visit-error')).to_contain_text('Bitte bestätige')
                    assert learning_snapshot(path)==before
                    other.goto(result_url)
                    expect(other.get_by_role('heading',name='Fehler bei der Anfrage 404')).to_be_visible()
                    groups.append('Same-name second visitor starts with zero activity and private history; Python rejects unconfirmed completion without JS; foreign results stay inaccessible')

                    other.goto(base+'/python/quiz')
                    q=SUBJECTS['python']['content'].QUIZ[0]
                    other.locator(f'[name="{q["id"]}"][value="{q["correct"]}"]').check()
                    before=learning_snapshot(path)
                    language(other,'en')
                    expect(other.locator(f'[name="{q["id"]}"][value="{q["correct"]}"]')).to_be_checked()
                    language(other,'de')
                    assert learning_snapshot(path)==before
                    other.get_by_role('button',name='Neuen Besuch beginnen',exact=True).click()
                    expect(other.get_by_label('Dein Name',exact=True)).to_be_visible()
                    other.get_by_label('Dein Name',exact=True).fill('Interface Learner')
                    other.get_by_label('Dein Name',exact=True).press('Enter')
                    other.goto(base+'/progress/')
                    expect(other.locator('#total-quizzes')).to_have_text('0')
                    other.get_by_role('button',name='Besuch beenden',exact=True).click()
                    expect(other.get_by_text('Dein Besuch ist beendet.',exact=False)).to_be_visible()
                    expect(other.get_by_label('Dein Name',exact=True)).to_be_visible()
                    assert rows('SELECT COUNT(*) FROM learning_attempts')==[(14,)]
                    groups.append('Without JavaScript: draft-preserving language controls, fresh New Visit, retained German, End Visit feedback and preserved old activity')
                    other_context.close();context.close()
                    assert not errors,errors
                finally: browser.close()
        finally:
            server.shutdown();thread.join();server.server_close()
    assert not Path(directory).exists()
    report={'passed_groups':groups,'errors':errors,'disposable_database_removed':True}
    (report_dir/'interface-browser-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir',type=Path,required=True)
    run(parser.parse_args().report_dir)
