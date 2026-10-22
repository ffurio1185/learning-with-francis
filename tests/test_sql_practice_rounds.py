"""Ten-question practice flow; every database is disposable under /tmp."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from html import unescape
import re
import unittest

from learning_with_francis import create_app, db, sql_content as content
from test_phase2_sql import SQLFlowSupport, HiddenFields


class PracticeRoundTests(SQLFlowSupport, unittest.TestCase):

    def next_link(self, html):
        match = re.search(r'id="practice-next" href="([^"]+)"', html)
        self.assertIsNotNone(match)
        return unescape(match.group(1))

    def answer_page(self, url, position, correct=True, client=None):
        client = client or self.client
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn(f"Question {position + 1} of 10", html)
        self.assertEqual(html.count('<input type="radio"'), 3)
        data = HiddenFields(html).fields
        question = content.PRACTICE[position]
        self.assertNotIn(question["explanation"], html)
        data[question["id"]] = question["correct"] if correct else next(
            choice for choice in question["choices"] if choice != question["correct"])
        result = client.post(url, data=data)
        self.assertEqual(result.status_code, 303)
        feedback = client.get(result.location).get_data(as_text=True)
        self.assertIn("Correct answer:", feedback)
        self.assertIn(question["explanation"], unescape(feedback))
        self.assertIn('correct-answer"' if correct else 'incorrect-answer"', feedback)
        return self.next_link(feedback), result.location, data

    def test_ten_distinct_questions_one_at_a_time_and_immediate_feedback(self):
        self.assertEqual(len(content.PRACTICE), 10)
        self.assertEqual(len({q["id"] for q in content.PRACTICE}), 10)
        self.assertEqual(len({q["prompt"] for q in content.PRACTICE}), 10)
        before = self.progress()
        url = "/sql/practice"
        for position in range(10):
            url, location, _ = self.answer_page(url, position, correct=position % 2 == 0)
            # Refreshing either a question or result cannot create another answer.
            self.client.get(location)
            self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(position + 1,)])
        html = self.client.get(url).get_data(as_text=True)
        self.assertIn("Practice complete!", html)
        self.assertIn("Francis! You have practised all 10", html)
        self.assertIn("Start Practicing Again", html)
        self.assertNotIn('<input type="radio"', html)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(10,)])
        self.assertEqual(self.rows("SELECT SUM(score) FROM learning_attempts"), [(5,)])
        self.assertEqual(self.progress(), before)
        counts = self.client.get("/sql/").get_data(as_text=True)
        for text in ('id="practice-count">10', 'id="exercise-count">5', 'id="quiz-count">0'):
            self.assertIn(text, counts)

    def test_all_wrong_answers_still_finish_round_and_can_restart_repeatedly(self):
        old_locations = []
        for cycle in range(3):
            url = "/sql/practice"
            for position in range(10):
                url, location, _ = self.answer_page(url, position, correct=False)
                old_locations.append(location)
            for _ in range(2):
                self.assertIn("Practice complete!", self.client.get(url).get_data(as_text=True))
            self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [((cycle + 1) * 10,)])
        self.assertEqual(len(set(old_locations)), 30)
        self.assertEqual(self.rows("SELECT SUM(score) FROM learning_attempts"), [(0,)])
        self.assertEqual(self.rows("SELECT COUNT(DISTINCT question_id) FROM learning_answers"), [(10,)])

    def test_duplicate_practice_posts_and_conflicting_answers_do_not_duplicate(self):
        _, location, data = self.answer_page("/sql/practice", 0)
        for _ in range(3):
            repeated = self.client.post("/sql/practice", data=data)
            self.assertEqual(repeated.location, location)
            self.assertEqual(repeated.status_code, 303)
        data["practice1"] = "b"
        self.assertEqual(self.client.post("/sql/practice", data=data).status_code, 409)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(1,)])
        self.assertEqual(self.rows("SELECT score FROM learning_attempts"), [(1,)])

    def test_concurrent_practice_posts_save_one_answer(self):
        data = self.fields("practice")
        data["practice1"] = "a"
        cookie = self.client.get_cookie(self.app.config["SESSION_COOKIE_NAME"]).value
        def post(_):
            client = self.app.test_client()
            client.set_cookie(self.app.config["SESSION_COOKIE_NAME"], cookie)
            response = client.post("/sql/practice", data=data)
            return response.status_code, response.location
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(post, range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0], 303)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(1,)])

    def test_round_and_results_are_isolated_for_same_name_visitors(self):
        url, location, data = self.answer_page("/sql/practice", 0)
        other = self.app.test_client()
        self.start(other)
        self.assertEqual(other.get(url).status_code, 400)
        self.assertEqual(other.get(location).status_code, 404)
        data["csrf_token"] = self.fields("practice", other)["csrf_token"]
        self.assertEqual(other.post("/sql/practice", data=data).status_code, 400)
        self.answer_page("/sql/practice", 0, client=other)
        self.assertEqual(self.rows("SELECT COUNT(DISTINCT visit_id) FROM learning_attempts"), [(2,)])

    def test_invalid_positions_questions_and_tokens_save_nothing(self):
        for change in ({"position": "9"}, {"practice2": "b"}, {"practice1": "not-an-option"},
                       {"submission_token": "forged"}, {"csrf_token": "forged"}):
            data = self.fields("practice")
            data["practice1"] = "a"
            data.update(change)
            response = self.client.post("/sql/practice", data=data)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(0,)])
        self.assertEqual(self.client.get("/sql/practice?run=forged").status_code, 400)

    def test_progress_survives_restart_and_old_result_still_opens(self):
        url = "/sql/practice"
        for position in range(4):
            url, location, _ = self.answer_page(url, position)
        cookie = self.client.get_cookie(self.app.config["SESSION_COOKIE_NAME"]).value
        restarted = create_app(self.config).test_client()
        restarted.set_cookie(self.app.config["SESSION_COOKIE_NAME"], cookie)
        self.assertIn("Question 5 of 10", restarted.get(url).get_data(as_text=True))
        self.assertEqual(restarted.get(location).status_code, 200)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(4,)])

    def test_legacy_practice_results_and_quiz_remain_unchanged(self):
        # Simulate a saved single-question result from the approved earlier preview.
        _, location, _ = self.answer_page("/sql/practice", 0)
        with closing(db.open_database(self.path)) as connection:
            connection.execute("UPDATE learning_attempts SET content_version = ?", (content.CONTENT_VERSION,))
            connection.commit()
        html = self.client.get(location).get_data(as_text=True)
        self.assertIn("Correct answer:", html)
        self.assertIn("Try Again", html)
        self.assertNotIn('id="practice-next"', html)
        self.assertEqual(len(content.QUIZ), 5)
        response = self.submit(5)
        self.assertIn(content.quiz_feedback(5, "Francis"), self.client.get(response.location).get_data(as_text=True))
