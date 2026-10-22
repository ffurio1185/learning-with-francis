"""P2.1 setup checks. All writable databases are disposable files under /tmp."""

from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from learning_with_francis import PROJECT_ROOT, create_app
from learning_with_francis import db


class VisibleText(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.parts = []
        self.feed(html)

    def handle_data(self, data):
        self.parts.append(data.strip())


class Phase2SetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="phase2-setup-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "nested" / "phase2.db"
        self.app = create_app({"TESTING": True, "DATABASE": str(self.path), "SECRET_KEY": "disposable-setup-test-key"})

    def initialize(self):
        result = self.app.test_cli_runner().invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0, result.output)
        return result

    def test_factory_is_separate_and_does_not_initialize_database(self):
        self.assertFalse(self.path.exists())
        default = create_app({"SECRET_KEY": "disposable-default-test-key"})
        self.assertEqual(Path(default.config["DATABASE"]),
                         PROJECT_ROOT / "instance" / "learning_with_francis.db")
        self.assertNotEqual(Path(default.config["DATABASE"]), PROJECT_ROOT / "milestone3_test.db")
        self.assertTrue({"/", "/static/<path:filename>"}.issubset({rule.rule for rule in self.app.url_map.iter_rules()}))

    def test_initialization_preserves_curriculum_and_adds_empty_visit_tables(self):
        result = self.initialize()
        self.assertIn("Initialized:", result.output)
        with closing(db.open_database(self.path)) as connection:
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
            self.assertEqual([row[0] for row in tables], ["learning_answers", "learning_attempts", "subjects", "topic_progress", "topic_status_history", "topics", "visits"])
            self.assertEqual([row[0] for row in connection.execute("SELECT name FROM subjects ORDER BY display_order")],
                             ["SQL", "Python", "JavaScript", "SAP"])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM topics").fetchone()[0], 4)
            self.assertEqual(connection.execute("PRAGMA application_id").fetchone()[0], db.APPLICATION_ID)
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)

    def test_repeat_initialization_preserves_existing_contents_and_bytes(self):
        self.initialize()
        with closing(db.open_database(self.path)) as connection:
            connection.execute("UPDATE topics SET title = ? WHERE topic_id = ?",
                               ("Keep this existing title", "sql-select-basics"))
            connection.commit()
        before = self.path.read_bytes()
        result = self.initialize()
        self.assertIn("Already initialized; left unchanged", result.output)
        self.assertEqual(self.path.read_bytes(), before)

    def test_check_command_reports_readiness_without_writing(self):
        self.initialize()
        before = self.path.read_bytes()
        result = self.app.test_cli_runner().invoke(args=["check-db"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(f"schema {db.SCHEMA_VERSION}", result.output)
        self.assertIn("4 subjects, 4 topics", result.output)
        self.assertEqual(self.path.read_bytes(), before)

    def test_missing_database_is_not_silently_created(self):
        with self.assertRaises(db.DatabaseSetupError):
            db.open_database(self.path)
        result = self.app.test_cli_runner().invoke(args=["check-db"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertFalse(self.path.exists())

    def test_missing_database_page_is_helpful_and_does_not_create_data(self):
        response = self.app.test_client().get("/learn/")
        self.assertEqual(response.status_code, 503)
        self.assertIn("Database setup is needed", response.get_data(as_text=True))
        self.assertFalse(self.path.exists())

    def test_foundation_subjects_and_shared_stylesheet_survive_welcome_addition(self):
        self.initialize()
        before = self.path.read_bytes()
        client = self.app.test_client()
        response = client.get("/learn/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Learning with Francis", html)
        for subject in ("SQL", "Python", "JavaScript", "SAP"):
            self.assertIn(subject, VisibleText(html).parts)
        self.assertIn('name="visitor_name"', html)
        self.assertIn("HttpOnly", response.headers.get("Set-Cookie", ""))
        css = client.get("/static/style.css")
        self.assertEqual(css.status_code, 200)
        self.assertEqual(css.data, (PROJECT_ROOT / "static" / "style.css").read_bytes())
        css.close()
        self.assertEqual(self.path.read_bytes(), before)

    def test_foreign_keys_are_enabled_on_every_connection(self):
        self.initialize()
        for _ in range(2):
            with closing(db.open_database(self.path)) as connection:
                self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute("INSERT INTO topics (topic_id, subject_id, title) VALUES (?, ?, ?)",
                                       ("unknown", "not-a-subject", "Invalid reference"))
                connection.rollback()

    def test_request_connection_is_reused_and_closed(self):
        self.initialize()
        with self.app.app_context():
            connection = db.get_db()
            self.assertIs(db.get_db(), connection)
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")

    def test_version1_database_is_rejected_without_modification(self):
        self.path.parent.mkdir()
        schema = (PROJECT_ROOT / "tests" / "fixtures" / "version1-schema.sql").read_text()
        with closing(sqlite3.connect(self.path)) as connection:
            connection.executescript(schema)
            connection.execute("INSERT INTO Categories (category_name) VALUES (?)", ("Preserve this record",))
            connection.commit()
        before = self.path.read_bytes()
        result = self.app.test_cli_runner().invoke(args=["init-db"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("left unchanged", result.output)
        with self.assertRaises(db.DatabaseSetupError):
            db.open_database(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_unrelated_or_empty_existing_files_are_never_overwritten(self):
        self.path.parent.mkdir()
        for payload in (b"", b"This is not a SQLite database"):
            self.path.write_bytes(payload)
            result = self.app.test_cli_runner().invoke(args=["init-db"])
            self.assertNotEqual(result.exit_code, 0)
            self.assertEqual(self.path.read_bytes(), payload)

    def test_unsupported_schema_version_is_left_unchanged(self):
        self.initialize()
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA user_version = 999")
        before = self.path.read_bytes()
        result = self.app.test_cli_runner().invoke(args=["init-db"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_initialization_removes_only_its_new_partial_database(self):
        bad_schema = self.root / "broken.sql"
        bad_schema.write_text("BEGIN; CREATE TABLE partial (id INTEGER); THIS IS INVALID SQL;")
        unrelated = self.root / "keep.txt"
        unrelated.write_text("Keep this file unchanged")
        with patch.object(db, "SCHEMA_PATH", bad_schema):
            result = self.app.test_cli_runner().invoke(args=["init-db"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertFalse(self.path.exists())
        self.assertEqual(unrelated.read_text(), "Keep this file unchanged")

    def test_initialized_database_survives_new_app_instance(self):
        self.initialize()
        other = create_app({"TESTING": True, "DATABASE": str(self.path), "SECRET_KEY": "disposable-setup-test-key"})
        result = other.test_cli_runner().invoke(args=["check-db"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(other.test_client().get("/learn/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
