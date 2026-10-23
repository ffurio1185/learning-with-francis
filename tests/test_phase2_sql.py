"""P2.3 checks: all activity, migration and answer data is disposable under /tmp."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path
from retention_support import learning_snapshot

import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from werkzeug.datastructures import MultiDict

from learning_with_francis import create_app, db, sql_content as content


class HiddenFields(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.fields = {}
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "input" and attributes.get("type") == "hidden":
            self.fields[attributes["name"]] = attributes.get("value", "")


class SQLFlowSupport:
    """Shared disposable database and request helpers, without test cases."""
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="p23-sql-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "phase2.db"
        db.initialize_database(self.path)
        self.config = {"TESTING": True, "DATABASE": str(self.path), "SECRET_KEY": "disposable-sql-test-key"}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.start(self.client)

    def start(self, client, name="Francis"):
        fields = HiddenFields(client.get("/learn/").get_data(as_text=True)).fields
        response = client.post("/visits/start", data={**fields, "visitor_name": name})
        self.assertEqual(response.status_code, 303)

    def rows(self, sql, parameters=()):
        with closing(db.open_database(self.path)) as connection:
            return [tuple(row) for row in connection.execute(sql, parameters)]

    def fields(self, kind="quiz", client=None):
        client = client or self.client
        return HiddenFields(client.get(f"/sql/{kind}").get_data(as_text=True)).fields

    def payload(self, score=5, kind="quiz", client=None):
        data = self.fields(kind, client)
        questions = content.questions_for(kind)
        if kind == "practice":
            questions = (questions[int(data["position"])],)
        for index, question in enumerate(questions):
            data[question["id"]] = question["correct"] if index < score else next(
                option for option in question["choices"] if option != question["correct"])
        return data

    def submit(self, score=5, kind="quiz", client=None):
        return (client or self.client).post(f"/sql/{kind}", data=self.payload(score, kind, client))

    def progress(self):
        return (self.rows("SELECT * FROM topic_progress ORDER BY visit_id, topic_id"),
                self.rows("SELECT * FROM topic_status_history ORDER BY history_id"))

class SQLFlowTests(SQLFlowSupport, unittest.TestCase):
    def test_home_sql_link_lesson_examples_and_empty_real_activity(self):
        self.assertIn('href="/sql/"', self.client.get("/learn/").get_data(as_text=True))
        response = self.client.get("/sql/")
        html = response.get_data(as_text=True)
        for text in ("SELECT and WHERE", "SELECT name, city FROM learners;", "WHERE city = 'Berlin'",
                     "No SQL activity recorded", 'id="practice-count">0', 'id="quiz-count">0'):
            self.assertIn(text, html)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(0,)])
        self.assertNotIn('href="/python', html)

    def test_public_forms_have_no_answer_key_and_get_does_not_save_activity(self):
        before = learning_snapshot(self.path)
        for kind in ("practice", "quiz"):
            html = self.client.get(f"/sql/{kind}").get_data(as_text=True)
            self.assertEqual(html.count('<input type="radio"'), 3 if kind == "practice" else 15)
            self.assertNotIn('name="score"', html)
            self.assertNotIn("correct_option", html)
            for question in content.questions_for(kind):
                self.assertNotIn(question["explanation"], html)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_all_six_scores_and_exact_personalized_feedback(self):
        for score in range(6):
            with self.subTest(score=score):
                response = self.submit(score)
                self.assertEqual(response.status_code, 303)
                html = self.client.get(response.location).get_data(as_text=True)
                self.assertIn(content.quiz_feedback(score, "Francis"), html)
                self.assertIn(f"{score} out of 5", html)
                self.assertEqual(html.count('class="answer-result correct-answer"'), score)
                self.assertEqual(html.count('class="answer-result incorrect-answer"'), 5 - score)
                self.assertIn("Correct answer:", html)
                self.assertIn("Your answer:", html)
        self.assertEqual(self.rows("SELECT score, total_questions FROM learning_attempts ORDER BY rowid"),
                         [(score, 5) for score in range(6)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(30,)])

    def test_correct_and_incorrect_practice_results_and_completion_counts(self):
        before = self.progress()
        for score in (0, 1):
            response = self.submit(score, "practice")
            self.assertEqual(response.status_code, 303)
            html = self.client.get(response.location).get_data(as_text=True)
            self.assertIn(f"{score} out of 1", html)
            self.assertIn("WHERE city =", html)
        html = self.client.get("/sql/").get_data(as_text=True)
        for text in ('id="practice-count">2', 'id="exercise-count">1', 'id="quiz-count">0'):
            self.assertIn(text, html)
        self.assertEqual(self.progress(), before)

    def test_browser_forged_score_and_owner_are_ignored(self):
        data = self.payload(0)
        data.update({"score": "5", "correct_answers": "5", "total_questions": "1", "visit_id": "other-owner"})
        response = self.client.post("/sql/quiz", data=data)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.rows("SELECT score,total_questions FROM learning_attempts"), [(0, 5)])

    def test_invalid_or_missing_answers_reject_whole_attempt_and_can_be_corrected(self):
        cases = ({"q1": "missing"}, {"q1": "' OR 1=1 --"}, {"q1": ""}, {"q1": ["a", "b"]}, {"q9": "a"})
        for change in cases:
            data = self.payload()
            data.update(change)
            response = self.client.post("/sql/quiz", data=MultiDict(data))
            self.assertEqual(response.status_code, 400)
            self.assertIn('role="alert"', response.get_data(as_text=True))
        data = self.payload()
        del data["q2"]
        response = self.client.post("/sql/quiz", data=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(0,)])
        fields = HiddenFields(response.get_data(as_text=True)).fields
        data.update(fields)
        data["q2"] = content.QUIZ[1]["correct"]
        self.assertEqual(self.client.post("/sql/quiz", data=data).status_code, 303)

    def test_missing_forged_and_foreign_csrf_and_submission_tokens_are_rejected(self):
        for field in ("csrf_token", "submission_token"):
            for value in (None, "forged", "forgé"):
                data = self.payload()
                if value is None:
                    del data[field]
                else:
                    data[field] = value
                self.assertEqual(self.client.post("/sql/quiz", data=data).status_code, 400)
        other = self.app.test_client()
        self.start(other, "Alex")
        data = self.payload(client=other)
        data["csrf_token"] = self.fields()["csrf_token"]
        self.assertEqual(other.post("/sql/quiz", data=data).status_code, 400)
        data = self.payload(client=other)
        data["submission_token"] = self.fields()["submission_token"]
        self.assertEqual(other.post("/sql/quiz", data=data).status_code, 400)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(0,)])

    def test_expired_wrong_kind_and_wrong_content_version_tokens_are_rejected(self):
        from learning_with_francis.learning import signer
        data = self.payload()
        data["submission_token"] = self.fields("practice")["submission_token"]
        self.assertEqual(self.client.post("/sql/quiz", data=data).status_code, 400)
        with self.app.app_context():
            serializer = signer()
            info = serializer.loads(self.fields()["submission_token"])
            info["version"] = "obsolete"
            data["submission_token"] = serializer.dumps(info)
        self.assertEqual(self.client.post("/sql/quiz", data=data).status_code, 400)
        import time
        data = self.payload()
        with self.app.app_context():
            serializer = signer()
            info = serializer.loads(data["submission_token"])
            # Age only the activity token, keeping the browser session itself valid.
            with patch("itsdangerous.timed.time.time", return_value=time.time() - 13 * 60 * 60):
                data["submission_token"] = serializer.dumps(info)
        self.assertEqual(self.client.post("/sql/quiz", data=data).status_code, 400)

    def test_duplicate_post_refresh_and_conflicting_resubmission(self):
        data = self.payload()
        first = self.client.post("/sql/quiz", data=data)
        duplicate = self.client.post("/sql/quiz", data=data)
        self.assertEqual(first.status_code, 303)
        self.assertEqual(first.location, duplicate.location)
        for _ in range(3):
            self.assertEqual(self.client.get(first.location).status_code, 200)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(1,)])
        data["q1"] = "a"
        self.assertEqual(self.client.post("/sql/quiz", data=data).status_code, 409)
        self.assertEqual(self.rows("SELECT score FROM learning_attempts"), [(5,)])

    def test_concurrent_duplicate_posts_create_one_complete_attempt(self):
        data = self.payload()
        cookie = self.client.get_cookie(self.app.config["SESSION_COOKIE_NAME"]).value
        def submit_copy(_):
            client = self.app.test_client()
            client.set_cookie(self.app.config["SESSION_COOKIE_NAME"], cookie)
            response = client.post("/sql/quiz", data=data)
            return response.status_code, response.location
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(submit_copy, range(2)))
        self.assertEqual(responses[0], responses[1])
        self.assertEqual(responses[0][0], 303)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(1,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(5,)])

    def test_many_unlimited_retries_receive_distinct_ids_and_dates(self):
        before = self.progress()
        locations = {self.submit(i % 6).location for i in range(15)}
        self.assertEqual(len(locations), 15)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(15,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts WHERE datetime(submitted_at) IS NOT NULL"), [(15,)])
        self.assertEqual(self.progress(), before)

    def test_saved_answer_snapshots_score_and_history_survive_app_restart(self):
        response = self.submit(3)
        location = response.location
        before = self.rows("SELECT * FROM learning_answers ORDER BY position")
        cookie = self.client.get_cookie(self.app.config["SESSION_COOKIE_NAME"]).value
        restarted = create_app(self.config).test_client()
        restarted.set_cookie(self.app.config["SESSION_COOKIE_NAME"], cookie)
        self.assertIn("3 out of 5", restarted.get(location).get_data(as_text=True))
        html = restarted.get("/sql/").get_data(as_text=True)
        self.assertIn('id="quiz-count">1', html)
        self.assertIn("SQL quiz: 3 out of 5", html)
        self.assertIn("Europe/Berlin", html)
        with patch.object(content, "QUIZ", ()):
            self.assertIn("3 out of 5", restarted.get(location).get_data(as_text=True))
        self.assertEqual(self.rows("SELECT * FROM learning_answers ORDER BY position"), before)

    def test_same_name_visitor_cannot_access_results_history_or_old_form(self):
        location = self.submit().location
        data = self.payload()
        other = self.app.test_client()
        self.start(other)
        self.assertEqual(other.get(location).status_code, 404)
        self.assertEqual(other.post(location).status_code, 405)
        html = other.get("/sql/").get_data(as_text=True)
        self.assertIn('id="quiz-count">0', html)
        self.assertNotIn(location, html)
        data["csrf_token"] = self.fields(client=other)["csrf_token"]
        self.assertEqual(other.post("/sql/quiz", data=data).status_code, 400)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(1,)])

    def test_end_visit_blocks_results_and_old_forms_and_deletes_rows(self):
        location = self.submit().location
        data = self.payload()
        fields = HiddenFields(self.client.get("/learn/").get_data(as_text=True)).fields
        self.client.post("/visits/end", data=fields)
        for path in ("/sql/", "/sql/quiz", "/sql/practice", location):
            self.assertEqual(self.client.get(path).status_code, 303)
        self.assertEqual(self.client.post("/sql/quiz", data=data).status_code, 303)
        self.start(self.client)
        self.assertEqual(self.client.get(location).status_code, 404)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(0,)])

    def test_answer_insert_failure_rolls_back_attempt_and_all_answers(self):
        with closing(db.open_database(self.path)) as connection:
            connection.execute("""CREATE TRIGGER fail_answer BEFORE INSERT ON learning_answers
                WHEN NEW.position = 3 BEGIN SELECT RAISE(ABORT, 'simulated failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.submit()
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(0,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(0,)])

    def test_example_queries_execute_and_match_answer_key(self):
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.executescript("CREATE TABLE learners(name TEXT, city TEXT, age INTEGER);"
                "INSERT INTO learners VALUES ('Alex','Berlin',22),('Mia','Hamburg',16),('Sam','Berlin',19);")
            self.assertEqual(connection.execute("SELECT name FROM learners WHERE city = 'Berlin'").fetchall(), [("Alex",), ("Sam",)])
            self.assertEqual(connection.execute("SELECT name FROM learners WHERE age < 18").fetchall(), [("Mia",)])
            self.assertEqual(connection.execute(content.PRACTICE[0]["choices"]["a"]).fetchall(), [("Alex",), ("Sam",)])
            self.assertEqual(len(connection.execute(content.QUIZ[2]["choices"]["a"]).fetchall()), 2)


class SQLMigrationTests(unittest.TestCase):
    def test_schema2_upgrade_preserves_visits_progress_history_and_backup(self):
        with tempfile.TemporaryDirectory(prefix="p23-migrate-", dir="/tmp") as directory:
            path = Path(directory) / "existing.db"
            with closing(sqlite3.connect(path)) as connection:
                connection.executescript(db.SCHEMA_PATH.read_text())
                connection.executescript(db.MIGRATION_PATH.read_text())
                connection.execute("INSERT INTO visits (visit_id,display_name) VALUES ('old-visit','Alex')")
                connection.execute("INSERT INTO topic_progress (visit_id,topic_id) VALUES ('old-visit','sql-select-basics')")
                connection.execute("""INSERT INTO topic_status_history
                    (visit_id,topic_id,new_status,user_confirmed) VALUES ('old-visit','sql-select-basics','Still Learning',0)""")
                connection.commit()
                before = "\n".join(connection.iterdump())
            backup = db.upgrade_database(path)
            self.assertEqual(backup.name, "existing.before-p2.3.db")
            with closing(sqlite3.connect(backup)) as connection:
                self.assertEqual("\n".join(connection.iterdump()), before)
            with closing(db.open_database(path)) as connection:
                self.assertEqual(connection.execute("SELECT display_name FROM visits").fetchone()[0], "Alex")
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM topic_status_history").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM learning_attempts").fetchone()[0], 0)
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            after = path.read_bytes()
            self.assertIsNone(db.upgrade_database(path))
            self.assertEqual(path.read_bytes(), after)

    def test_failed_second_migration_rolls_back_entire_upgrade(self):
        with tempfile.TemporaryDirectory(prefix="p23-rollback-", dir="/tmp") as directory:
            path = Path(directory) / "existing.db"
            broken = Path(directory) / "broken.sql"
            broken.write_text("BEGIN IMMEDIATE; CREATE TABLE partial(id INTEGER); INVALID; COMMIT;")
            with closing(sqlite3.connect(path)) as connection:
                connection.executescript(db.SCHEMA_PATH.read_text())
            before = path.read_bytes()
            with patch.object(db, "ACTIVITY_MIGRATION_PATH", broken):
                with self.assertRaises(db.DatabaseSetupError):
                    db.upgrade_database(path)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
