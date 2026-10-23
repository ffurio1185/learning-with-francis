"""L1 real-browser checks with disposable current-schema data and loopback serving."""

from retention_support import learning_snapshot

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
    with tempfile.TemporaryDirectory(prefix="l1-browser-data-", dir="/tmp") as directory:
        path = Path(directory) / "learning.db"
        db.initialize_database(path)
        app = create_app({"TESTING": True, "DATABASE": str(path),
                          "SECRET_KEY": "disposable-l1-browser-key"})
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        before = learning_snapshot(path)

        def observe(page):
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: errors.append(f"{response.status} {response.url}")
                    if response.status >= 500 else None)
            page.on("console", lambda message: errors.append(message.text)
                    if message.type == "error" and "Failed to load resource" not in message.text else None)

        def language(page, code):
            with page.expect_response(lambda response: response.request.method == "POST"
                                      and response.url == base + "/preferences/language") as posted:
                page.get_by_role("button", name="Deutsch" if code == "de" else "English", exact=True).click()
            assert posted.value.status == 303
            expect(page.locator("html")).to_have_attribute("lang", code)
            expect(page.locator(f'button[value="{code}"]')).to_have_attribute("aria-pressed", "true")

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(locale="de-DE", viewport={"width": 1440, "height": 900})
                    page = context.new_page()
                    observe(page)
                    page.goto(base + "/")
                    expect(page.locator("html")).to_have_attribute("lang", "en")
                    expect(page.get_by_role("group", name="Language", exact=True)).to_be_visible()
                    for flag in page.locator(".language-options img").all():
                        expect(flag).to_have_attribute("alt", "")
                        assert flag.evaluate("el => el.complete && el.naturalWidth > 0")
                    language(page, "de")
                    expect(page.get_by_role("group", name="Sprache", exact=True)).to_be_visible()
                    expect(page.get_by_text("Lerne etwas Neues.", exact=False)).to_be_visible()
                    expect(page.get_by_role("link", name="EINTRETEN", exact=True)).to_have_attribute("href", "/learn/")
                    page.wait_for_timeout(1100)
                    page.screenshot(path=str(report_dir / "cover-german-desktop.png"), full_page=True)
                    assert learning_snapshot(path) == before
                    groups.append("English default even in German browser; German cover, selected control, translated labels and 303 redirect; no database writes")

                    page.reload()
                    for label in ("English", "Deutsch"):
                        page.keyboard.press("Tab")
                        control = page.get_by_role("button", name=label, exact=True)
                        expect(control).to_be_focused()
                        assert control.evaluate("el => getComputedStyle(el).outlineStyle") == "solid"
                        assert control.bounding_box()["height"] >= 44
                    page.keyboard.press("Tab")
                    expect(page.get_by_role("link", name="EINTRETEN", exact=True)).to_be_focused()
                    groups.append("Native language controls and entrance are keyboard reachable, clearly focused and at least 44px high")

                    for width, height in ((320, 640), (375, 812), (768, 1024), (844, 390)):
                        page.set_viewport_size({"width": width, "height": height})
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        controls = page.locator(".cover-languages").bounding_box()
                        content = page.locator(".cover-content").bounding_box()
                        assert controls["y"] + controls["height"] < content["y"]
                        for code in ("en", "de"):
                            box = page.locator(f'button[value="{code}"]').bounding_box()
                            assert box["x"] >= 0 and box["x"] + box["width"] <= width
                    page.set_viewport_size({"width": 320, "height": 640})
                    page.add_style_tag(content=":root { font-size: 200%; }")
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    controls = page.locator(".cover-languages").bounding_box()
                    content = page.locator(".cover-content").bounding_box()
                    assert controls["y"] + controls["height"] < content["y"]
                    page.screenshot(path=str(report_dir / "cover-german-mobile-enlarged.png"), full_page=True)
                    language(page, "en")
                    assert learning_snapshot(path) == before
                    groups.append("German desktop, phone, tablet, landscape and 200% text reflow without overlap or horizontal overflow; English switch works")
                    context.close()

                    for javascript, reduced in ((False, "no-preference"), (True, "reduce")):
                        context = browser.new_context(java_script_enabled=javascript, reduced_motion=reduced)
                        page = context.new_page()
                        observe(page)
                        page.goto(base + "/")
                        language(page, "de")
                        if reduced == "reduce":
                            assert page.locator("#welcome-cover").evaluate("el => getComputedStyle(el).animationName") == "none"
                        began = monotonic()
                        page.get_by_role("link", name="EINTRETEN", exact=True).click()
                        expect(page).to_have_url(base + "/learn/")
                        assert monotonic() - began < 1.1
                        # L2 now translates the application interface as well as retaining the preference.
                        expect(page.get_by_label("Dein Name", exact=True)).to_be_visible()
                        page.goto(base + "/")
                        expect(page.locator("html")).to_have_attribute("lang", "de")
                        context.close()
                    assert learning_snapshot(path) == before
                    groups.append("Language selection and ENTER work without JavaScript and with reduced motion; preference survives application navigation")

                    context = browser.new_context(reduced_motion="reduce")
                    other_context = browser.new_context(reduced_motion="reduce")
                    page, other = context.new_page(), other_context.new_page()
                    observe(page)
                    observe(other)
                    for current in (page, other):
                        current.goto(base + "/learn/")
                        current.get_by_label("Your name", exact=True).fill("Language Learner")
                        current.get_by_role("button", name="Start Visit", exact=True).click()
                        expect(current.get_by_role("heading", name="Welcome to Learning with Francis, Language Learner!")).to_be_visible()
                    saved = learning_snapshot(path)
                    page.goto(base + "/")
                    language(page, "de")
                    other.goto(base + "/")
                    expect(other.locator("html")).to_have_attribute("lang", "en")
                    assert learning_snapshot(path) == saved
                    for current in (page, other):
                        current.goto(base + "/progress/")
                        expect(current.locator("#no-activity")).to_be_visible()
                    assert learning_snapshot(path) == saved
                    with closing(db.open_database(path)) as connection:
                        assert connection.execute("SELECT COUNT(DISTINCT visit_id) FROM visits").fetchone()[0] == 2
                        assert connection.execute("SELECT COUNT(*) FROM learning_attempts").fetchone()[0] == 0
                    groups.append("Two same-name browser visitors keep separate identities and languages, zero activity and unchanged progress")

                    page.get_by_role("button", name="Besuch beenden", exact=True).click()
                    expect(page.get_by_label("Dein Name", exact=True)).to_be_visible()
                    page.goto(base + "/")
                    expect(page.locator("html")).to_have_attribute("lang", "de")
                    page.get_by_role("link", name="EINTRETEN", exact=True).click()
                    page.get_by_label("Dein Name", exact=True).fill("Language Learner")
                    page.get_by_role("button", name="Besuch starten", exact=True).click()
                    page.get_by_role("button", name="Neuen Besuch beginnen", exact=True).click()
                    expect(page.get_by_label("Dein Name", exact=True)).to_be_visible()
                    page.goto(base + "/")
                    expect(page.locator("html")).to_have_attribute("lang", "de")
                    with closing(db.open_database(path)) as connection:
                        assert connection.execute("SELECT COUNT(*) FROM visits").fetchone()[0] == 1
                        assert connection.execute("SELECT COUNT(*) FROM learning_attempts").fetchone()[0] == 0
                    groups.append("End Visit and Start New Visit retain German, revoke old access and preserve the other visitor")
                    context.close()
                    other_context.close()
                    assert not errors, errors
                finally:
                    browser.close()
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
    assert not Path(directory).exists()
    report = {"passed_groups": groups, "errors": errors, "disposable_database_removed": True}
    (report_dir / "language-browser-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    run(parser.parse_args().report_dir)
