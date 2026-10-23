"""Real Gunicorn release smoke checks using disposable /tmp data only.

Uses Render's HTTP-backend topology on trusted localhost; Render supplies public
TLS later. Requires external Playwright/Chromium. No external service calls.
"""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from learning_with_francis import db
from learning_with_francis.subjects import SUBJECTS


def run(report_dir):
    from playwright.sync_api import sync_playwright, expect
    report_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    groups, errors = [], []
    with tempfile.TemporaryDirectory(prefix="release-gunicorn-", dir="/tmp") as directory:
        private = Path(directory)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        env = {**os.environ, "LWF_SECRET_KEY": secrets.token_urlsafe(48),
               "LWF_DATA_DIR": str(private / "data"), "LWF_ALLOWED_HOSTS": "127.0.0.1,localhost",
               "LWF_BIND_HOST": "127.0.0.1", "PORT": str(port), "LWF_DEMO_MODE": "1",
               "GUNICORN_CMD_ARGS": "",
               "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
               "PYTHONDONTWRITEBYTECODE": "1"}
        base = f"http://localhost:{port}"
        path = private / "data/learning_with_francis.db"
        log = (report_dir / "gunicorn.log").open("w")
        process = None

        def start_server():
            process = subprocess.Popen(["sh", "render-start.sh"], cwd=root, env=env,
                                       stdout=log, stderr=subprocess.STDOUT)
            for _ in range(100):
                if process.poll() is not None:
                    raise AssertionError("Gunicorn startup failed; inspect the local test log.")
                try:
                    with urllib.request.urlopen(base + "/healthz", timeout=1) as response:
                        assert json.load(response) == {"status": "ok"}
                    return process
                except OSError:
                    time.sleep(0.1)
            process.terminate()
            process.wait(timeout=10)
            raise AssertionError("Gunicorn readiness timed out")

        def rows(sql):
            with closing(db.open_database(path)) as connection:
                return [tuple(row) for row in connection.execute(sql)]

        try:
            process = start_server()
            assert rows("SELECT COUNT(*) FROM visits") == [(0,)]
            groups.append("Actual start script creates fresh schema 3 and Gunicorn serves HTTP-backend readiness on loopback")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(reduced_motion="reduce")
                    page = context.new_page()
                    requested = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("request", lambda request: requested.append(request.url))
                    page.on("response", lambda response: errors.append(str(response.status)) if response.status >= 500 else None)
                    page.goto(base + "/")
                    expect(page.get_by_role("link", name="ENTER", exact=True)).to_be_visible()
                    expect(page.get_by_role("complementary", name="Public learning demonstration")).to_contain_text("may be lost")
                    assert page.locator("audio").count() == 0
                    assert not any(".mp3" in url or "/audio/" in url for url in requested)
                    page.get_by_role("button", name="Deutsch", exact=True).click()
                    expect(page.locator("html")).to_have_attribute("lang", "de")
                    page.get_by_role("link", name="EINTRETEN", exact=True).click()
                    expect(page.locator(".demo-notice")).to_contain_text("verloren gehen")
                    page.get_by_label("Dein Name", exact=True).fill("Release Learner")
                    page.get_by_role("button", name="Besuch starten", exact=True).click()
                    expect(page.get_by_role("heading", level=2).first).to_contain_text("Release Learner")
                    assert any(c["secure"] and c["httpOnly"] and c["sameSite"] == "Lax" for c in context.cookies())
                    groups.append("Silent bilingual cover, ENTER, personalised visit and real Secure/HttpOnly/SameSite cookies")

                    for slug, info in SUBJECTS.items():
                        page.goto(base + f"/{slug}/")
                        expect(page.locator("h1")).to_contain_text(info["name"])
                        content = info["content"]
                        page.goto(base + f"/{slug}/practice")
                        question = content.PRACTICE[0]
                        page.locator(f'input[name="{question["id"]}"][value="{question["correct"]}"]').check()
                        page.locator("#activity-form button[type=submit]").click()
                        expect(page.locator("#score")).to_contain_text("1 von 1")
                        expect(page.locator("#practice-next")).to_be_visible()
                        page.goto(base + f"/{slug}/quiz")
                        for question in content.QUIZ:
                            page.locator(f'input[name="{question["id"]}"][value="{question["correct"]}"]').check()
                        page.locator("#activity-form button[type=submit]").click()
                        expect(page.locator("#score")).to_contain_text("5 von 5")
                        expect(page.locator("#personal-feedback")).to_contain_text("Release Learner")
                        page.reload()
                    assert rows("SELECT COUNT(*) FROM learning_attempts") == [(8,)]
                    assert rows("SELECT COUNT(*) FROM learning_answers") == [(24,)]
                    assert rows("SELECT COUNT(*) FROM topic_progress WHERE learning_status='Completed'") == [(0,)]
                    groups.append("Four German lessons, immediate practice feedback, full quiz scoring, persistent answers and refresh deduplication under production headers")

                    page.goto(base + "/progress/")
                    first = page.locator(".status-form").first
                    first.locator("select").select_option("Completed")
                    first.locator('button[type="submit"]').click()
                    expect(first.locator(".confirmation-error")).to_be_visible()
                    first.locator('input[type="checkbox"]').check()
                    first.locator('button[type="submit"]').click()
                    expect(page.locator(".status-form").first.locator("select")).to_have_value("Completed")
                    page.get_by_role("button", name="English", exact=True).click()
                    expect(page.locator("html")).to_have_attribute("lang", "en")
                    page.screenshot(path=str(report_dir / "production-progress.png"), full_page=True)
                    groups.append("Production CSP permits filters/forms; explicit confirmation and language switching preserve real progress")

                    before = path.read_bytes()
                    process.terminate()
                    process.wait(timeout=15)
                    process = start_server()
                    page.reload()
                    expect(page.locator(".status-form").first.locator("select")).to_have_value("Completed")
                    assert path.read_bytes() == before
                    groups.append("Real Gunicorn stop/start preserves database bytes, stable signed session and saved status")

                    other = browser.new_context(java_script_enabled=False)
                    second = other.new_page()
                    second.goto(base + "/learn/")
                    second.get_by_label("Your name", exact=True).fill("Release Learner")
                    second.get_by_role("button", name="Start Visit", exact=True).click()
                    second.goto(base + "/progress/")
                    expect(second.locator("#no-activity")).to_be_visible()
                    form = second.locator(".status-form").first
                    form.locator("select").select_option("Completed")
                    form.locator('button[type="submit"]').click()
                    expect(second.locator(".visit-error")).to_be_visible()
                    assert rows("SELECT COUNT(*) FROM visits") == [(2,)]
                    assert rows("SELECT COUNT(*) FROM learning_attempts") == [(8,)]
                    groups.append("Independent same-name visitor has zero activity; Python rejects unconfirmed completion without JavaScript")
                    other.close()
                    for locale, heading in (("en", "Public learning demonstration"), ("de", "Öffentliche Lern-Demo")):
                        page.get_by_role("button", name="English" if locale == "en" else "Deutsch", exact=True).click()
                        for width in (320, 375, 1440):
                            page.set_viewport_size({"width": width, "height": 850})
                            expect(page.get_by_role("complementary", name=heading)).to_be_visible()
                            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                        page.add_style_tag(content="html { font-size: 200%; }")
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                        page.reload()
                    page.screenshot(path=str(report_dir / "free-demo-german.png"), full_page=True)
                    groups.append("Bilingual demo notice remains readable at mobile/desktop widths and enlarged text")

                    saved = path.read_bytes()
                    process.terminate()
                    process.wait(timeout=15)
                    env["LWF_DATA_DIR"] = str(private / "replacement-instance")
                    process = start_server()
                    old_path = path
                    path = private / "replacement-instance/learning_with_francis.db"
                    page.goto(base + "/progress/")
                    expect(page).to_have_url(base + "/learn/")
                    expect(page.get_by_label("Dein Name", exact=True)).to_be_visible()
                    assert rows("SELECT COUNT(*) FROM visits") == [(0,)]
                    assert rows("SELECT COUNT(*) FROM learning_attempts") == [(0,)]
                    page.get_by_label("Dein Name", exact=True).fill("Release Learner")
                    page.get_by_role("button", name="Besuch starten", exact=True).click()
                    page.goto(base + "/progress/")
                    expect(page.locator("#no-activity")).to_be_visible()
                    assert rows("SELECT COUNT(*) FROM topic_progress WHERE learning_status='Still Learning'") == [(4,)]
                    assert old_path.read_bytes() == saved
                    groups.append("Simulated lost Free instance storage creates fresh data; old browser session safely returns to name entry with zero activity")
                    context.close()
                finally:
                    browser.close()
            assert rows("PRAGMA integrity_check") == [("ok",)]
            assert rows("PRAGMA foreign_key_check") == []
            assert not errors, errors
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
            log.close()
    assert not Path(directory).exists()
    report = {"passed_groups": groups, "errors": errors, "disposable_database_removed": True}
    (report_dir / "browser-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    run(parser.parse_args().report_dir)
