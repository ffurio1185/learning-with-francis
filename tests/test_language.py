"""L1 preferences/security; every writable database is disposable under /tmp."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from retention_support import learning_snapshot

import gettext
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from babel.messages.pofile import read_po
from flask_babel import get_locale
from werkzeug.datastructures import MultiDict

from learning_with_francis import create_app, db
from learning_with_francis.i18n import current_language
from test_phase2_sql import SQLFlowSupport


class LanguageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="l1-language-", dir="/tmp")
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "learning.db"
        self.config = {"TESTING": True, "DATABASE": str(self.path),
                       "SECRET_KEY": "disposable-l1-test-key"}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def token(self, client=None):
        client = client or self.client
        client.get("/")
        with client.session_transaction() as session:
            return session["csrf_token"]

    def choose(self, language="de", client=None, **extra):
        client = client or self.client
        return client.post("/preferences/language", data={"language": language,
                           "csrf_token": self.token(client), **extra})

    def test_english_default_ignores_browser_headers_and_query_parameters(self):
        response = self.client.get("/?language=de", headers={"Accept-Language": "de-DE,de;q=0.9"})
        self.assertIn('<html lang="en">', response.text)
        self.assertIn("Learn something new.", response.text)
        with self.client.session_transaction() as session:
            self.assertEqual(set(session), {"csrf_token"})

    def test_both_cover_languages_and_fixed_local_redirect(self):
        for language, title, enter in (("de", "Willkommen bei", "EINTRETEN"),
                                        ("en", "Welcome to", "ENTER")):
            response = self.choose(language, next="https://example.invalid/", visit_id="forged")
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.location, "/")
            html = self.client.get("/").text
            self.assertIn(f'<html lang="{language}">', html)
            self.assertIn(title, html)
            self.assertIn(f"<span>{enter}</span>", html)
            self.assertIn(f'value="{language}" aria-pressed="true"', html)
            self.assertIn('lang="en">English', html)
            self.assertIn('lang="de">Deutsch', html)
            with self.client.session_transaction() as session:
                self.assertEqual(set(session), {"language", "csrf_token"})

    def test_language_actions_never_open_or_initialize_database(self):
        with patch.object(db, "get_db", side_effect=AssertionError("Language used database")):
            self.assertEqual(self.client.get("/").status_code, 200)
            self.assertEqual(self.choose().status_code, 303)
            self.assertEqual(self.client.get("/").status_code, 200)
        self.assertFalse(self.path.exists())

    def test_missing_and_forged_csrf_fail_without_changing_preference(self):
        self.choose()
        for data in ({"language": "en"}, {"language": "en", "csrf_token": "forged"},
                     {"language": "en", "csrf_token": "Ü"}):
            response = self.client.post("/preferences/language", data=data)
            self.assertEqual(response.status_code, 400)
            self.assertIn('role="alert"', response.text)
            self.assertIn("Dieses Formular ist abgelaufen.", response.text)
            with self.client.session_transaction() as session:
                self.assertEqual(session["language"], "de")

    def test_other_browser_csrf_token_is_rejected(self):
        foreign = self.token(self.app.test_client())
        self.token()
        self.assertEqual(self.client.post("/preferences/language", data={"language": "de", "csrf_token": foreign}).status_code, 400)
        with self.client.session_transaction() as session:
            self.assertNotIn("language", session)

    def test_unsupported_missing_duplicate_and_injected_language_fail(self):
        self.choose()
        token = self.token()
        cases = [MultiDict([("csrf_token", token)])]
        cases += [MultiDict([("csrf_token", token), ("language", value)])
                  for value in ("", "DE", "de-DE", "fr", "../de", "<script>alert(1)</script>", "en\x00")]
        cases += [MultiDict([("csrf_token", token), ("language", "en"), ("language", "de")])]
        cases += [MultiDict([("csrf_token", token), ("csrf_token", token), ("language", "en")])]
        for data in cases:
            with self.subTest(data=data):
                response = self.client.post("/preferences/language", data=data)
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("<script>alert", response.text)
                with self.client.session_transaction() as session:
                    self.assertEqual(session["language"], "de")

    def test_get_cannot_change_language_and_session_cookie_has_protections(self):
        response = self.client.get("/")
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])
        self.assertIn("SameSite=Lax", response.headers["Set-Cookie"])
        self.assertEqual(self.client.get("/preferences/language?language=de").status_code, 405)
        secure = create_app({**self.config, "SESSION_COOKIE_SECURE": True}).test_client()
        self.assertIn("Secure;", secure.get("/", base_url="https://localhost").headers["Set-Cookie"])

    def test_language_and_error_responses_are_not_cached(self):
        self.assertEqual(self.client.get("/").headers["Cache-Control"], "no-store")
        self.assertEqual(self.choose().headers["Cache-Control"], "no-store")
        response = self.client.post("/preferences/language", data={"language": "en"})
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_invalid_signed_locale_falls_back_to_english(self):
        for value in (None, "../de", ["de"], {"language": "de"}, 12):
            with self.subTest(value=value):
                with self.client.session_transaction() as session:
                    session["language"] = value
                self.assertIn('<html lang="en">', self.client.get("/").text)

    def test_forged_cookie_does_not_select_german_or_a_visitor(self):
        self.choose()
        name = self.app.config["SESSION_COOKIE_NAME"]
        cookie = self.client.get_cookie(name).value
        self.client.set_cookie(name, cookie + "tampered")
        self.assertIn('<html lang="en">', self.client.get("/").text)
        with self.client.session_transaction() as session:
            self.assertEqual(set(session), {"csrf_token"})

    def test_preference_survives_new_app_with_same_signing_key(self):
        self.choose()
        name = self.app.config["SESSION_COOKIE_NAME"]
        new_client = create_app(self.config).test_client()
        new_client.set_cookie(name, self.client.get_cookie(name).value)
        self.assertIn('<html lang="de">', new_client.get("/").text)
        self.assertFalse(self.path.exists())

    def test_simultaneous_visitors_do_not_share_a_global_language(self):
        def render(language):
            client = self.app.test_client()
            self.choose(language, client)
            return [client.get("/").text for _ in range(3)]
        with ThreadPoolExecutor(max_workers=2) as executor:
            pages = list(executor.map(render, ("en", "de")))
        for language, results in zip(("en", "de"), pages):
            self.assertTrue(all(f'<html lang="{language}">' in page for page in results))

    def test_catalog_source_and_compiled_runtime_messages_match(self):
        directory = Path(self.app.root_path) / "translations"
        with (directory / "messages.pot").open("rb") as handle:
            template = read_po(handle)
        with (directory / "de/LC_MESSAGES/messages.po").open("rb") as handle:
            german = read_po(handle, locale="de")
        with (directory / "de/LC_MESSAGES/messages.mo").open("rb") as handle:
            compiled = gettext.GNUTranslations(handle)
        self.assertEqual({m.id for m in template if m.id}, {m.id for m in german if m.id})
        for message in german:
            if message.id:
                self.assertTrue(message.string)
                self.assertNotIn("fuzzy", message.flags)
                self.assertFalse(list(message.check()))
                self.assertEqual(compiled.gettext(message.id), message.string)


class LanguageVisitTests(SQLFlowSupport, unittest.TestCase):
    def choose(self, language, client=None):
        client = client or self.client
        fields = self.fields("quiz", client)  # Existing protected form; no write.
        response = client.post("/preferences/language", data={"language": language, "csrf_token": fields["csrf_token"]})
        self.assertEqual(response.status_code, 303)

    def test_switch_preserves_actual_results_owner_statuses_and_open_quiz(self):
        self.submit(3)
        self.submit(1, "practice")
        data = self.payload(5)
        before = learning_snapshot(self.path)
        with self.client.session_transaction() as session:
            old = dict(session)
        self.choose("de")
        self.assertEqual(learning_snapshot(self.path), before)
        with self.client.session_transaction() as session:
            self.assertEqual({k: v for k, v in session.items() if k != "language"}, old)
        # Language is a preference: saved SQL identifiers/answers remain canonical.
        self.assertEqual(self.client.post("/sql/quiz", data=data).status_code, 303)
        self.assertEqual(self.rows("SELECT score FROM learning_attempts WHERE activity_kind = 'quiz' ORDER BY rowid"), [(3,), (5,)])
        self.assertEqual(self.rows("SELECT DISTINCT learning_status FROM topic_progress"), [("Still Learning",)])


    def test_visit_start_preserves_only_valid_language_and_clears_old_tokens(self):
        self.choose("de")
        with self.client.session_transaction() as session:
            previous_id = session["visit_id"]
            token = session["csrf_token"]
            session["unrelated"] = "must not survive"
        response = self.client.post("/visits/start", data={"visitor_name": "Francis", "csrf_token": token})
        self.assertEqual(response.status_code, 303)
        with self.client.session_transaction() as session:
            self.assertEqual(set(session), {"visit_id", "language"})
            self.assertEqual(session["language"], "de")
            self.assertNotEqual(session["visit_id"], previous_id)
        self.assertEqual(self.client.post("/preferences/language", data={"language": "en", "csrf_token": token}).status_code, 400)

    def test_end_and_new_visit_keep_language_but_revoke_previous_identity(self):
        for route in ("end", "new"):
            self.choose("de")
            with self.client.session_transaction() as session:
                previous_id = session["visit_id"]
                token = session["csrf_token"]
            self.assertEqual(self.client.post("/visits/" + route, data={"csrf_token": token}).status_code, 303)
            with self.client.session_transaction() as session:
                self.assertNotIn("visit_id", session)
                self.assertEqual(session["language"], "de")
                self.assertNotIn("csrf_token", session)
            self.assertEqual(self.rows("SELECT * FROM visits WHERE visit_id = ?", (previous_id,)), [])
            self.assertEqual(self.client.get("/progress/").location, "/learn/")
            self.start(self.client)
            with self.client.session_transaction() as session:
                self.assertEqual(session["language"], "de")
                self.assertNotEqual(session["visit_id"], previous_id)

    def test_same_name_visitors_with_different_languages_keep_separate_records(self):
        other = self.app.test_client()
        self.start(other)
        self.choose("de")
        self.choose("en", other)
        first = self.submit(5)
        before = learning_snapshot(self.path)
        self.assertEqual(other.get(first.location).status_code, 404)
        self.assertIn("No practice or quiz activity yet", other.get("/progress/").text)
        self.assertIn("5 / 5 richtig", self.client.get("/progress/").text)
        self.assertEqual(learning_snapshot(self.path), before)
        self.assertIn('<html lang="de">', self.client.get("/").text)
        self.assertIn('<html lang="en">', other.get("/").text)


    def test_invalid_preference_is_discarded_at_visit_boundary(self):
        with self.client.session_transaction() as session:
            session["language"] = "fr"
        self.start(self.client)
        with self.client.session_transaction() as session:
            self.assertNotIn("language", session)
        self.assertIn('<html lang="en">', self.client.get("/").text)


if __name__ == "__main__":
    unittest.main()
