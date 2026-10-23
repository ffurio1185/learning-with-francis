"""L3 SQL browser checks using disposable current-schema data, never original records."""

from retention_support import learning_snapshot

import argparse
from contextlib import closing
import json
from pathlib import Path
import tempfile
from threading import Thread

from werkzeug.serving import make_server
from learning_with_francis import create_app, db, sql_content


def run(report_dir):
    from playwright.sync_api import sync_playwright, expect
    report_dir.mkdir(parents=True,exist_ok=True)
    groups,errors=[],[]
    with tempfile.TemporaryDirectory(prefix='l3-sql-browser-',dir='/tmp') as directory:
        path=Path(directory)/'learning.db';db.initialize_database(path)
        app=create_app({'TESTING':True,'DATABASE':str(path),'SECRET_KEY':'disposable-l3-browser-key'})
        server=make_server('127.0.0.1',0,app,threaded=True)
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'

        def observe(page):
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('response',lambda response:errors.append(f'{response.status} {response.url}') if response.status>=500 else None)
            page.on('console',lambda message:errors.append(message.text) if message.type=='error' and 'Failed to load resource' not in message.text else None)

        def language(page,code):
            with page.expect_response(lambda response: response.request.method=='POST' and response.url==base+'/preferences/language') as posted:
                page.get_by_role('button',name='Deutsch' if code=='de' else 'English',exact=True).click()
            assert posted.value.status==303
            expect(page.locator('html')).to_have_attribute('lang',code)

        def rows(sql):
            with closing(db.open_database(path)) as connection:return [tuple(row) for row in connection.execute(sql)]

        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True)
                try:
                    context=browser.new_context(reduced_motion='reduce',viewport={'width':1440,'height':1000})
                    page=context.new_page();observe(page)
                    page.goto(base+'/learn/')
                    page.get_by_label('Your name',exact=True).fill('SQL Learner')
                    page.get_by_label('Your name',exact=True).press('Enter')
                    page.get_by_role('link',name='Open SQL lesson',exact=True).click()
                    codes=page.locator('pre code').all_text_contents()
                    before=learning_snapshot(path);language(page,'de')
                    expect(page.get_by_role('heading',name='SQL: SELECT und WHERE',exact=True)).to_be_visible()
                    expect(page.get_by_role('heading',name='1. Spalten mit SELECT auswählen',exact=True)).to_be_visible()
                    expect(page.get_by_role('heading',name='2. Zeilen mit WHERE auswählen',exact=True)).to_be_visible()
                    expect(page.locator('.interface-scope')).to_have_count(0)
                    assert page.locator('pre code').all_text_contents()==codes
                    page.screenshot(path=str(report_dir/'sql-lesson-german-desktop.png'),full_page=True)
                    page.goto(base+'/progress/')
                    expect(page.locator('[data-subject="sql"] .topic-title')).to_have_text('Tabellen mit SELECT und WHERE lesen')
                    assert learning_snapshot(path)==before
                    groups.append('German SQL lesson and topic titles; English default; unchanged executable examples, fictional table and zero activity')

                    page.goto(base+'/sql/practice')
                    for position,q in enumerate(sql_content.PRACTICE):
                        expect(page.locator('#practice-progress')).to_have_text(f'Frage {position+1} von 10')
                        assert q['prompt'] not in page.locator('.activity-form legend').inner_text()
                        option=q['correct'] if position%2==0 else next(k for k in q['choices'] if k!=q['correct'])
                        page.locator(f'[name="{q["id"]}"][value="{option}"]').check()
                        if position==2:
                            saved=learning_snapshot(path);language(page,'en')
                            expect(page.locator('#practice-progress')).to_have_text('Question 3 of 10')
                            expect(page.locator(f'[name="{q["id"]}"][value="{option}"]')).to_be_checked()
                            language(page,'de');assert learning_snapshot(path)==saved
                        page.get_by_role('button',name='Antwort überprüfen',exact=True).click()
                        expect(page.locator('#personal-feedback')).to_contain_text('richtig gelöst' if position%2==0 else 'Lies die Erklärung')
                        expect(page.locator('.answer-result strong')).to_have_text('Richtig' if position%2==0 else 'Falsch')
                        assert q['explanation'] not in page.locator('.answer-result').inner_text()
                        saved=learning_snapshot(path);page.reload();assert learning_snapshot(path)==saved
                        page.get_by_role('link',name='Nächste Frage' if position<9 else 'Übung beenden',exact=True).click()
                    expect(page.get_by_role('heading',name='Übungsrunde abgeschlossen!',exact=True)).to_be_visible()
                    page.get_by_role('link',name='Erneut üben',exact=True).click()
                    expect(page.locator('#practice-progress')).to_have_text('Frage 1 von 10')
                    assert rows("SELECT COUNT(*),SUM(score) FROM learning_attempts WHERE activity_kind='practice'")==[(10,5)]
                    groups.append('All ten German practice questions, translated options/explanations and immediate correct/incorrect feedback; round-preserving switches, restart and no refresh duplicates')

                    for score in (0,2,3,5):
                        page.goto(base+'/sql/quiz')
                        expect(page.locator('.activity-form fieldset')).to_have_count(5)
                        expect(page.locator('.answer-result')).to_have_count(0)
                        assert 'Die Spaltennamen hinter SELECT' not in page.content()
                        for index,q in enumerate(sql_content.QUIZ):
                            option=q['correct'] if index<score else next(k for k in q['choices'] if k!=q['correct'])
                            page.locator(f'[name="{q["id"]}"][value="{option}"]').check()
                        if score==3:
                            token=page.locator('.activity-form [name="submission_token"]').input_value()
                            saved=learning_snapshot(path);language(page,'en');language(page,'de')
                            assert page.locator('.activity-form input:checked').count()==5
                            assert page.locator('.activity-form [name="submission_token"]').input_value()==token
                            assert learning_snapshot(path)==saved
                        page.locator('.activity-form input:checked').last.press('Enter')
                        expect(page.locator('#score')).to_contain_text(f'{score} von 5')
                        expect(page.locator('#personal-feedback')).to_contain_text('Übe weiter' if score<=2 else 'Quiz bestanden' if score<5 else 'Volle Punktzahl')
                        expect(page.locator('#personal-feedback')).to_contain_text('SQL Learner!')
                        expect(page.locator('.answer-result')).to_have_count(5)
                        expect(page.get_by_text('Richtige Antwort:',exact=False)).to_have_count(5)
                        saved=learning_snapshot(path);page.reload();assert learning_snapshot(path)==saved
                        expect(page.get_by_role('link',name='Erneut versuchen',exact=True)).to_be_visible()
                    result_url=page.url
                    assert rows("SELECT score FROM learning_attempts WHERE activity_kind='quiz' ORDER BY rowid")==[(0,),(2,),(3,),(5,)]
                    assert rows('SELECT DISTINCT learning_status FROM topic_progress')==[('Still Learning',)]
                    groups.append('Five-question German quiz, no early answer reveal, all feedback bands, unlimited retries, draft/token preservation and accurate scores without automatic completion')

                    saved=learning_snapshot(path)
                    language(page,'en')
                    expect(page.locator('#personal-feedback')).to_contain_text('Congratulations, SQL Learner!')
                    expect(page.locator('.answer-result h2').first).to_have_text(sql_content.QUIZ[0]['prompt'])
                    language(page,'de')
                    expect(page.locator('.answer-result h2').first).to_have_text('Was wählt SELECT in einer Abfrage aus?')
                    assert learning_snapshot(path)==saved
                    assert rows("SELECT prompt FROM learning_answers WHERE question_id='q1' AND attempt_id IN (SELECT attempt_id FROM learning_attempts WHERE activity_kind='quiz')")==[(sql_content.QUIZ[0]['prompt'],)]*4
                    page.goto(base+'/progress/')
                    expect(page.locator('#total-practice')).to_have_text('10')
                    expect(page.locator('#total-exercises')).to_have_text('5')
                    expect(page.locator('#total-quizzes')).to_have_text('4')
                    groups.append('Saved result translation is read-only; SQLite retains English answer snapshots, original IDs and real practice/quiz totals')

                    page.goto(result_url)
                    page.screenshot(path=str(report_dir/'sql-results-german-desktop.png'),full_page=True)
                    for width,height in ((320,700),(375,812),(768,1024),(844,390)):
                        page.set_viewport_size({'width':width,'height':height})
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
                    page.set_viewport_size({'width':375,'height':812})
                    page.add_style_tag(content=':root { font-size: 200%; }')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    page.screenshot(path=str(report_dir/'sql-results-german-mobile-enlarged.png'),full_page=True)
                    page.goto(base+'/sql/quiz')
                    page.get_by_role('button',name='Deutsch',exact=True).focus()
                    expect(page.get_by_role('button',name='Deutsch',exact=True)).to_be_focused()
                    assert page.get_by_role('button',name='Deutsch',exact=True).evaluate('el => getComputedStyle(el).outlineStyle')=='solid'
                    groups.append('German lesson/results remain readable on desktop, phone, tablet, landscape and 200% text; language controls retain keyboard focus')

                    other_context=browser.new_context(java_script_enabled=False)
                    other=other_context.new_page();observe(other)
                    other.goto(base+'/learn/')
                    other.get_by_label('Your name',exact=True).fill('SQL Learner')
                    other.get_by_label('Your name',exact=True).press('Enter')
                    other.goto(base+'/progress/')
                    expect(other.locator('#total-quizzes')).to_have_text('0')
                    expect(other.locator('#total-practice')).to_have_text('0')
                    expect(other.locator('#status-history tbody tr')).to_have_count(4)
                    other.goto(result_url)
                    expect(other.get_by_role('heading',name='Request error 404')).to_be_visible()
                    other.goto(base+'/sql/quiz')
                    first=sql_content.QUIZ[0]
                    other.locator(f'[name="{first["id"]}"][value="{first["correct"]}"]').check()
                    before=learning_snapshot(path);language(other,'de')
                    expect(other.locator(f'[name="{first["id"]}"][value="{first["correct"]}"]')).to_be_checked()
                    assert learning_snapshot(path)==before
                    for q in sql_content.QUIZ:
                        other.locator(f'[name="{q["id"]}"][value="{q["correct"]}"]').check()
                    other.locator('.activity-form input:checked').last.press('Enter')
                    expect(other.locator('#personal-feedback')).to_contain_text('Herzlichen Glückwunsch, SQL Learner!')
                    other.goto(base+'/progress/')
                    other_row=other.locator('[data-subject="sql"]')
                    expect(other_row.locator('.saved-status')).to_have_text('Noch am Lernen')
                    other_row.locator('[name="new_status"]').select_option('Completed')
                    before=learning_snapshot(path)
                    other_row.get_by_role('button',name='Speichern',exact=True).click()
                    expect(other.locator('.visit-error')).to_contain_text('Bitte bestätige')
                    assert learning_snapshot(path)==before
                    # Validation re-renders the saved status; choose the intended new status again.
                    other_row.locator('[name="new_status"]').select_option('Completed')
                    other_row.locator('[name="user_confirmed"]').check()
                    other_row.get_by_role('button',name='Speichern',exact=True).click()
                    expect(other_row.locator('.saved-status')).to_contain_text('Abgeschlossen')
                    other_row.locator('[name="new_status"]').select_option('Needs Review')
                    other_row.get_by_role('button',name='Speichern',exact=True).click()
                    expect(other_row.locator('.saved-status')).to_have_text('Wiederholung nötig')
                    groups.append('Same-name visitors stay isolated; German quiz/draft/Enter work without JS; Python enforces personal completion and allows returning to review')
                    other_context.close();context.close();assert not errors,errors
                finally:browser.close()
        finally:server.shutdown();thread.join();server.server_close()
    assert not Path(directory).exists()
    report={'passed_groups':groups,'errors':errors,'disposable_database_removed':True}
    (report_dir/'sql-language-browser-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir',type=Path,required=True)
    run(parser.parse_args().report_dir)
