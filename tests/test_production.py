"""Production boundary checks; every writable database/key uses /tmp."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from retention_support import learning_snapshot

import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from learning_with_francis import create_app, db
from learning_with_francis.production import production_config, prepare_database, create_production_app
from learning_with_francis.subjects import SUBJECTS
from test_phase2_sql import HiddenFields


class ProductionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="release-production-", dir="/tmp")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.env = {"LWF_SECRET_KEY": "disposable-production-test-key-123456789",
                    "LWF_DATA_DIR": str(self.directory / "data"),
                    "LWF_ALLOWED_HOSTS": "localhost"}
        self.path = Path(production_config(self.env)["DATABASE"])

    def app(self):
        prepare_database(self.env)
        return create_production_app(self.env)

    def rows(self, sql, args=()):
        with closing(db.open_database(self.path)) as connection:
            return [tuple(row) for row in connection.execute(sql, args)]

    def get(self, client, path):
        return client.get(path, base_url="https://localhost")

    def post(self, client, path, data):
        return client.post(path, data=data, base_url="https://localhost")

    def start(self, client):
        fields = HiddenFields(self.get(client, "/learn/").text).fields
        result = self.post(client, "/visits/start", {**fields, "visitor_name": "Release Learner"})
        self.assertEqual(result.status_code, 303)

    def test_missing_or_short_secret_fails_without_creating_data(self):
        for value in ("", "short", " " * 40):
            with self.subTest(value_length=len(value)), self.assertRaises(RuntimeError):
                prepare_database({**self.env, "LWF_SECRET_KEY": value})
        self.assertFalse(self.path.exists())

    def test_data_directory_must_be_absolute_private_and_outside_source(self):
        source = Path(__file__).resolve().parents[1]
        for value in ("", "relative", "/", str(source), str(source / "static/data")):
            with self.subTest(path=value), self.assertRaises(RuntimeError):
                production_config({**self.env, "LWF_DATA_DIR": value})

    def test_allowed_hosts_are_required_and_reject_wildcards_or_urls(self):
        for value in ("", "*", "https://example.com", "example.com:443", "example.com,", "../example.com"):
            with self.subTest(host=value), self.assertRaises(RuntimeError):
                production_config({**self.env, "LWF_ALLOWED_HOSTS": value})

    def test_render_hostname_is_supported_without_a_hardcoded_domain(self):
        env = dict(self.env)
        del env["LWF_ALLOWED_HOSTS"]
        env["RENDER_EXTERNAL_HOSTNAME"] = "learning-with-francis.onrender.com"
        self.assertEqual(production_config(env)["TRUSTED_HOSTS"], [env["RENDER_EXTERNAL_HOSTNAME"]])

    def test_fresh_database_has_no_visitor_or_demonstration_records(self):
        self.assertTrue(prepare_database(self.env))
        self.assertEqual(self.rows("PRAGMA user_version"), [(db.SCHEMA_VERSION,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM subjects"), [(4,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM topics"), [(4,)])
        for table in ("visits", "topic_progress", "topic_status_history", "learning_attempts", "learning_answers"):
            self.assertEqual(self.rows("SELECT COUNT(*) FROM " + table), [(0,)])
        self.assertEqual(self.path.stat().st_mode & 0o077, 0)

    def test_repeated_prepare_and_restart_preserve_saved_records(self):
        first = self.app()
        client = first.test_client()
        self.start(client)
        before = learning_snapshot(self.path)
        self.assertFalse(prepare_database(self.env))
        second = create_production_app(self.env)
        replacement = second.test_client()
        cookie = client.get_cookie(first.config["SESSION_COOKIE_NAME"])
        replacement.set_cookie(second.config["SESSION_COOKIE_NAME"], cookie.value)
        self.assertIn("Release Learner!", self.get(replacement, "/learn/").text)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_existing_invalid_database_is_never_replaced_or_upgraded(self):
        self.path.parent.mkdir()
        self.path.write_bytes(b"keep this unrelated file")
        before = self.path.read_bytes()
        with self.assertRaises(db.DatabaseSetupError):
            prepare_database(self.env)
        self.assertEqual(self.path.read_bytes(), before)

    def test_startup_requires_existing_valid_database(self):
        with self.assertRaises(db.DatabaseSetupError):
            create_production_app(self.env)
        self.assertFalse(self.path.exists())

    def test_secure_cookie_headers_and_no_audio_on_cover(self):
        app = self.app()
        client = app.test_client()
        response = self.get(client, "/")
        cookie = response.headers.get("Set-Cookie", "")
        for setting in ("Secure", "HttpOnly", "SameSite=Lax"):
            self.assertIn(setting, cookie)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("form-action 'self'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertNotIn("<audio", response.text)
        self.assertNotIn("cover-audio.js", response.text)
        self.assertFalse(app.debug)

    def test_12_hour_session_behavior_is_preserved(self):
        app = self.app()
        self.assertEqual(app.permanent_session_lifetime, timedelta(hours=12))
        client = app.test_client()
        self.start(client)
        issued = time.time()
        with patch("time.time", return_value=issued + 12 * 3600 + 5):
            self.assertEqual(self.get(client, "/progress/").status_code, 303)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM visits"), [(1,)])

    def test_untrusted_host_is_rejected_without_exposing_data(self):
        response = self.app().test_client().get("/", base_url="https://attacker.invalid")
        self.assertEqual(response.status_code, 400)

    def test_readiness_checks_database_without_writing_or_exposing_paths(self):
        client = self.app().test_client()
        before = learning_snapshot(self.path)
        response = self.get(client, "/healthz")
        self.assertEqual(response.json, {"status": "ok"})
        self.assertEqual(learning_snapshot(self.path), before)
        with patch.object(db, "get_db", side_effect=db.DatabaseSetupError("private-path")):
            response = self.get(client, "/healthz")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json, {"status": "unavailable"})
        self.assertNotIn("private-path", response.text)


    def test_same_name_isolation_and_ended_visit_replay_protection(self):
        app = self.app()
        first, second = app.test_client(), app.test_client()
        self.start(first)
        self.start(second)
        self.get(first, "/learn/")
        with first.session_transaction(base_url="https://localhost") as session:
            first_id, csrf = session["visit_id"], session["csrf_token"]
        with second.session_transaction(base_url="https://localhost") as session:
            self.assertNotEqual(first_id, session["visit_id"])
        old_cookie = first.get_cookie(app.config["SESSION_COOKIE_NAME"]).value
        self.assertEqual(self.post(first, "/visits/end", {"csrf_token": csrf}).status_code, 303)
        first.set_cookie(app.config["SESSION_COOKIE_NAME"], old_cookie)
        self.assertEqual(self.get(first, "/progress/").status_code, 303)
        self.assertEqual(self.get(second, "/progress/").status_code, 200)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(0,)])

    def test_four_subject_scores_retries_and_confirmation_are_unchanged(self):
        client = self.app().test_client()
        self.start(client)
        for slug, info in SUBJECTS.items():
            fields = HiddenFields(self.get(client, f"/{slug}/quiz").text).fields
            payload = {**fields, **{q["id"]: q["correct"] for q in info["content"].QUIZ}}
            first = self.post(client, f"/{slug}/quiz", payload)
            self.assertEqual(first.status_code, 303)
            self.assertEqual(self.post(client, f"/{slug}/quiz", payload).location, first.location)
            self.assertIn("5 out of 5", self.get(client, first.location).text)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(4,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(20,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM topic_progress WHERE learning_status='Completed'"), [(0,)])
        page = self.get(client, "/progress/")
        fields = HiddenFields(page.text).fields
        topic = SUBJECTS["sql"]["content"].TOPIC_ID
        path = f"/progress/{topic}/status"
        self.assertEqual(self.post(client, path, {**fields, "new_status": "Completed"}).status_code, 400)
        self.assertEqual(self.post(client, path, {**fields, "new_status": "Completed", "user_confirmed": "yes"}).status_code, 303)
        self.assertEqual(self.post(client, path, {**fields, "new_status": "Needs Review"}).status_code, 303)

    def test_concurrent_distinct_visits_preserve_integrity(self):
        app = self.app()
        def start(_):
            client = app.test_client()
            self.start(client)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(start, range(8)))
        self.assertEqual(self.rows("SELECT COUNT(DISTINCT visit_id) FROM visits"), [(8,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM topic_progress"), [(32,)])
        self.assertEqual(self.rows("PRAGMA integrity_check"), [("ok",)])
        self.assertEqual(self.rows("PRAGMA foreign_key_check"), [])

    def test_consistent_backup_restores_visit_owned_records_to_disposable_storage(self):
        client = self.app().test_client()
        self.start(client)
        backup = self.directory / "recovery" / "learning_with_francis.db"
        backup.parent.mkdir()
        with closing(db.open_database(self.path)) as source, closing(sqlite3.connect(backup)) as destination:
            source.backup(destination)
        recovered = create_production_app({**self.env, "LWF_DATA_DIR": str(backup.parent)})
        restored_client = recovered.test_client()
        cookie = client.get_cookie(recovered.config["SESSION_COOKIE_NAME"])
        restored_client.set_cookie(recovered.config["SESSION_COOKIE_NAME"], cookie.value)
        self.assertIn("Release Learner!", self.get(restored_client, "/learn/").text)
        with closing(db.open_database(backup)) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])


if __name__ == "__main__":
    unittest.main()
