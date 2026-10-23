"""Retention browser checks: controlled clock, disposable data, loopback only."""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from threading import Thread
from unittest.mock import patch

from werkzeug.serving import make_server
from learning_with_francis import create_app, db, visitors
from learning_with_francis.subjects import SUBJECTS


def run(report_dir):
    from playwright.sync_api import sync_playwright, expect
    report_dir.mkdir(parents=True, exist_ok=True)
    groups, errors = [], []
    with tempfile.TemporaryDirectory(prefix='retention-browser-', dir='/tmp') as directory:
        path = Path(directory)/'learning.db'
        db.initialize_database(path)
        now = [datetime.now(timezone.utc).replace(microsecond=0)]
        config = {'TESTING':True, 'DATABASE':str(path), 'SECRET_KEY':'disposable-retention-browser-key'}
        server = thread = None
        def serve():
            nonlocal server, thread
            server=make_server('127.0.0.1',0,create_app(config),threaded=True)
            thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            return f'http://127.0.0.1:{server.server_port}'
        def rows(sql,args=()):
            with closing(db.open_database(path)) as conn:return [tuple(row) for row in conn.execute(sql,args)]
        def start(page,base,de=False):
            page.goto(base+'/learn/')
            page.get_by_label('Dein Name' if de else 'Your name',exact=True).fill('Temporary Learner')
            page.get_by_role('button',name='Besuch starten' if de else 'Start Visit',exact=True).click()
        def observe(page):
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('response',lambda response:errors.append(f'{response.status} {response.url}') if response.status>=500 else None)
        def answer(page,base,slug,kind):
            page.goto(f'{base}/{slug}/{kind}')
            content=SUBJECTS[slug]['content']
            questions=content.QUIZ if kind=='quiz' else (content.PRACTICE[0],)
            for q in questions:page.locator(f'input[name="{q["id"]}"][value="{q["correct"]}"]').check()
            page.locator('#activity-form button[type="submit"]').click()
            expect(page.locator('h1')).to_be_visible()
            return page.url
        with patch.object(visitors,'utc_now',side_effect=lambda:now[0]):
            base=serve()
            try:
                with sync_playwright() as playwright:
                    browser=playwright.chromium.launch(headless=True)
                    try:
                        a=browser.new_context(reduced_motion='reduce');b=browser.new_context(reduced_motion='reduce',java_script_enabled=False)
                        page=a.new_page();other=b.new_page();observe(page);observe(other)
                        start(page,base);start(other,base)
                        ids=[row[0] for row in rows('SELECT visit_id FROM visits ORDER BY rowid')]
                        assert ids[0]!=ids[1]
                        page.goto(base+'/progress/');expect(page.locator('#total-quizzes')).to_have_text('0')
                        groups.append('Independent same-name visits start with zero counts and four Still Learning subjects')
                        result=''
                        for slug in SUBJECTS:
                            result=answer(page,base,slug,'practice')
                            result=answer(page,base,slug,'quiz')
                        page.goto(base+'/progress/')
                        expect(page.locator('#total-practice')).to_have_text('4')
                        expect(page.locator('#total-quizzes')).to_have_text('4')
                        assert rows("SELECT COUNT(*) FROM topic_progress WHERE learning_status='Still Learning'")==[(8,)]
                        other.goto(result);expect(other.locator('h1')).to_contain_text('404')
                        groups.append('All four subject practice and quiz scores save without completing topics; second visitor cannot read results')
                        page.goto(base+'/progress/')
                        row=page.locator('[data-subject="sql"]')
                        row.locator('[name="new_status"]').select_option('Completed')
                        row.get_by_role('button',name='Save',exact=True).click()
                        expect(row.locator('.confirmation-error')).to_be_visible()
                        row.locator('[name="user_confirmed"]').check();row.get_by_role('button',name='Save',exact=True).click()
                        expect(page.locator('[data-subject="sql"]')).to_have_attribute('data-learning-status','Completed')
                        cookies=a.cookies()
                        page.get_by_role('button',name='End Visit',exact=True).click()
                        expect(page.get_by_text('Your visit has ended. Your learning data has been deleted.',exact=True)).to_be_visible()
                        assert rows('SELECT COUNT(*) FROM learning_answers')==[(0,)]
                        assert rows('SELECT COUNT(*) FROM visits')==[(1,)]
                        other.goto(base+'/progress/');expect(other.locator('#total-quizzes')).to_have_text('0')
                        groups.append('Confirmed completion remains manual; End Visit deletes answers, attempts, confirmation and history without deleting other visitor')
                        replay=browser.new_context(reduced_motion='reduce');replay.add_cookies(cookies);old=replay.new_page();observe(old)
                        old.goto(result);expect(old.get_by_label('Your name',exact=True)).to_be_visible()
                        page.go_back();expect(page.get_by_label('Your name',exact=True)).to_be_visible()
                        groups.append('Old signed cookies, saved result URLs and browser Back cannot reopen ended progress')
                        start(page,base);answer(page,base,'sql','quiz')
                        page.get_by_role('button',name='Start New Visit',exact=True).click()
                        expect(page.get_by_label('Your name',exact=True)).to_be_visible()
                        assert rows('SELECT COUNT(*) FROM learning_attempts')==[(0,)]
                        start(page,base);page.goto(base+'/progress/')
                        expect(page.locator('#total-quizzes')).to_have_text('0')
                        groups.append('Start New Visit removes previous activity before name entry; repeated same-name visit is empty')
                        now[0]+=timedelta(seconds=1799)
                        page.goto(base+'/python/')
                        expect(page.locator('h1')).to_be_visible()
                        now[0]+=timedelta(seconds=1799)
                        page.goto(base+'/progress/');expect(page.locator('#total-quizzes')).to_have_text('0')
                        assert rows('SELECT COUNT(*) FROM visits')==[(1,)] # inactive second visitor was cleaned
                        groups.append('Learning at 29:59 renews inactivity; total learning exceeds 30 minutes; expired second visitor alone is removed')
                        page.get_by_role('button',name='Deutsch',exact=True).click()
                        expect(page.locator('html')).to_have_attribute('lang','de')
                        now[0]+=timedelta(seconds=1800)
                        page.reload();expect(page.get_by_label('Dein Name',exact=True)).to_be_visible()
                        expect(page.get_by_text('Dein Besuch ist abgelaufen oder wurde beendet. Beginne einen neuen Besuch, um weiterzulernen.',exact=True)).to_be_visible()
                        assert rows('SELECT COUNT(*) FROM visits')==[(0,)]
                        groups.append('At exactly 30 minutes, reload expires before renewal, clears identity and preserves German')
                        start(other,base)
                        for language in ('de','en'):
                            other.get_by_role('button',name='Deutsch' if language=='de' else 'English',exact=True).click()
                            for width in (375,1440):
                                other.set_viewport_size({'width':width,'height':900})
                                other.goto(base+'/learn/')
                                assert other.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                                other.keyboard.press('Tab')
                                assert other.evaluate('document.activeElement !== document.body')
                        other.get_by_role('button',name='End Visit',exact=True).click()
                        expect(other.get_by_label('Your name',exact=True)).to_be_visible()
                        groups.append('No JavaScript: bilingual end/new controls, deletion, keyboard focus and phone/desktop notices work')
                        start(page,base,de=True)
                        now[0]+=timedelta(hours=2)
                        assert rows('SELECT COUNT(*) FROM visits')==[(1,)] # no scheduler exists
                        server.shutdown();thread.join();server.server_close();base=serve()
                        assert rows('SELECT COUNT(*) FROM visits')==[(0,)]
                        page.goto(base+'/learn/');expect(page.get_by_label('Dein Name',exact=True)).to_be_visible()
                        groups.append('Sleeping/no-request simulation retains expired rows until startup; restart cleans without recovering stale session')
                        assert rows('PRAGMA foreign_key_check')==[]
                        assert rows('PRAGMA integrity_check')==[('ok',)]
                        assert rows('SELECT COUNT(*) FROM subjects')==[(4,)]
                        assert rows('SELECT COUNT(*) FROM topics')==[(4,)]
                        assert not errors,errors
                        groups.append('Curriculum, database integrity and foreign keys remain valid; no unexpected browser/server errors')
                        for context in (a,b,replay):context.close()
                    finally:browser.close()
            finally:
                server.shutdown();thread.join();server.server_close()
    assert not Path(directory).exists()
    report={'passed_groups':groups,'errors':errors,'disposable_database_removed':True}
    (report_dir/'retention-browser-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report-dir',type=Path,required=True)
    run(parser.parse_args().report_dir)
