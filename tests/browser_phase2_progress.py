"""Optional Chromium integration checks. Run with Playwright installed outside the project.

Uses its own temporary current-schema database and loopback server; keeps only reports.
Example: PYTHONPATH=.:/tmp/p25-browser-tools PLAYWRIGHT_BROWSERS_PATH=/tmp/p25-browser-cache
         .venv/bin/python -B tests/browser_phase2_progress.py --report-dir /tmp/p25-report
"""

import argparse
import base64
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from threading import Thread
from zoneinfo import ZoneInfo

from werkzeug.serving import make_server

from learning_with_francis import create_app, db
from learning_with_francis.subjects import SUBJECTS


def run(report_dir):
    from playwright.sync_api import sync_playwright, expect

    groups, errors = [], []
    report_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='p25-browser-data-', dir='/tmp') as directory:
        database = Path(directory) / 'learning.db'
        db.initialize_database(database)
        config = {'TESTING': True, 'DATABASE': str(database),
                  'SECRET_KEY_FILE': str(Path(directory) / 'signing-key'),
                  'SESSION_COOKIE_NAME': 'p25_browser_check'}

        def rows(sql, parameters=()):
            with closing(db.open_database(database)) as connection:
                return [tuple(row) for row in connection.execute(sql, parameters)]

        def serve():
            server = make_server('127.0.0.1', 0, create_app(config), threaded=True)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            return server, thread

        server, thread = serve()
        base = f'http://127.0.0.1:{server.server_port}'
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                page = context.new_page()

                def observe(page):
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('console', lambda message: errors.append(message.text)
                            if message.type == 'error' and 'Failed to load resource' not in message.text else None)
                    page.on('response', lambda response: errors.append(f'{response.status} {response.url}')
                            if response.status >= 500 else None)

                observe(page)

                def start(page):
                    page.goto(base + '/learn/')
                    page.get_by_label('Your name', exact=True).fill('Browser Learner')
                    page.get_by_role('button', name='Start Visit', exact=True).click()
                    expect(page.get_by_role('heading', name='Welcome to Learning with Francis, Browser Learner!')).to_be_visible()

                def progress(page):
                    page.goto(base + '/progress/')
                    expect(page.locator('#topic-filter')).to_be_enabled()

                def local_time_matches(node, stored):
                    instant = datetime.fromisoformat(stored).replace(tzinfo=timezone.utc)
                    local = instant.astimezone(ZoneInfo('Europe/Berlin'))
                    expect(node).to_have_text(local.strftime('%d.%m.%Y %H:%M:%S %Z'))
                    expect(node).to_have_attribute('datetime', local.isoformat())

                def status(slug, value, confirm=False):
                    progress(page)
                    form = page.locator(f'.topic-row[data-subject="{slug}"] .status-form')
                    form.locator('select').select_option(value)
                    if confirm:
                        form.locator('input[type="checkbox"]').check()
                    with page.expect_response(lambda response: '/status' in response.url and response.request.method == 'POST') as response:
                        form.get_by_role('button', name='Save', exact=True).click()
                    assert response.value.status == 303
                    expect(page.locator(f'.topic-row[data-subject="{slug}"]')).to_have_attribute('data-learning-status', value)

                def attempt(slug, kind, score=5, target=None):
                    target = target or page
                    target.goto(base + f'/{slug}/{kind}')
                    module = SUBJECTS[slug]['content']
                    questions = module.QUIZ if kind == 'quiz' else (module.PRACTICE[0],)
                    for index, question in enumerate(questions):
                        selected = question['correct'] if index < score else next(
                            key for key in question['choices'] if key != question['correct'])
                        target.locator(f'input[name="{question["id"]}"][value="{selected}"]').check()
                    target.get_by_role('button', name='Submit quiz' if kind == 'quiz' else 'Check answer', exact=True).click()
                    expect(target.locator('#score')).to_contain_text(f'{min(score, len(questions))} out of {len(questions)}')
                    expect(target.get_by_role('link', name='My Progress', exact=True)).to_be_visible()
                    stored = rows('SELECT submitted_at FROM learning_attempts WHERE attempt_id=?',
                                  (target.url.rsplit('/', 1)[1],))[0][0]
                    local_time_matches(target.locator('time').first, stored)
                    return target.url

                page.goto(base + '/learn/')
                expect(page.locator('.available-subjects .subject-icon')).to_have_count(4)
                start(page)
                expect(page.locator('.subject-cards .subject-icon')).to_have_count(4)
                expect(page.locator('.available-subjects .subject-icon')).to_have_count(4)
                for slug, subject in SUBJECTS.items():
                    expect(page.locator('.subject-heading', has_text=subject['name'])).to_have_text(subject['name'])
                home_icon_sources = {slug: page.locator('.subject-heading', has_text=subject['name']).locator('img').get_attribute('src')
                                     for slug, subject in SUBJECTS.items()}
                for width in (1280, 390):
                    page.set_viewport_size({'width': width, 'height': 900})
                    for icon in page.locator('.subject-icon').all():
                        expect(icon).to_be_visible()
                        assert icon.evaluate('image => image.complete && image.naturalWidth > 0')
                        expect(icon).to_have_attribute('alt', '')
                        expect(icon).to_have_css('width', '32px')
                        expect(icon).to_have_css('height', '32px')
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                    expect(page.locator('.available-subjects')).to_have_css('list-style-type', 'none')
                    page.screenshot(path=str(report_dir / f'subject-icons-{width}.png'), full_page=True)
                page.set_viewport_size({'width': 1280, 'height': 900})
                assert rows('SELECT COUNT(*) FROM learning_attempts') == [(0,)]
                groups.append('Four local subject icons replace bullets and match card headings; loaded images, accessible text and desktop/mobile layout verified without activity writes')
                progress(page)
                expect(page.locator('.topic-row')).to_have_count(4)
                expect(page.locator('.topic-row .subject-icon')).to_have_count(4)
                for width in (1280, 390):
                    page.set_viewport_size({'width': width, 'height': 900})
                    for slug, subject in SUBJECTS.items():
                        row = page.locator(f'.topic-row[data-subject="{slug}"]')
                        icon = row.locator('.subject-icon')
                        expect(row.locator('.subject-heading')).to_have_text(subject['name'])
                        expect(row.locator('th[scope="row"]')).to_have_count(1)
                        expect(icon).to_have_attribute('src', home_icon_sources[slug])
                        expect(icon).to_have_attribute('alt', '')
                        expect(icon).to_have_css('width', '32px')
                        expect(icon).to_have_css('height', '32px')
                        assert icon.evaluate('image => image.complete && image.naturalWidth > 0')
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                    page.screenshot(path=str(report_dir / f'progress-subject-icons-{width}.png'), full_page=True)
                page.set_viewport_size({'width': 1280, 'height': 900})
                assert rows('SELECT COUNT(*) FROM learning_attempts') == [(0,)]
                groups.append('My Progress reuses the same four local 32px icons; row headers, accessible names and desktop/mobile table layout remain intact')
                for selector in ('#total-practice', '#total-exercises', '#total-quizzes'):
                    expect(page.locator(selector)).to_have_text('0')
                expect(page.locator('#no-activity')).to_be_visible()
                expect(page.locator('#visit-started')).to_contain_text('Current visit started:')
                expect(page.locator('#initial-history-help')).to_contain_text('not practice, quiz attempts or completed exercises')
                assert page.locator('input[type="checkbox"]:checked').count() == 0
                groups.append('Welcome, greeting, connected navigation, four subjects and zero activity')

                sql_result = None
                for slug in SUBJECTS:
                    page.goto(base + f'/{slug}/')
                    expect(page.get_by_role('link', name='My Progress', exact=True)).to_be_visible()
                    attempt(slug, 'practice', score=0 if slug == 'sql' else 1)
                    expect(page.get_by_text('Correct answer:', exact=False)).to_be_visible()
                    result = attempt(slug, 'quiz', score=5)
                    expect(page.locator('#personal-feedback')).to_have_text(SUBJECTS[slug]['content'].quiz_feedback(5, 'Browser Learner'))
                    if slug == 'sql':
                        sql_result = result
                progress(page)
                expect(page.locator('#total-practice')).to_have_text('4')
                expect(page.locator('#total-exercises')).to_have_text('3')
                expect(page.locator('#total-quizzes')).to_have_text('4')
                assert rows("SELECT DISTINCT learning_status FROM topic_progress") == [('Still Learning',)]
                assert len(rows('SELECT * FROM learning_answers')) == 24
                groups.append('All four lessons, real practice/quiz results, correct counts and no automatic completion')

                for score in (1, 3):
                    attempt('sql', 'quiz', score)
                    expect(page.locator('#personal-feedback')).to_have_text(SUBJECTS['sql']['content'].quiz_feedback(score, 'Browser Learner'))
                before = rows('SELECT COUNT(*) FROM learning_attempts')
                page.reload()
                assert rows('SELECT COUNT(*) FROM learning_attempts') == before
                expect(page.get_by_role('link', name='Try Again', exact=True)).to_be_visible()
                groups.append('Quiz feedback bands, unlimited retries and refresh without duplicate activity')

                page.goto(base + '/sql/practice')
                for question in SUBJECTS['sql']['content'].PRACTICE:
                    page.locator(f'input[name="{question["id"]}"][value="{question["correct"]}"]').check()
                    page.get_by_role('button', name='Check answer', exact=True).click()
                    expect(page.get_by_text(question['explanation'], exact=True)).to_be_visible()
                    page.locator('#practice-next').click()
                expect(page.get_by_role('heading', name='Practice complete!')).to_be_visible()
                expect(page.get_by_role('link', name='My Progress', exact=True)).to_be_visible()
                page.get_by_role('link', name='Start Practicing Again', exact=True).click()
                expect(page.locator('#practice-progress')).to_have_text('Question 1 of 10')
                groups.append('Ten-question practice, completion, restart and tracker navigation')

                progress(page)
                form = page.locator('.topic-row[data-subject="sql"] .status-form')
                form.locator('select').select_option('Completed')
                before = rows('SELECT * FROM topic_progress')
                posts = []
                page.on('request', lambda request: posts.append(request.url) if request.method == 'POST' else None)
                form.get_by_role('button', name='Save', exact=True).click()
                expect(form.locator('.confirmation-error')).to_be_visible()
                expect(form.locator('input[type="checkbox"]')).not_to_be_checked()
                assert not posts
                assert rows('SELECT * FROM topic_progress') == before
                groups.append('JavaScript blocks unconfirmed completion without checking the checkbox or submitting')

                status('sql', 'Completed', True)
                status('python', 'Needs Review')
                expect(page.locator('[data-summary-status="Still Learning"]')).to_have_text('2')
                expect(page.locator('[data-summary-status="Needs Review"]')).to_have_text('1')
                expect(page.locator('[data-summary-status="Completed"]')).to_have_text('1')
                before = rows('SELECT * FROM topic_progress'), rows('SELECT * FROM topic_status_history')
                for value, count in (('All', 4), ('Still Learning', 2), ('Needs Review', 1), ('Completed', 1)):
                    page.locator('#topic-filter').select_option(value)
                    expect(page.locator('.topic-row:visible')).to_have_count(count)
                    expect(page.locator('#filter-empty-message')).to_be_hidden()
                assert (rows('SELECT * FROM topic_progress'), rows('SELECT * FROM topic_status_history')) == before
                groups.append('All four saved-status filters; filtering is read-only and totals remain unchanged')

                status('sql', 'Needs Review')
                page.locator('#topic-filter').select_option('Completed')
                expect(page.locator('#filter-empty-message')).to_be_visible()
                expect(page.locator('#topics-table-container')).to_be_hidden()
                status('sql', 'Still Learning')
                status('sql', 'Completed', True)
                expect(page.locator('#topic-filter')).to_have_value('All')
                expect(page.locator('.topic-row input[type="checkbox"]:checked')).to_have_count(0)
                assert rows("SELECT understanding_confirmed_at FROM topic_progress WHERE topic_id='sql-select-basics'")[0][0]
                groups.append('No-match message, changes back from Completed, fresh confirmation and 303/reset behaviour')

                progress(page)
                expect(page.locator('#activity-history tbody tr')).to_have_count(20)
                expect(page.locator('#status-history tbody tr')).to_have_count(9)
                expect(page.locator('#total-practice')).to_have_text('14')
                expect(page.locator('#total-quizzes')).to_have_text('6')
                for row in page.locator('#activity-history tbody tr').all():
                    assert row.locator('time').inner_text()
                stored_dates = rows('SELECT submitted_at FROM learning_attempts ORDER BY submitted_at DESC,rowid DESC')
                for node, (stored,) in zip(page.locator('#activity-history time').all(), stored_dates, strict=True):
                    local_time_matches(node, stored)
                stored_dates = rows('SELECT changed_at FROM topic_status_history ORDER BY changed_at DESC,history_id DESC')
                for node, (stored,) in zip(page.locator('#status-history time').all(), stored_dates, strict=True):
                    local_time_matches(node, stored)
                confirmed = rows("SELECT understanding_confirmed_at FROM topic_progress WHERE topic_id='sql-select-basics'")[0][0]
                local_time_matches(page.locator('.topic-row[data-subject="sql"] .saved-status time'), confirmed)
                local_time_matches(page.locator('#visit-started time'), rows('SELECT started_at FROM visits')[0][0])
                groups.append('New practice/quiz dates, status history, confirmations and visit start display in Europe/Berlin; stored UTC is unchanged')
                page.locator('#activity-history a').first.click()
                expect(page.locator('#score')).to_be_visible()
                groups.append('Dated scores/activity/status history, zero-safe totals and saved answer links')

                other_context = browser.new_context()
                other = other_context.new_page()
                observe(other)
                start(other)
                progress(other)
                expect(other.locator('#total-quizzes')).to_have_text('0')
                expect(other.locator('[data-summary-status="Still Learning"]')).to_have_text('4')
                expect(other.locator('#status-history tbody tr')).to_have_count(4)
                assert other.goto(sql_result).status == 404
                groups.append('Same-name visitors have separate statuses, counts, history and result access')

                attempt('python', 'practice', 0, target=other)
                foreign_result = attempt('python', 'quiz', 3, target=other)
                progress(other)
                expect(other.locator('#total-practice')).to_have_text('1')
                expect(other.locator('#total-exercises')).to_have_text('0')
                expect(other.locator('#total-quizzes')).to_have_text('1')
                expect(other.locator('#activity-history tbody tr')).to_have_count(2)
                expect(other.locator('#activity-history')).to_contain_text('Python')
                expect(other.locator('#activity-history')).not_to_contain_text('SQL')
                assert page.goto(foreign_result).status == 404
                progress(page)
                expect(page.locator('#total-practice')).to_have_text('14')
                expect(page.locator('#total-quizzes')).to_have_text('6')
                # Another tab shares this context's cookie and must resume, not create a visit.
                shared_tab = context.new_page()
                shared_tab.goto(base + '/progress/')
                expect(shared_tab.locator('#total-quizzes')).to_have_text('6')
                expect(shared_tab.locator('#visit-started')).to_have_text(page.locator('#visit-started').inner_text())
                shared_tab.close()
                groups.append('Two active visitors save separate answers; another tab deliberately resumes the same visit')

                no_js = browser.new_context(java_script_enabled=False, storage_state=context.storage_state())
                no_js_page = no_js.new_page()
                no_js_page.goto(base + '/progress/')
                form = no_js_page.locator('.topic-row[data-subject="sap"] .status-form')
                form.locator('select').select_option('Completed')
                with no_js_page.expect_response(lambda response: '/status' in response.url) as response:
                    form.get_by_role('button', name='Save', exact=True).click()
                assert response.value.status == 400
                expect(no_js_page.locator('.visit-error')).to_contain_text('Please confirm')
                assert rows("SELECT learning_status FROM topic_progress WHERE visit_id=(SELECT visit_id FROM visits ORDER BY rowid LIMIT 1) AND topic_id='sap-basics'") == [('Still Learning',)]
                no_js.close()
                groups.append('Python rejects unconfirmed completion with JavaScript disabled')

                progress(page)
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path=str(report_dir / 'progress-mobile.png'), full_page=True)
                page.set_viewport_size({'width': 1280, 'height': 900})
                page.screenshot(path=str(report_dir / 'progress-desktop.png'), full_page=True)
                assert not errors, errors
                groups.append('Mobile/desktop layout and no unexpected JavaScript, console or server errors')

                # A new Flask instance uses the same database and stable signing-key file.
                server.shutdown()
                thread.join()
                server.server_close()
                server, thread = serve()
                base = f'http://127.0.0.1:{server.server_port}'
                progress(page)
                expect(page.locator('.topic-row[data-subject="sql"]')).to_have_attribute('data-learning-status', 'Completed')
                expect(page.locator('#total-quizzes')).to_have_text('6')
                groups.append('Saved statuses, scores and history survive a fresh Flask server instance')

                progress(page)
                page.get_by_role('button', name='Start New Visit', exact=True).click()
                start(page)
                progress(page)
                expect(page.locator('#total-practice')).to_have_text('0')
                expect(page.locator('#total-exercises')).to_have_text('0')
                expect(page.locator('#total-quizzes')).to_have_text('0')
                expect(page.locator('#no-activity')).to_be_visible()
                expect(page.locator('#status-history tbody tr')).to_have_count(4)
                expect(page.locator('[data-summary-status="Still Learning"]')).to_have_text('4')
                assert rows('SELECT COUNT(*) FROM learning_attempts') == [(2,)]
                progress(other)
                expect(other.locator('#total-quizzes')).to_have_text('1')
                page.goto(base + '/learn/')
                page.get_by_role('button', name='End Visit', exact=True).click()
                expect(page.get_by_text('Your visit has ended. Your learning data has been deleted.', exact=True)).to_be_visible()
                groups.append('New visit resets progress; End Visit deletes previous records without affecting the other visitor')

                # A normal persistent browser profile retains browsing history across visits.
                # Screenshot pixels, rather than :visited/getComputedStyle history detection,
                # verify the actual rendered link color (browsers mask visited state in JS).
                profile = playwright.chromium.launch_persistent_context(
                    str(Path(directory) / 'link-color-profile'), headless=True)
                try:
                    link_page = profile.pages[0]
                    observe(link_page)
                    start(link_page)
                    first_visit = rows('SELECT visit_id FROM visits ORDER BY rowid DESC LIMIT 1')[0][0]
                    before = rows('SELECT * FROM topic_progress'), rows('SELECT * FROM topic_status_history')
                    for slug in SUBJECTS:
                        link = link_page.locator(f'a.lesson-link[href="/{slug}/"]')
                        expect(link).to_have_css('color', 'rgb(23, 94, 172)')
                        link.click()
                        expect(link_page.get_by_role('link', name='My Progress', exact=True)).to_be_visible()
                        link_page.get_by_role('link', name='Learning home', exact=True).click()
                    assert (rows('SELECT * FROM topic_progress'), rows('SELECT * FROM topic_status_history')) == before
                    link_page.get_by_role('button', name='Start New Visit', exact=True).click()
                    start(link_page)
                    second_visit = rows('SELECT visit_id FROM visits ORDER BY rowid DESC LIMIT 1')[0][0]
                    assert second_visit != first_visit
                    for slug in SUBJECTS:
                        link = link_page.locator(f'a.lesson-link[href="/{slug}/"]')
                        link_page.mouse.move(0, 0)
                        expect(link).to_have_css('color', 'rgb(23, 94, 172)')
                        image_bytes = link.screenshot(path=str(report_dir / f'{slug}-visited-link.png'))
                        colors = link_page.evaluate('''async (png) => {
                            const image = new Image();
                            image.src = 'data:image/png;base64,' + png;
                            await image.decode();
                            const canvas = document.createElement('canvas');
                            canvas.width = image.width; canvas.height = image.height;
                            const context = canvas.getContext('2d');
                            context.drawImage(image, 0, 0);
                            const data = context.getImageData(0, 0, canvas.width, canvas.height).data;
                            let blue = 0, purple = 0;
                            for (let i = 0; i < data.length; i += 4) {
                                if (data[i] === 23 && data[i+1] === 94 && data[i+2] === 172) blue++;
                                if (data[i] === 85 && data[i+1] === 26 && data[i+2] === 139) purple++;
                            }
                            return {blue, purple};
                        }''', base64.b64encode(image_bytes).decode())
                        assert colors['blue'] > 0 and colors['purple'] == 0, (slug, colors)
                        link.hover()
                        expect(link).to_have_css('color', 'rgb(16, 71, 120)')
                    # The visited selector must explicitly use the same blue, independently
                    # of browser privacy masking and operating-system history settings.
                    assert link_page.evaluate('''() => [...document.styleSheets].some(sheet =>
                        [...sheet.cssRules].some(rule => rule.selectorText?.includes('a:visited')
                            && rule.selectorText.includes('a:link') && rule.style.color === 'rgb(23, 94, 172)'))''')
                    link_page.mouse.move(0, 0)
                    link = link_page.locator('a.lesson-link').first
                    link.focus()
                    link_page.keyboard.press('Shift+Tab')
                    link_page.keyboard.press('Tab')
                    expect(link).to_be_focused()
                    assert link.evaluate("element => element.matches(':focus-visible')")
                    expect(link).to_have_css('outline-width', '3px')
                    expect(link).to_have_css('text-decoration-line', 'underline')
                    expect(link_page.locator('a.button-link').first).to_have_css('color', 'rgb(255, 255, 255)')
                    progress(link_page)
                    expect(link_page.locator('#total-practice')).to_have_text('0')
                    expect(link_page.locator('#total-exercises')).to_have_text('0')
                    expect(link_page.locator('#total-quizzes')).to_have_text('0')
                    expect(link_page.locator('[data-summary-status="Still Learning"]')).to_have_text('4')
                    link_page.goto(base + '/sql/')
                    link_page.get_by_role('button', name='End Visit', exact=True).click()
                    expect(link_page.get_by_text('Your visit has ended. Your learning data has been deleted.', exact=True)).to_be_visible()
                    groups.append('Persistent-profile lesson links stay blue across a fresh visit; screenshot pixels, hover, keyboard focus and unchanged understanding verified')
                finally:
                    profile.close()

                # Explicitly model a browser restoring session cookies after closing.
                # No assumption is made that every browser discards them at shutdown.
                saved_state = other_context.storage_state()
                other_context.close()
                for iteration in range(2):
                    reopened_browser = playwright.chromium.launch(headless=True)
                    try:
                        restored_context = reopened_browser.new_context(storage_state=saved_state)
                        restored_page = restored_context.new_page()
                        observe(restored_page)
                        if iteration == 0:
                            progress(restored_page)
                            expect(restored_page.locator('#total-quizzes')).to_have_text('1')
                            expect(restored_page.locator('#total-practice')).to_have_text('1')
                            restored_page.get_by_role('button', name='End Visit', exact=True).click()
                            expect(restored_page.get_by_text('Your visit has ended. Your learning data has been deleted.', exact=True)).to_be_visible()
                            restored_page.go_back()
                            expect(restored_page.get_by_label('Your name', exact=True)).to_be_visible()
                            expect(restored_page.locator('#activity-history')).to_have_count(0)
                        else:
                            # Restoring the older cookie cannot undo the server-side End Visit.
                            restored_page.goto(base + '/progress/')
                            expect(restored_page.get_by_label('Your name', exact=True)).to_be_visible()
                            expect(restored_page.get_by_role('heading', name='My Progress', exact=True)).to_have_count(0)
                            clean_context = reopened_browser.new_context()
                            clean_page = clean_context.new_page()
                            start(clean_page)
                            progress(clean_page)
                            for selector in ('#total-practice', '#total-exercises', '#total-quizzes'):
                                expect(clean_page.locator(selector)).to_have_text('0')
                            expect(clean_page.locator('[data-summary-status="Still Learning"]')).to_have_text('4')
                            clean_context.close()
                        restored_context.close()
                    finally:
                        reopened_browser.close()
                assert rows('SELECT COUNT(*) FROM learning_attempts') == [(0,)]
                assert not errors, errors
                groups.append('Browser close/reopen with restored cookies resumes only the same active visit; End Visit blocks old cookies; no-cookie visitor starts empty')
                context.close()
            finally:
                browser.close()
                server.shutdown()
                thread.join()
                server.server_close()
    assert not Path(directory).exists()
    report = {'passed_groups': groups, 'errors': errors, 'disposable_database_removed': True}
    (report_dir / 'browser-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir', type=Path, required=True)
    run(parser.parse_args().report_dir)
