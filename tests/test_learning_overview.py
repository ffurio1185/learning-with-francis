"""Regression checks using disposable SQLite copies under /tmp only."""

from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app as application
import database


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_test_database(destination):
    """Build a disposable Version 1 database without opening original records."""
    schema = (PROJECT_ROOT / "tests" / "fixtures" / "version1-schema.sql").read_text()
    with closing(sqlite3.connect(destination)) as connection:
        connection.executescript(schema)


def seed_learning_data(db_path):
    """Replace records in an explicitly supplied disposable test copy."""
    with closing(database.connect_database(db_path)) as connection, connection:
        for table in ("Tasks", "QuizAttempts", "TopicStatusHistory", "Categories"):
            connection.execute("DELETE FROM " + table)

    ids = {name: database.create_topic(db_path, name)
           for name in ("SQL", "Python", "JavaScript", "SAP")}
    first = database.record_exercise(db_path, ids["SQL"], "Practise JOINs")
    database.record_exercise(db_path, ids["SQL"], "Practise JOINs")
    database.record_exercise(db_path, ids["Python"], "Read Python's documentation")
    with closing(database.connect_database(db_path)) as connection, connection:
        connection.execute(
            "UPDATE Tasks SET status = 1, completed_at = datetime('now') WHERE task_id = ?",
            (first,)
        )
    database.record_quiz_attempt(db_path, ids["SQL"], "JOIN quiz", 3, 5)
    database.record_quiz_attempt(db_path, ids["SQL"], "JOIN quiz", 5, 5)
    database.record_quiz_attempt(db_path, ids["Python"], "Python's functions", 0, 4)
    database.change_topic_status(db_path, ids["SQL"], "Needs Review")
    database.change_topic_status(db_path, ids["JavaScript"], "Completed", user_confirmed=True)
    return ids


class LearningOverviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="learning-overview-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.db_path = Path(self.temporary.name) / "test.db"
        create_test_database(self.db_path)
        self.ids = seed_learning_data(self.db_path)

    def overview(self):
        return database.get_learning_overview(self.db_path)

    def records(self):
        with closing(database.connect_database(self.db_path)) as connection, connection:
            return {table: connection.execute("SELECT * FROM " + table + " ORDER BY 1").fetchall()
                    for table in ("Categories", "Tasks", "QuizAttempts", "TopicStatusHistory")}

    def test_status_counts_cover_all_three_states(self):
        self.assertEqual(self.overview()["status_counts"], [
            {"learning_status": "Still Learning", "topic_count": 2},
            {"learning_status": "Needs Review", "topic_count": 1},
            {"learning_status": "Completed", "topic_count": 1},
        ])

    def test_counts_do_not_multiply_exercises_by_quizzes(self):
        rows = {row["category_name"]: row for row in self.overview()["topic_counts"]}
        self.assertEqual((rows["SQL"]["exercise_count"], rows["SQL"]["completed_exercises"],
                          rows["SQL"]["quiz_attempt_count"]), (2, 1, 2))
        database.record_quiz_attempt(self.db_path, self.ids["SQL"], "One more", 1, 1)
        sql = next(row for row in self.overview()["topic_counts"] if row["category_name"] == "SQL")
        self.assertEqual((sql["exercise_count"], sql["completed_exercises"], sql["quiz_attempt_count"]), (2, 1, 3))

    def test_topics_with_no_practice_and_quiz_only_are_included(self):
        sap = next(row for row in self.overview()["topic_counts"] if row["category_name"] == "SAP")
        self.assertEqual((sap["exercise_count"], sap["completed_exercises"], sap["quiz_attempt_count"]), (0, 0, 0))
        database.record_quiz_attempt(self.db_path, self.ids["SAP"], "SAP basics", 1, 2)
        sap = next(row for row in self.overview()["topic_counts"] if row["category_name"] == "SAP")
        self.assertEqual((sap["exercise_count"], sap["completed_exercises"], sap["quiz_attempt_count"]), (0, 0, 1))

    def test_practice_history_preserves_repeats_dates_and_results(self):
        entries = self.overview()["practice_history"]
        self.assertEqual(len(entries), 6)
        sql_exercises = [entry for entry in entries if entry["category_name"] == "SQL"
                         and entry["practice_type"] == "Exercise"]
        self.assertEqual(len(sql_exercises), 2)
        self.assertEqual(len({entry["entry_id"] for entry in sql_exercises}), 2)
        self.assertEqual(sorted(entry["exercise_status"] for entry in sql_exercises), [0, 1])
        self.assertEqual(sum(entry["completed_at"] is not None for entry in sql_exercises), 1)
        self.assertTrue(all(entry["recorded_at"] for entry in entries))
        self.assertEqual([entry["recorded_at"] for entry in entries],
                         sorted((entry["recorded_at"] for entry in entries), reverse=True))
        self.assertIn((5, 5), [(entry["correct_answers"], entry["total_questions"])
                              for entry in entries if entry["practice_type"] == "Quiz"])

    def test_status_history_shows_only_saved_events_and_confirmation(self):
        before = self.records()["TopicStatusHistory"]
        entries = self.overview()["status_history"]
        self.assertEqual(len(entries), len(before))
        self.assertEqual(sum(entry["previous_status"] is None for entry in entries), 4)
        confirmed = [entry for entry in entries if entry["new_status"] == "Completed"]
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(confirmed[0]["user_confirmed"], 1)
        with closing(database.connect_database(self.db_path)) as connection, connection:
            connection.execute("DELETE FROM TopicStatusHistory WHERE category_id = ? AND previous_status IS NULL",
                               (self.ids["SQL"],))
        self.assertEqual(len(self.overview()["status_history"]), len(before) - 1)

    def test_overview_is_read_only_and_perfect_results_do_not_complete_topic(self):
        before_bytes = self.db_path.read_bytes()
        before_records = self.records()
        overview = self.overview()
        self.assertEqual(self.db_path.read_bytes(), before_bytes)
        self.assertEqual(self.records(), before_records)
        sql = next(row for row in overview["topic_counts"] if row["category_name"] == "SQL")
        self.assertEqual(sql["learning_status"], "Needs Review")

    def test_empty_database_returns_zero_states_and_empty_histories(self):
        with closing(database.connect_database(self.db_path)) as connection, connection:
            for table in ("Tasks", "QuizAttempts", "TopicStatusHistory", "Categories"):
                connection.execute("DELETE FROM " + table)
        overview = self.overview()
        self.assertEqual([row["topic_count"] for row in overview["status_counts"]], [0, 0, 0])
        for name in ("topic_counts", "practice_history", "status_history"):
            self.assertEqual(overview[name], [])
        with patch.object(application, "DB_PATH", self.db_path):
            response = application.app.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        for message in ("No learning topics recorded yet.", "No practice recorded yet.",
                        "No topic status history recorded yet."):
            self.assertIn(message, response.get_data(as_text=True))

    def test_home_page_and_validation_error_keep_overview(self):
        with patch.object(application, "DB_PATH", self.db_path):
            client = application.app.test_client()
            home = client.get("/")
            rejected = client.post(f"/topics/{self.ids['SQL']}/status", data={"new_status": "Completed"})
        self.assertEqual(home.status_code, 200)
        self.assertEqual(rejected.status_code, 400)
        for response in (home, rejected):
            for section in ('id="practice-counts"', 'id="practice-history"', 'id="status-history"'):
                self.assertIn(section, response.get_data(as_text=True))

    def test_confirmed_change_updates_summary_and_retains_practice(self):
        before = self.records()
        with patch.object(application, "DB_PATH", self.db_path):
            response = application.app.test_client().post(
                f"/topics/{self.ids['SQL']}/status",
                data={"new_status": "Completed", "user_confirmed": "yes"}
            )
        self.assertEqual(response.status_code, 303)
        self.assertEqual([row["topic_count"] for row in self.overview()["status_counts"]], [2, 0, 2])
        self.assertEqual(self.records()["Tasks"], before["Tasks"])
        self.assertEqual(self.records()["QuizAttempts"], before["QuizAttempts"])
        self.assertEqual(len(self.records()["TopicStatusHistory"]), len(before["TopicStatusHistory"]) + 1)

    def test_existing_validation_and_parameterised_inputs(self):
        before = self.records()
        for title in ("", "   "):
            with self.assertRaises(ValueError):
                database.record_exercise(self.db_path, self.ids["SQL"], title)
        with self.assertRaises(sqlite3.IntegrityError):
            database.record_exercise(self.db_path, 99999, "Unknown topic")
        with self.assertRaises(TypeError):
            database.record_quiz_attempt(self.db_path, self.ids["SQL"], "Quiz", True, 3)
        with self.assertRaises(ValueError):
            database.record_quiz_attempt(self.db_path, self.ids["SQL"], "Quiz", 4, 3)
        self.assertEqual(self.records(), before)
        title = "Learner's exercise'); DROP TABLE Categories; --"
        task_id = database.record_exercise(self.db_path, self.ids["Python"], title)
        entry = next(entry for entry in self.overview()["practice_history"]
                     if entry["practice_type"] == "Exercise" and entry["entry_id"] == task_id)
        self.assertEqual(entry["title"], title)
        self.assertEqual(len(database.list_topics(self.db_path)), 4)

    def test_existing_transaction_rollback_preserves_summary(self):
        before = self.records()
        with closing(database.connect_database(self.db_path)) as connection, connection:
            connection.execute("""CREATE TRIGGER reject_test_history BEFORE INSERT ON TopicStatusHistory
                                  BEGIN SELECT RAISE(ABORT, 'deliberate test failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            database.change_topic_status(self.db_path, self.ids["SQL"], "Completed", user_confirmed=True)
        self.assertEqual(self.records(), before)
        self.assertEqual(next(row[2] for row in database.list_topics(self.db_path)
                              if row[0] == self.ids["SQL"]), "Needs Review")

    def test_missing_database_does_not_create_file(self):
        missing = Path(self.temporary.name) / "missing.db"
        with self.assertRaises(FileNotFoundError):
            database.get_learning_overview(missing)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
