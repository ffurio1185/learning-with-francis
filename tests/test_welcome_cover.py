"""Cover routing and visit preservation; all databases are disposable."""

from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from learning_with_francis import create_app, db


class WelcomeCoverTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="welcome-cover-test-", dir="/tmp")
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / "learning.db"
        self.app = create_app({"TESTING": True, "DATABASE": str(self.database),
                               "SECRET_KEY": "disposable-cover-test-key"})
        self.client = self.app.test_client()

    def start(self):
        self.client.get("/learn/")
        with self.client.session_transaction() as session:
            token = session["csrf_token"]
        response = self.client.post("/visits/start", data={"visitor_name": "Cover Learner", "csrf_token": token})
        self.assertEqual(response.location, "/learn/")
        return response

    def test_cover_does_not_require_database_or_create_cookie(self):
        # The visual entrance must not resolve or mutate visitor state.
        with patch.object(db, "get_db", side_effect=AssertionError("Cover touched database")):
            for method in (self.client.get, self.client.head):
                response = method("/")
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("Set-Cookie", response.headers)
        self.assertFalse(self.database.exists())
        self.assertEqual(self.client.get("/learn/").status_code, 503)
        self.assertFalse(self.database.exists())

    def test_cover_uses_plain_app_link_and_isolated_local_assets(self):
        html = self.client.get("/").get_data(as_text=True)
        for text in ('lang="en"', 'name="viewport"', 'id="welcome-title"',
                     'id="cover-enter" href="/learn/"', 'aria-hidden="true">4U',
                     '/static/cover.css', '/static/cover.js', 'defer'):
            self.assertIn(text, html)
        for text in ('visitor_name', 'csrf_token', '/static/phase2.css', '/static/style.css'):
            self.assertNotIn(text, html)
        for asset in ('cover.css', 'cover.js'):
            with self.client.get('/static/' + asset) as response:
                self.assertEqual(response.status_code, 200)

    def test_cover_always_appears_for_active_visit_without_changing_records(self):
        db.initialize_database(self.database)
        self.start()
        name = self.app.config['SESSION_COOKIE_NAME']
        cookie = self.client.get_cookie(name).value
        before = self.database.read_bytes()
        for _ in range(3):
            html = self.client.get('/').get_data(as_text=True)
            self.assertIn('id="welcome-cover"', html)
            self.assertNotIn('Cover Learner', html)
            self.assertEqual(self.client.get_cookie(name).value, cookie)
        self.assertIn('Cover Learner!', self.client.get('/learn/').get_data(as_text=True))
        self.assertEqual(self.database.read_bytes(), before)

    def test_existing_app_endpoint_and_navigation_stay_inside_app(self):
        db.initialize_database(self.database)
        self.start()
        for path in ('/learn/', '/sql/', '/progress/'):
            html = self.client.get(path).get_data(as_text=True)
            self.assertNotIn('id="welcome-cover"', html)
            self.assertIn('Cover Learner', html)
        with self.app.test_request_context():
            from flask import url_for
            self.assertEqual(url_for('index'), '/learn/')
        other = self.app.test_client()
        for path in ('/sql/', '/progress/'):
            self.assertEqual(other.get(path).location, '/learn/')

    def test_end_and_new_visit_redirect_to_name_entry_not_cover(self):
        db.initialize_database(self.database)
        for route in ('new', 'end'):
            self.start()
            self.client.get('/learn/')
            with self.client.session_transaction() as session:
                token = session['csrf_token']
            response = self.client.post('/visits/' + route, data={'csrf_token': token})
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.location, '/learn/')
            self.assertIn('name="visitor_name"', self.client.get(response.location).get_data(as_text=True))
        with closing(db.open_database(self.database)) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM visits').fetchone()[0], 2)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM visits WHERE ended_at IS NULL').fetchone()[0], 0)

    def test_cover_cannot_be_submitted_as_mutating_route(self):
        db.initialize_database(self.database)
        before = self.database.read_bytes()
        self.assertEqual(self.client.post('/').status_code, 405)
        self.assertEqual(self.database.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
