"""P2.2 integration, isolation and setup tests. Every database/key lives in /tmp."""

from contextlib import closing
from pathlib import Path
import secrets
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from learning_with_francis import create_app, db
from learning_with_francis.security import load_signing_key


class VisitorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="p22-visitors-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "visits.db"
        self.config = {"TESTING": True, "DATABASE": str(self.path),
                       "SECRET_KEY_FILE": str(self.root / "private" / "signing-key")}
        self.app = create_app(self.config)
        db.initialize_database(self.path)
        self.client = self.app.test_client()

    def query(self, sql, params=()):
        with closing(db.open_database(self.path)) as connection:
            return [tuple(row) for row in connection.execute(sql, params).fetchall()]

    def csrf(self, client=None):
        client = client or self.client
        client.get("/learn/")
        with client.session_transaction() as session:
            return session["csrf_token"]

    def start(self, name="Francis", client=None, **extra):
        client = client or self.client
        return client.post("/visits/start", data={"visitor_name": name,
                            "csrf_token": self.csrf(client), **extra})

    def visit_id(self, client=None):
        with (client or self.client).session_transaction() as session:
            return session.get("visit_id")

    def finish(self, route="end", client=None, **extra):
        client = client or self.client
        return client.post(f"/visits/{route}", data={"csrf_token": self.csrf(client), **extra})

    def test_welcome_and_four_subjects_without_creating_records(self):
        response = self.client.get("/learn/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for text in ("Your name", "Start Visit", "SQL", "Python", "JavaScript", "SAP"):
            self.assertIn(text, html)
        self.assertEqual(self.query("SELECT COUNT(*) FROM visits"), [(0,)])
        with self.client.get("/static/phase2.css") as response:
            self.assertEqual(response.status_code, 200)
        self.assertNotIn('href="/sql/"', html)  # Start a visit before opening the lesson.

    def test_start_greeting_random_id_and_initial_history(self):
        response = self.start("  Francis  ")
        self.assertEqual(response.status_code, 303)
        visit_id = self.visit_id()
        self.assertGreaterEqual(len(visit_id), 40)
        self.assertNotIn("Francis", visit_id)
        self.assertIn("Welcome to Learning with Francis, Francis!", self.client.get("/learn/").get_data(as_text=True))
        self.assertEqual(self.query("SELECT display_name, ended_at FROM visits"), [("Francis", None)])
        rows = self.query("SELECT learning_status, understanding_confirmed_at FROM topic_progress")
        self.assertEqual(rows, [("Still Learning", None)] * 4)
        self.assertEqual(self.query("SELECT previous_status, new_status, user_confirmed FROM topic_status_history"),
                         [(None, "Still Learning", 0)] * 4)
        self.assertTrue(all(row[0] for row in self.query("SELECT changed_at FROM topic_status_history")))

    def test_different_visitors_have_separate_greetings_and_progress(self):
        other = self.app.test_client()
        self.start("Francis")
        self.start("Alex", other)
        self.assertNotEqual(self.visit_id(), self.visit_id(other))
        first_html = self.client.get("/learn/").get_data(as_text=True)
        other_html = other.get("/learn/").get_data(as_text=True)
        self.assertIn("Francis!", first_html)
        self.assertNotIn("Alex!", first_html)
        self.assertIn("Alex!", other_html)
        self.assertEqual(self.query("SELECT COUNT(*) FROM topic_progress"), [(8,)])

    def test_identical_names_never_recover_or_share_progress(self):
        other = self.app.test_client()
        self.start()
        first_id = self.visit_id()
        with closing(db.open_database(self.path)) as connection:
            # Fixture only: stand in for later progress features without adding them now.
            connection.execute("UPDATE topic_progress SET learning_status = 'Needs Review' WHERE visit_id = ?",
                               (first_id,))
            connection.commit()
        self.start("Francis", other)
        self.assertNotEqual(first_id, self.visit_id(other))
        self.assertIn("Needs Review", self.client.get("/learn/").get_data(as_text=True))
        self.assertNotIn("Needs Review", other.get("/learn/").get_data(as_text=True))
        self.assertEqual(self.query("SELECT COUNT(*) FROM visits WHERE display_name = 'Francis'"), [(2,)])

    def test_invalid_names_are_rejected_without_writing(self):
        token = self.csrf()
        before = self.path.read_bytes()
        for name in ("", "   ", "A" * 51, "1234", "<script>alert(1)</script>", "A\nB", "A\x00B", "--"):
            with self.subTest(name=repr(name)):
                response = self.client.post("/visits/start", data={"visitor_name": name, "csrf_token": token})
                self.assertEqual(response.status_code, 400)
                self.assertIn('role="alert"', response.get_data(as_text=True))
                self.assertEqual(self.path.read_bytes(), before)
        self.assertIsNone(self.visit_id())

    def test_international_names_apostrophes_and_html_escaping(self):
        for name in ("José", "王明", "O'Neil", "Anne-Marie"):
            with self.subTest(name=name):
                self.assertEqual(self.start(name).status_code, 303)
                html = self.client.get("/learn/").get_data(as_text=True)
                self.assertIn("Welcome to Learning with Francis,", html)
                self.assertEqual(self.query("SELECT display_name FROM visits WHERE visit_id = ?", (self.visit_id(),)), [(name,)])
        self.assertIn("O&#39;Neil", self.app.jinja_env.from_string("{{ name }}").render(name="O'Neil"))

    def test_missing_and_duplicate_name_values_are_rejected(self):
        from werkzeug.datastructures import MultiDict
        token = self.csrf()
        for data in ({"csrf_token": token}, MultiDict([("csrf_token", token), ("visitor_name", "One"), ("visitor_name", "Two")])):
            self.assertEqual(self.client.post("/visits/start", data=data).status_code, 400)
        self.assertEqual(self.query("SELECT COUNT(*) FROM visits"), [(0,)])

    def test_get_refresh_and_all_assets_do_not_duplicate_visits(self):
        self.start()
        before = self.path.read_bytes()
        for path in ("/learn/", "/learn/", "/static/style.css", "/static/phase2.css"):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)
        self.assertEqual(self.path.read_bytes(), before)

    def test_csrf_required_on_every_mutating_route(self):
        self.start()
        before = self.path.read_bytes()
        for route in ("start", "end", "new"):
            for token in (None, "forged", "forgé"):
                data = {"visitor_name": "Other"}
                if token is not None:
                    data["csrf_token"] = token
                self.assertEqual(self.client.post(f"/visits/{route}", data=data).status_code, 400)
        self.assertEqual(self.path.read_bytes(), before)

    def test_cross_session_csrf_is_rejected(self):
        other = self.app.test_client()
        token = self.csrf()
        self.csrf(other)
        self.assertEqual(other.post("/visits/start", data={"visitor_name": "Alex", "csrf_token": token}).status_code, 400)
        self.assertEqual(self.query("SELECT COUNT(*) FROM visits"), [(0,)])

    def test_end_visit_revokes_cookie_and_preserves_all_saved_progress(self):
        self.start()
        visit_id = self.visit_id()
        cookie = self.client.get_cookie(self.app.config["SESSION_COOKIE_NAME"]).value
        progress_before = self.query("SELECT * FROM topic_progress")
        history_before = self.query("SELECT * FROM topic_status_history")
        self.assertEqual(self.finish().status_code, 303)
        self.assertIsNone(self.visit_id())
        self.assertIsNotNone(self.query("SELECT ended_at FROM visits WHERE visit_id = ?", (visit_id,))[0][0])
        self.assertEqual(self.query("SELECT * FROM topic_progress"), progress_before)
        self.assertEqual(self.query("SELECT * FROM topic_status_history"), history_before)
        replay = self.app.test_client()
        replay.set_cookie(self.app.config["SESSION_COOKIE_NAME"], cookie)
        html = replay.get("/learn/").get_data(as_text=True)
        self.assertNotIn("Francis!", html)
        self.assertIsNone(self.visit_id(replay))

    def test_new_visit_requires_name_and_creates_fresh_rows(self):
        self.start()
        old_id = self.visit_id()
        before_progress = self.query("SELECT * FROM topic_progress")
        self.assertEqual(self.finish("new").status_code, 303)
        self.assertIn("Start a fresh visit", self.client.get("/learn/").get_data(as_text=True))
        self.assertIsNone(self.visit_id())
        self.assertEqual(self.start().status_code, 303)
        self.assertNotEqual(old_id, self.visit_id())
        self.assertEqual(self.query("SELECT * FROM topic_progress WHERE visit_id = ?", (old_id,)), before_progress)
        self.assertEqual(self.query("SELECT learning_status FROM topic_progress WHERE visit_id = ?", (self.visit_id(),)), [("Still Learning",)] * 4)
        self.assertEqual(self.query("SELECT COUNT(*) FROM visits"), [(2,)])

    def test_direct_start_ends_only_own_previous_visit(self):
        other = self.app.test_client()
        self.start()
        self.start("Alex", other)
        old_id = self.visit_id()
        other_id = self.visit_id(other)
        self.start("New Name")
        self.assertIsNotNone(self.query("SELECT ended_at FROM visits WHERE visit_id = ?", (old_id,))[0][0])
        self.assertEqual(self.query("SELECT ended_at FROM visits WHERE visit_id = ?", (other_id,)), [(None,)])

    def test_invalid_new_name_does_not_end_existing_visit(self):
        self.start()
        old_id = self.visit_id()
        self.assertEqual(self.start(" ").status_code, 400)
        self.assertEqual(self.visit_id(), old_id)
        self.assertEqual(self.query("SELECT ended_at FROM visits"), [(None,)])

    def test_spoofed_owner_ids_in_form_and_query_are_ignored(self):
        other = self.app.test_client()
        self.start()
        self.start("Alex", other)
        other_id = self.visit_id(other)
        other_progress = self.query("SELECT * FROM topic_progress WHERE visit_id = ?", (other_id,))
        html = self.client.get("/learn/?visit_id=" + other_id).get_data(as_text=True)
        self.assertNotIn("Alex!", html)
        self.assertEqual(self.finish(visit_id=other_id).status_code, 303)
        self.assertEqual(self.query("SELECT ended_at FROM visits WHERE visit_id = ?", (other_id,)), [(None,)])
        self.assertEqual(self.query("SELECT * FROM topic_progress WHERE visit_id = ?", (other_id,)), other_progress)
        for method in (self.client.get, self.client.post):
            self.assertEqual(method("/visits/" + other_id).status_code, 404)

    def test_tampered_or_unknown_visit_cookie_cannot_read_records(self):
        self.start()
        name = self.app.config["SESSION_COOKIE_NAME"]
        cookie = self.client.get_cookie(name).value
        attacker = self.app.test_client()
        payload, signature = cookie.rsplit(".", 1)
        # Change actual signature bytes, not unused padding bits in its final character.
        forged_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
        attacker.set_cookie(name, payload + "." + forged_signature)
        self.assertNotIn("Francis!", attacker.get("/learn/").get_data(as_text=True))
        with attacker.session_transaction() as session:
            session["visit_id"] = secrets.token_urlsafe(32)
        self.assertNotIn("Francis!", attacker.get("/learn/").get_data(as_text=True))

    def test_cookie_is_private_signed_and_does_not_contain_the_name(self):
        token = self.csrf()
        response = self.client.post("/visits/start", data={"visitor_name": "Francis", "csrf_token": token})
        header = response.headers["Set-Cookie"]
        self.assertIn("HttpOnly", header)
        self.assertIn("SameSite=Lax", header)
        self.assertNotIn("Expires=", header)
        with self.client.session_transaction() as session:
            self.assertEqual(set(session), {"visit_id"})
        self.assertNotIn("Francis", header)
        https = create_app({**self.config, "SESSION_COOKIE_SECURE": True})
        self.assertIn("Secure", https.test_client().get("/learn/", base_url="https://localhost").headers["Set-Cookie"])

    def test_csrf_rotates_on_new_visit_and_stale_tabs_cannot_submit(self):
        old_token = self.csrf()
        self.start()
        self.assertNotEqual(old_token, self.csrf())
        self.assertEqual(self.client.post("/visits/end", data={"csrf_token": old_token}).status_code, 400)
        self.assertIsNotNone(self.visit_id())

    def test_stable_private_key_and_visit_survive_application_restart(self):
        self.start()
        name = self.app.config["SESSION_COOKIE_NAME"]
        cookie = self.client.get_cookie(name).value
        key_path = Path(self.config["SECRET_KEY_FILE"])
        key = key_path.read_bytes()
        self.assertEqual(key_path.stat().st_mode & 0o777, 0o600)
        new_app = create_app(self.config)
        new_client = new_app.test_client()
        new_client.set_cookie(name, cookie)
        self.assertIn("Francis!", new_client.get("/learn/").get_data(as_text=True))
        self.assertEqual(key_path.read_bytes(), key)

    def test_insecure_or_corrupt_key_is_rejected_not_replaced(self):
        path = Path(self.config["SECRET_KEY_FILE"])
        original = path.read_bytes()
        path.chmod(0o644)
        with self.assertRaises(RuntimeError):
            load_signing_key(path)
        path.chmod(0o600)
        path.write_text("broken")
        with self.assertRaises(RuntimeError):
            load_signing_key(path)
        self.assertEqual(path.read_text(), "broken")
        path.write_bytes(original)

    def test_failed_history_insert_rolls_back_whole_visit_including_previous_end(self):
        self.start()
        before = self.query("SELECT * FROM visits")
        with closing(db.open_database(self.path)) as connection:
            connection.execute("""CREATE TRIGGER reject_initial_history BEFORE INSERT ON topic_status_history
                                  BEGIN SELECT RAISE(ABORT, 'simulated history failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.start("Next Visitor")
        self.assertEqual(self.query("SELECT * FROM visits"), before)
        self.assertEqual(self.query("SELECT COUNT(*) FROM topic_progress"), [(4,)])

    def test_database_rejects_completed_progress_without_confirmation(self):
        self.start()
        with closing(db.open_database(self.path)) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("UPDATE topic_progress SET learning_status = 'Completed'")
        self.assertEqual(self.query("SELECT DISTINCT learning_status FROM topic_progress"), [("Still Learning",)])


class VisitorMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="p22-migrate-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "phase2.db"
        with closing(sqlite3.connect(self.path)) as connection:
            connection.executescript(db.SCHEMA_PATH.read_text())
            connection.execute("UPDATE topics SET title = 'Keep my title' WHERE topic_id = 'sql-select-basics'")
            connection.commit()
        self.before = self.path.read_bytes()

    def assert_backup_restores_original(self, backup):
        with closing(sqlite3.connect(backup)) as connection:
            restored = "\n".join(connection.iterdump())
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
        original = self.root / "original-for-restore.db"
        original.write_bytes(self.before)
        with closing(sqlite3.connect(original)) as connection:
            self.assertEqual(restored, "\n".join(connection.iterdump()))

    def test_explicit_upgrade_preserves_catalogue_backup_and_is_repeatable(self):
        with self.assertRaisesRegex(db.DatabaseSetupError, "upgrade-db"):
            db.initialize_database(self.path)
        self.assertEqual(self.path.read_bytes(), self.before)
        backup = db.upgrade_database(self.path)
        self.assert_backup_restores_original(backup)
        with closing(db.open_database(self.path)) as connection:
            self.assertEqual(connection.execute("SELECT title FROM topics WHERE topic_id = 'sql-select-basics'").fetchone()[0], "Keep my title")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM visits").fetchone()[0], 0)
        after = self.path.read_bytes()
        self.assertIsNone(db.upgrade_database(self.path))
        self.assertEqual(self.path.read_bytes(), after)

    def test_failed_migration_rolls_back_ddl_and_keeps_original_backup(self):
        broken = self.root / "broken.sql"
        broken.write_text("BEGIN IMMEDIATE; CREATE TABLE partial (id INTEGER); INVALID; COMMIT;")
        with patch.object(db, "MIGRATION_PATH", broken):
            with self.assertRaises(db.DatabaseSetupError):
                db.upgrade_database(self.path)
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assert_backup_restores_original(self.path.with_name("phase2.before-p2.2.db"))

    def test_existing_backup_and_wrong_database_are_never_overwritten(self):
        backup = self.path.with_name("phase2.before-p2.2.db")
        backup.write_bytes(b"preserve")
        with self.assertRaises(db.DatabaseSetupError):
            db.upgrade_database(self.path)
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertEqual(backup.read_bytes(), b"preserve")
        wrong = self.root / "wrong.db"
        wrong.write_bytes(b"")
        with self.assertRaises(db.DatabaseSetupError):
            db.upgrade_database(wrong)
        self.assertEqual(wrong.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
