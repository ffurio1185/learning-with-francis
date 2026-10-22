"""Optional real-browser cover checks using an independent disposable database.

Use the external Playwright setup described in browser_phase2_progress.py.
"""

import argparse
from contextlib import closing
import json
from pathlib import Path
import tempfile
from threading import Thread
from time import monotonic

from werkzeug.serving import make_server
from learning_with_francis import create_app, db


def run(report_dir):
    from playwright.sync_api import sync_playwright, expect

    report_dir.mkdir(parents=True, exist_ok=True)
    groups, errors = [], []
    with tempfile.TemporaryDirectory(prefix='cover-browser-data-', dir='/tmp') as directory:
        database = Path(directory) / 'learning.db'
        db.initialize_database(database)
        app = create_app({'TESTING': True, 'DATABASE': str(database),
                          'SECRET_KEY': 'disposable-cover-browser-key'})
        server = make_server('127.0.0.1', 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        before = database.read_bytes()

        def observe(page):
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('response', lambda response: errors.append(f'{response.status} {response.url}')
                    if response.status >= 500 else None)
            page.on('console', lambda message: errors.append(message.text)
                    if message.type == 'error' and 'Failed to load resource' not in message.text else None)

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(viewport={'width': 1440, 'height': 900})
                    page = context.new_page()
                    observe(page)
                    page.goto(base + '/')
                    expect(page.get_by_role('heading', level=1)).to_contain_text('Learning with Francis')
                    enter = page.get_by_role('link', name='ENTER', exact=True)
                    expect(enter).to_have_attribute('href', '/learn/')
                    assert page.locator('.cover-watermark').get_attribute('aria-hidden') == 'true'
                    page.wait_for_timeout(1200)
                    page.screenshot(path=str(report_dir / 'cover-desktop.png'), full_page=True)
                    assert page.locator('.cover-watermark').evaluate('el => getComputedStyle(el).opacity') == '1'
                    assert page.locator('h1').evaluate('el => getComputedStyle(el).opacity') == '1'
                    assert page.locator('a, button, input, select').count() == 1
                    enter.hover()
                    assert enter.evaluate('el => getComputedStyle(el).boxShadow') != 'none'
                    page.mouse.move(0, 0)
                    page.keyboard.press('Tab')
                    expect(enter).to_be_focused()
                    assert enter.evaluate('el => getComputedStyle(el).outlineStyle') == 'solid'
                    assert enter.bounding_box()['height'] >= 44
                    # The lightest blue in the gradient is the lowest contrast.
                    rgb = [int('216fcf'[i:i + 2], 16) / 255 for i in (0, 2, 4)]
                    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
                    assert 1.05 / (sum(v * w for v, w in zip(linear, (.2126, .7152, .0722))) + .05) >= 4.5
                    groups.append('Desktop cover, visible 4U/title, local assets, readable button contrast, hover and keyboard focus')

                    began = monotonic()
                    page.keyboard.press('Enter')
                    expect(page.locator('#welcome-cover')).to_have_class('welcome-cover is-entering')
                    # Repeated clicks must not restart the transition or send two navigations.
                    page.locator('#cover-enter').evaluate('el => el.click()')
                    expect(page).to_have_url(base + '/learn/')
                    elapsed = monotonic() - began
                    assert 1.1 <= elapsed <= 3, elapsed
                    expect(page.get_by_label('Your name', exact=True)).to_be_visible()
                    assert database.read_bytes() == before
                    groups.append(f'Keyboard ENTER and repeated activation navigate once after approximately 1.2 seconds ({elapsed:.2f}s); no database writes')

                    page.go_back()
                    expect(enter).to_be_visible()
                    expect(page.locator('#welcome-cover')).not_to_have_class('welcome-cover is-entering')
                    assert page.locator('#welcome-cover').get_attribute('aria-busy') is None
                    # Explicitly simulate a persisted pageshow, as engines may reload on Back.
                    page.evaluate('''() => {
                        const cover = document.querySelector('#welcome-cover');
                        cover.classList.add('is-entering');
                        cover.setAttribute('aria-busy', 'true');
                        dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}));
                    }''')
                    expect(page.locator('#welcome-cover')).not_to_have_class('welcome-cover is-entering')
                    expect(enter).to_be_visible()
                    groups.append('Back navigation and persisted pageshow restore a visible, usable cover')

                    for width, height in ((320, 640), (375, 812), (768, 1024), (844, 390)):
                        page.set_viewport_size({'width': width, 'height': height})
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        expect(enter).to_be_visible()
                        box = enter.bounding_box()
                        assert box['x'] >= 0 and box['x'] + box['width'] <= width
                        assert page.locator('h1').bounding_box()['width'] <= width
                    page.set_viewport_size({'width': 375, 'height': 812})
                    page.wait_for_timeout(1100)  # Back may reload and replay the initial title reveal.
                    page.screenshot(path=str(report_dir / 'cover-mobile.png'), full_page=True)
                    # Text enlargement must reflow instead of clipping the entrance.
                    page.add_style_tag(content=':root { font-size: 200%; }')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    expect(enter).to_be_visible()
                    groups.append('320px phone, tablet, landscape and 200% text layouts reflow without horizontal overflow')
                    context.close()

                    for reduced, javascript in (('reduce', True), ('no-preference', False)):
                        context = browser.new_context(reduced_motion=reduced, java_script_enabled=javascript)
                        page = context.new_page()
                        observe(page)
                        page.goto(base + '/')
                        if reduced == 'reduce':
                            for selector in ('#welcome-cover', '.cover-watermark', 'h1', '#cover-enter'):
                                assert page.locator(selector).evaluate('el => getComputedStyle(el).animationName') == 'none'
                        began = monotonic()
                        page.get_by_role('link', name='ENTER', exact=True).click()
                        expect(page).to_have_url(base + '/learn/')
                        assert monotonic() - began < 1.1
                        expect(page.get_by_label('Your name', exact=True)).to_be_visible()
                        context.close()
                    assert database.read_bytes() == before
                    groups.append('Reduced motion removes entrance animations/delay; disabled JavaScript follows the normal link; no activity created')

                    context = browser.new_context(viewport={'width': 375, 'height': 812},
                                                  is_mobile=True, has_touch=True, device_scale_factor=2)
                    page = context.new_page()
                    observe(page)
                    page.goto(base + '/')
                    page.wait_for_timeout(1100)
                    page.get_by_role('link', name='ENTER', exact=True).tap()
                    expect(page).to_have_url(base + '/learn/')
                    expect(page.get_by_label('Your name', exact=True)).to_be_visible()
                    assert database.read_bytes() == before
                    context.close()
                    groups.append('Touch-enabled mobile viewport enters the existing application without creating a visit')

                    context = browser.new_context(reduced_motion='reduce')
                    page = context.new_page()
                    observe(page)
                    page.goto(base + '/learn/')
                    page.get_by_label('Your name', exact=True).fill('Cover Learner')
                    page.get_by_role('button', name='Start Visit', exact=True).click()
                    expect(page.get_by_role('heading', name='Welcome to Learning with Francis, Cover Learner!')).to_be_visible()
                    with closing(db.open_database(database)) as connection:
                        visit_id = connection.execute('SELECT visit_id FROM visits').fetchone()[0]
                    saved = database.read_bytes()
                    for _ in range(2):
                        page.goto(base + '/')
                        expect(page.locator('#welcome-cover')).to_be_visible()
                        expect(page.get_by_text('Cover Learner', exact=True)).to_have_count(0)
                        page.get_by_role('link', name='ENTER', exact=True).click()
                        expect(page.get_by_role('heading', name='Welcome to Learning with Francis, Cover Learner!')).to_be_visible()
                    assert database.read_bytes() == saved
                    with closing(db.open_database(database)) as connection:
                        assert connection.execute('SELECT visit_id FROM visits').fetchall()[0][0] == visit_id
                        assert connection.execute('SELECT COUNT(*) FROM visits').fetchone()[0] == 1
                        assert connection.execute('SELECT COUNT(*) FROM learning_attempts').fetchone()[0] == 0
                    page.get_by_role('link', name='Open SQL lesson', exact=True).click()
                    expect(page.get_by_role('link', name='My Progress', exact=True)).to_be_visible()
                    page.get_by_role('link', name='My Progress', exact=True).click()
                    expect(page.get_by_role('heading', name='My Progress', exact=True)).to_be_visible()
                    groups.append('Root always shows cover; ENTER resumes the same visit without new records; SQL and progress navigation remain connected')
                    context.close()
                    assert not errors, errors
                finally:
                    browser.close()
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
    assert not Path(directory).exists()
    report = {'passed_groups': groups, 'errors': errors, 'disposable_database_removed': True}
    (report_dir / 'cover-browser-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir', type=Path, required=True)
    run(parser.parse_args().report_dir)
