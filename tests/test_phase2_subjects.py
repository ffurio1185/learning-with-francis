"""P2.4: subject-owned activity, reuse of SQL flow and no original database access."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from html import unescape
import re
import sqlite3
import unittest

from learning_with_francis import create_app, db
from learning_with_francis.subjects import SUBJECTS
from test_phase2_sql import SQLFlowSupport, HiddenFields


class SubjectFlowTests(SQLFlowSupport, unittest.TestCase):
    def data(self, slug, kind="quiz", score=5, url=None, client=None):
        client = client or self.client
        html = client.get(url or f"/{slug}/{kind}").get_data(as_text=True)
        data = HiddenFields(html).fields
        module = SUBJECTS[slug]["content"]
        questions = module.QUIZ if kind == "quiz" else (module.PRACTICE[int(data["position"])],)
        for index, question in enumerate(questions):
            data[question["id"]] = question["correct"] if index < score else next(
                key for key in question["choices"] if key != question["correct"])
        return data, html

    def quiz_attempt(self, slug, score=5, client=None):
        data, _ = self.data(slug, score=score, client=client)
        return (client or self.client).post(f"/{slug}/quiz", data=data)

    def test_all_subject_links_and_lessons_have_the_correct_material(self):
        html = self.client.get("/learn/").get_data(as_text=True)
        for slug, info in SUBJECTS.items():
            with self.subTest(subject=slug):
                self.assertIn(f'Open {info["name"]} lesson', html)
                response = self.client.get(f"/{slug}/")
                self.assertEqual(response.status_code, 200)
                lesson = unescape(response.get_data(as_text=True))
                self.assertIn(info["title"], lesson)
                self.assertIn(f'Start {info["name"]} quiz', lesson)
                self.assertIn(f'href="/{slug}/practice"', lesson)
                self.assertIn('id="quiz-count">0', lesson)
        self.assertIn("return number + 1", self.client.get('/python/').get_data(as_text=True))
        self.assertIn("addEventListener", self.client.get('/javascript/').get_data(as_text=True))
        self.assertIn("purchase order", self.client.get('/sap/').get_data(as_text=True))
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(0,)])

    def test_new_content_has_ten_unique_practice_and_five_quiz_questions(self):
        for slug, info in SUBJECTS.items():
            module = info["content"]
            self.assertEqual(len(module.PRACTICE), 10)
            self.assertEqual(len(module.QUIZ), 5)
            for questions in (module.PRACTICE, module.QUIZ):
                self.assertEqual(len({q["id"] for q in questions}), len(questions))
                self.assertEqual(len({q["prompt"] for q in questions}), len(questions))
                for question in questions:
                    self.assertEqual(len(question["choices"]), 3)
                    self.assertIn(question["correct"], question["choices"])
                    self.assertTrue(question["explanation"])
            public = module.public_questions("quiz")
            self.assertTrue(all(set(q) == {"id", "prompt", "choices"} for q in public))

    def test_full_practice_rounds_feedback_completion_and_restart_for_each_new_subject(self):
        before = self.progress()
        for slug in ("python", "javascript", "sap"):
            with self.subTest(subject=slug):
                url = f"/{slug}/practice"
                for position in range(10):
                    data, html = self.data(slug, "practice", score=position % 2, url=url)
                    self.assertIn(f"Question {position+1} of 10", html)
                    self.assertEqual(html.count('<input type="radio"'), 3)
                    response = self.client.post(url, data=data)
                    self.assertEqual(response.status_code, 303)
                    result = unescape(self.client.get(response.location).get_data(as_text=True))
                    question = SUBJECTS[slug]["content"].PRACTICE[position]
                    self.assertIn(question["explanation"], result)
                    self.assertIn("Correct answer:", result)
                    self.assertIn("Incorrect" if position % 2 == 0 else "Correct", result)
                    url = unescape(re.search(r'id="practice-next" href="([^"]+)"', result).group(1))
                    self.assertTrue(url.startswith(f"/{slug}/practice?run="))
                completion = self.client.get(url).get_data(as_text=True)
                self.assertIn("Practice complete!", completion)
                self.assertIn("Start Practicing Again", completion)
                data, html = self.data(slug, "practice")
                self.assertIn("Question 1 of 10", html)
                self.assertEqual(self.client.post(f"/{slug}/practice", data=data).status_code, 303)
                topic = SUBJECTS[slug]["content"].TOPIC_ID
                self.assertEqual(self.rows("SELECT COUNT(*),SUM(score) FROM learning_attempts WHERE topic_id=?", (topic,)), [(11, 6)])
                lesson = self.client.get(f"/{slug}/").get_data(as_text=True)
                self.assertIn('id="practice-count">11', lesson)
                self.assertIn('id="exercise-count">6', lesson)
        self.assertEqual(self.progress(), before)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(33,)])

    def test_all_six_scores_exact_feedback_and_stored_answer_snapshots_for_each_new_subject(self):
        before = self.progress()
        for slug in ("python", "javascript", "sap"):
            for score in range(6):
                with self.subTest(subject=slug, score=score):
                    response = self.quiz_attempt(slug, score)
                    self.assertEqual(response.status_code, 303)
                    html = unescape(self.client.get(response.location).get_data(as_text=True))
                    self.assertIn(SUBJECTS[slug]["content"].quiz_feedback(score, "Francis"), html)
                    self.assertIn(f"{score} out of 5", html)
                    self.assertEqual(html.count('class="answer-result correct-answer"'), score)
                    self.assertEqual(html.count('class="answer-result incorrect-answer"'), 5-score)
                    self.assertIn(SUBJECTS[slug]["content"].QUIZ[0]["explanation"], html)
            lesson = self.client.get(f"/{slug}/").get_data(as_text=True)
            self.assertIn('id="quiz-count">6', lesson)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(90,)])
        self.assertEqual(self.rows("SELECT COUNT(DISTINCT topic_id) FROM learning_attempts"), [(3,)])
        self.assertEqual(self.progress(), before)

    def test_subject_tokens_results_counts_and_history_cannot_cross_subjects(self):
        result = self.quiz_attempt("python")
        for slug in ("sql", "javascript", "sap"):
            self.assertEqual(self.client.get(result.location.replace('/python/', f'/{slug}/')).status_code, 404)
            self.assertIn('id="quiz-count">0', self.client.get(f'/{slug}/').get_data(as_text=True))
            data, _ = self.data("python")
            self.assertEqual(self.client.post(f'/{slug}/quiz', data=data).status_code, 400)
            data, _ = self.data("python", "practice")
            self.assertEqual(self.client.post(f'/{slug}/practice', data=data).status_code, 400)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(1,)])

    def test_same_name_visitors_and_end_visit_keep_each_subject_private(self):
        other = self.app.test_client()
        self.start(other)
        locations = []
        for slug in ("python", "javascript", "sap"):
            response = self.quiz_attempt(slug)
            locations.append(response.location)
            self.assertEqual(other.get(response.location).status_code, 404)
            self.assertIn('id="quiz-count">0', other.get(f'/{slug}/').get_data(as_text=True))
            data, _ = self.data(slug)
            data["csrf_token"] = self.data(slug, client=other)[0]["csrf_token"]
            self.assertEqual(other.post(f'/{slug}/quiz', data=data).status_code, 400)
        csrf = HiddenFields(self.client.get('/learn/').get_data(as_text=True)).fields
        self.client.post('/visits/end', data=csrf)
        for location in locations:
            self.assertEqual(self.client.get(location).status_code, 303)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(15,)])

    def test_retries_duplicates_conflicting_submissions_and_forged_scores(self):
        for slug in ("python", "javascript", "sap"):
            data, _ = self.data(slug, score=0)
            data.update({"score": "5", "visit_id": "other", "topic_id": "sql-select-basics"})
            first = self.client.post(f'/{slug}/quiz', data=data)
            duplicate = self.client.post(f'/{slug}/quiz', data=data)
            self.assertEqual(first.status_code, 303)
            self.assertEqual(first.location, duplicate.location)
            data["q1"] = SUBJECTS[slug]["content"].QUIZ[0]["correct"]
            self.assertEqual(self.client.post(f'/{slug}/quiz', data=data).status_code, 409)
            for _ in range(5):
                self.assertEqual(self.quiz_attempt(slug).status_code, 303)
            topic = SUBJECTS[slug]["content"].TOPIC_ID
            self.assertEqual(self.rows("SELECT COUNT(*),SUM(score) FROM learning_attempts WHERE topic_id=?", (topic,)), [(6, 25)])

    def test_missing_invalid_answers_and_csrf_reject_each_new_subject(self):
        for slug in ("python", "javascript", "sap"):
            for field, value in (("q1", None), ("q1", "' OR 1=1 --"), ("q1", ["a", "b"]), ("csrf_token", "forged")):
                data, _ = self.data(slug)
                if value is None:
                    del data[field]
                else:
                    data[field] = value
                self.assertEqual(self.client.post(f'/{slug}/quiz', data=data).status_code, 400)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(0,)])

    def test_answer_failure_rolls_back_new_subject_attempt(self):
        with closing(db.open_database(self.path)) as connection:
            connection.execute("""CREATE TRIGGER reject_answer BEFORE INSERT ON learning_answers
                WHEN NEW.position = 3 BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
        for slug in ("python", "javascript", "sap"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.quiz_attempt(slug)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_answers"), [(0,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM learning_attempts"), [(0,)])

    def test_saved_results_survive_app_restart_for_every_subject(self):
        locations = [(slug, self.quiz_attempt(slug, 3).location) for slug in SUBJECTS]
        cookie = self.client.get_cookie(self.app.config["SESSION_COOKIE_NAME"]).value
        restarted = create_app(self.config).test_client()
        restarted.set_cookie(self.app.config["SESSION_COOKIE_NAME"], cookie)
        for slug, location in locations:
            self.assertIn('3 out of 5', restarted.get(location).get_data(as_text=True))
            self.assertIn('id="quiz-count">1', restarted.get(f'/{slug}/').get_data(as_text=True))

    def test_concurrent_different_subject_requests_use_separate_content(self):
        payloads = [(slug, self.data(slug, score=i)[0]) for i, slug in enumerate(SUBJECTS)]
        cookie = self.client.get_cookie(self.app.config["SESSION_COOKIE_NAME"]).value
        def submit(item):
            slug, data = item
            client = self.app.test_client()
            client.set_cookie(self.app.config["SESSION_COOKIE_NAME"], cookie)
            response = client.post(f'/{slug}/quiz', data=data)
            return response.status_code
        with ThreadPoolExecutor(max_workers=4) as executor:
            self.assertEqual(list(executor.map(submit, payloads)), [303] * 4)
        for score, slug in enumerate(SUBJECTS):
            self.assertEqual(self.rows("SELECT score FROM learning_attempts WHERE topic_id=?", (SUBJECTS[slug]["content"].TOPIC_ID,)), [(score,)])

    def test_unknown_subject_and_invalid_result_urls_are_rejected(self):
        self.assertEqual(self.client.get('/unknown/').status_code, 404)
        self.assertEqual(self.client.get('/python/results/not-an-attempt').status_code, 404)
        self.assertEqual(self.client.post('/sap/results/not-an-attempt').status_code, 405)

    def test_known_python_lesson_example_runs(self):
        # Trusted authored lesson code, not submitted visitor code.
        scope = {}
        exec("def add_one(number):\n    return number + 1\nresult = add_one(4)", scope)
        self.assertEqual(scope['result'], 5)
