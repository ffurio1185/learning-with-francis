"""Focused local privacy-page browser checks with disposable current-schema data."""

from retention_support import learning_snapshot
import argparse
from contextlib import closing
import json
from pathlib import Path
import tempfile
from threading import Thread

from werkzeug.serving import make_server
from learning_with_francis import db
from learning_with_francis.production import prepare_database, create_production_app
from learning_with_francis.subjects import SUBJECTS


def run(report_dir):
    from playwright.sync_api import sync_playwright, expect
    report_dir.mkdir(parents=True, exist_ok=True)
    groups, errors = [], []
    with tempfile.TemporaryDirectory(prefix='privacy-browser-', dir='/tmp') as directory:
        env = {'LWF_DATA_DIR': str(Path(directory)/'data'), 'LWF_SECRET_KEY': 'disposable-privacy-browser-test-key-12345678',
               'LWF_ALLOWED_HOSTS': 'localhost', 'LWF_DEMO_MODE': '1'}
        prepare_database(env)
        path = Path(directory)/'data/learning_with_francis.db'
        app = create_production_app(env)
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True);thread.start()
        base = f'http://localhost:{server.server_port}'
        def rows(sql):
            with closing(db.open_database(path)) as connection:
                return [tuple(row) for row in connection.execute(sql)]
        def observe(page):
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: errors.append(str(response.status)) if response.status >= 500 else None)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(viewport={'width': 1440, 'height': 900}, reduced_motion='reduce')
                    page = context.new_page();observe(page)
                    requests=[];page.on('request', lambda request: requests.append(request.url))
                    before = learning_snapshot(path)
                    page.goto(base+'/')
                    link = page.get_by_role('link', name='Privacy Policy', exact=True)
                    link.focus();expect(link).to_be_focused()
                    assert link.evaluate('el => getComputedStyle(el).outlineStyle') == 'solid'
                    page.keyboard.press('Enter')
                    expect(page).to_have_url(base+'/privacy/')
                    expect(page.get_by_role('heading', level=1)).to_have_text('Privacy Policy')
                    expect(page.locator('.hosting-verification')).to_be_visible()
                    expect(page.locator('.operator-contact')).to_contain_text('Francis Furio')
                    expect(page.get_by_role('link', name='Impressum', exact=True)).to_have_attribute('href', '/impressum/')
                    page.get_by_role('button', name='Deutsch', exact=True).click()
                    expect(page).to_have_url(base+'/privacy/')
                    expect(page.get_by_role('heading', level=1)).to_have_text('Datenschutzerklärung')
                    assert learning_snapshot(path) == before
                    assert rows('SELECT COUNT(*) FROM visits') == [(0,)]
                    assert all(url.startswith(base+'/') for url in requests)
                    groups.append('Cover keyboard link, English/German final legal pages, no third-party embeds/requests and no visitor/database writes')

                    layout_cases=0
                    for document in ('/privacy/', '/impressum/'):
                        page.goto(base+document)
                        for language in ('English','Deutsch'):
                            page.get_by_role('button', name=language, exact=True).click()
                            expect(page).to_have_url(base+document)
                            for width in (320,375,768,1440):
                                for scale in (100,200):
                                    page.set_viewport_size({'width':width,'height':850})
                                    style=page.add_style_tag(content=f'html {{font-size: {scale}%;}}')
                                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'),(document,language,width,scale)
                                    expect(page.locator('h1')).to_be_visible()
                                    assert page.locator('h1').count()==1
                                    assert page.locator('main').count()==1
                                    for link in page.locator('.privacy-nav a').all():
                                        link.focus();expect(link).to_be_focused()
                                        assert link.evaluate('el => getComputedStyle(el).outlineStyle')=='solid'
                                    style.evaluate('el=>el.remove()');layout_cases+=1
                        page.set_viewport_size({'width':375,'height':850})
                        page.screenshot(path=str(report_dir/('legal-'+document.strip('/')+'-german-mobile.png')),full_page=True)
                    page.set_viewport_size({'width':1440,'height':900})
                    page.get_by_role('button', name='English', exact=True).click()
                    page.get_by_role('link',name='Privacy Policy',exact=True).click()
                    groups.append(f'Both legal documents in English/German, desktop/mobile and 200% text: {layout_cases} layout cases; visible keyboard focus')

                    page.get_by_role('link', name='Learning home', exact=True).click()
                    expect(page.get_by_role('link', name='Privacy Policy', exact=True)).to_be_visible()
                    page.get_by_label('Your name', exact=True).fill('Privacy Learner')
                    page.get_by_role('button', name='Start Visit', exact=True).click()
                    for slug in SUBJECTS:
                        page.goto(base+f'/{slug}/')
                        expect(page.get_by_role('link', name='Privacy Policy', exact=True)).to_have_attribute('href','/privacy/')
                        expect(page.get_by_role('link', name='Impressum', exact=True)).to_have_attribute('href','/impressum/')
                    page.goto(base+'/sql/quiz')
                    for question in SUBJECTS['sql']['content'].QUIZ:
                        page.locator(f'input[name="{question["id"]}"][value="{question["correct"]}"]').check()
                    page.locator('#activity-form button[type=submit]').click()
                    result_url=page.url
                    expect(page.locator('#score')).to_contain_text('5 out of 5')
                    before = learning_snapshot(path);identity=rows('SELECT visit_id FROM visits')
                    page.get_by_role('link', name='Privacy Policy', exact=True).click()
                    page.get_by_role('button', name='Deutsch', exact=True).click()
                    page.goto(base+'/progress/')
                    expect(page.locator('#total-quizzes')).to_have_text('1')
                    assert learning_snapshot(path)==before and rows('SELECT visit_id FROM visits')==identity
                    page.goto(result_url);expect(page.locator('#score')).to_contain_text('5 von 5')
                    groups.append('All subject links, real saved quiz, translated results and progress stay intact after reading/switching privacy page')

                    other=browser.new_context(java_script_enabled=False,viewport={'width':375,'height':850})
                    second=other.new_page();observe(second)
                    second.goto(base+'/impressum/')
                    expect(second.get_by_role('heading',level=1)).to_have_text('Impressum')
                    second.get_by_role('button',name='Deutsch',exact=True).click()
                    expect(second).to_have_url(base+'/impressum/')
                    expect(second.get_by_text('Anbieter und Kontakt',exact=True)).to_be_visible()
                    second.get_by_role('link',name='Datenschutzerklärung',exact=True).click()
                    second.get_by_role('button', name='Deutsch', exact=True).click()
                    expect(second.get_by_role('heading', level=1)).to_have_text('Datenschutzerklärung')
                    second.get_by_role('link', name='Lernübersicht', exact=True).click()
                    second.get_by_label('Dein Name', exact=True).fill('Privacy Learner')
                    second.get_by_role('button', name='Besuch starten', exact=True).click()
                    second.goto(base+'/progress/')
                    expect(second.locator('#no-activity')).to_be_visible()
                    form=second.locator('.status-form').first
                    form.locator('select').select_option('Completed');form.locator('button[type=submit]').click()
                    expect(second.locator('.visit-error')).to_be_visible()
                    second.goto(result_url)
                    expect(second.locator('h1')).to_contain_text('404')
                    groups.append('No-JavaScript policy/language/forms work; same-name visitors remain isolated and Python confirmation still protects completion')

                    page.goto(base+'/learn/')
                    page.get_by_role('button',name='Besuch beenden',exact=True).click()
                    before=learning_snapshot(path)
                    page.get_by_role('link',name='Datenschutzerklärung',exact=True).click()
                    expect(page.get_by_role('heading',level=1)).to_have_text('Datenschutzerklärung')
                    assert rows('SELECT COUNT(*) FROM visits')==[(1,)]
                    assert rows('SELECT COUNT(*) FROM learning_attempts')==[(0,)]
                    assert rows('SELECT COUNT(*) FROM learning_answers')==[(0,)]
                    assert learning_snapshot(path)==before
                    groups.append('End Visit deletes owned records; public privacy page remains available without a visit')
                    assert rows('PRAGMA integrity_check')==[('ok',)]
                    assert rows('PRAGMA foreign_key_check')==[]
                    other.close();context.close()
                finally:
                    browser.close()
        finally:
            server.shutdown();thread.join(timeout=5);server.server_close()
    assert not Path(directory).exists()
    assert not errors,errors
    report={'passed_groups':groups,'layout_cases':layout_cases,'errors':errors,'disposable_database_removed':True}
    (report_dir/'browser-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir',type=Path,required=True)
    run(parser.parse_args().report_dir)
