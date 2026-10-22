"""P2.5 connected tracker checks, using disposable schema 3 databases only."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from html.parser import HTMLParser
import sqlite3
import unittest

from werkzeug.datastructures import MultiDict

from learning_with_francis import create_app, db
from learning_with_francis.progress import learning_overview
from learning_with_francis.subjects import SUBJECTS
from test_phase2_sql import HiddenFields, SQLFlowSupport


class Checkboxes(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.items = []
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == 'input' and attributes.get('type') == 'checkbox':
            self.items.append(attributes)


class ProgressTests(SQLFlowSupport, unittest.TestCase):
    def owner(self, client=None):
        with (client or self.client).session_transaction() as session:
            return session['visit_id']

    def token(self, client=None):
        client = client or self.client
        client.get('/progress/')
        with client.session_transaction() as session:
            return session['csrf_token']

    def change(self, status, confirmation=None, slug='sql', client=None, **extra):
        client = client or self.client
        data = {'new_status': status, 'csrf_token': self.token(client), **extra}
        if confirmation is not None:
            data['user_confirmed'] = confirmation
        topic = SUBJECTS[slug]['content'].TOPIC_ID
        return client.post(f'/progress/{topic}/status', data=data)

    def overview(self, client=None):
        owner = self.owner(client)
        with self.app.app_context():
            return learning_overview(owner)

    def activity(self, slug='sql', kind='quiz', score=5, client=None):
        client = client or self.client
        data = HiddenFields(client.get(f'/{slug}/{kind}').get_data(as_text=True)).fields
        module = SUBJECTS[slug]['content']
        questions = module.QUIZ if kind == 'quiz' else (module.PRACTICE[int(data['position'])],)
        for index, question in enumerate(questions):
            data[question['id']] = question['correct'] if index < score else next(
                option for option in question['choices'] if option != question['correct'])
        return client.post(f'/{slug}/{kind}', data=data)

    def test_fresh_visit_shows_four_subjects_zero_activity_and_initial_history(self):
        before = self.path.read_bytes()
        overview = self.overview()
        self.assertEqual([row['subject_id'] for row in overview['topics']], list(SUBJECTS))
        self.assertEqual(overview['totals'], dict(practice_attempts=0, exercises_completed=0, quiz_attempts=0))
        self.assertEqual([row['topic_count'] for row in overview['status_counts']], [4, 0, 0])
        self.assertEqual(len(overview['history']), 4)
        self.assertTrue(all(row['previous_status'] is None and row['changed_at'] for row in overview['history']))
        html = self.client.get('/progress/').get_data(as_text=True)
        self.assertIn('No practice or quiz activity yet', html)
        self.assertEqual(html.count('class="topic-row"'), 4)
        self.assertEqual(html.count('name="user_confirmed" value="yes"'), 4)
        self.assertTrue(all('checked' not in item for item in Checkboxes(html).items))
        self.assertEqual(self.path.read_bytes(), before)

    def test_real_attempts_counts_scores_and_zero_subjects_without_answer_multiplication(self):
        self.activity(kind='practice', score=0)
        self.activity(kind='practice', score=1)
        self.activity(score=3)
        self.activity(score=5)
        overview = self.overview()
        self.assertEqual(overview['totals'], dict(practice_attempts=2, exercises_completed=1, quiz_attempts=2))
        sql = overview['topics'][0]
        self.assertEqual(tuple(sql[key] for key in overview['totals']), (2, 1, 2))
        for row in overview['topics'][1:]:
            self.assertEqual(tuple(row[key] for key in overview['totals']), (0, 0, 0))
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_answers'), [(12,)])
        self.assertEqual(len(overview['activity']), 4)
        html = self.client.get('/progress/').get_data(as_text=True)
        for value in ('3 / 5 correct', '5 / 5 correct', 'Exercise completed', 'Try again'):
            self.assertIn(value, html)
        for row in overview['activity']:
            self.assertTrue(row['submitted_at'])
            self.assertEqual(self.client.get(f"/sql/results/{row['attempt_id']}").status_code, 200)

    def test_status_transitions_confirmation_dates_and_history(self):
        for status, confirmation in [('Needs Review', None), ('Completed', 'yes'),
                                     ('Needs Review', None), ('Still Learning', None), ('Completed', 'yes')]:
            response = self.change(status, confirmation)
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.location, '/progress/')
            topic = self.overview()['topics'][0]
            self.assertEqual(topic['learning_status'], status)
            history = self.overview()['history'][0]
            self.assertEqual(history['new_status'], status)
            self.assertEqual(history['user_confirmed'], int(status == 'Completed'))
            self.assertEqual(topic['understanding_confirmed_at'], history['changed_at'] if status == 'Completed' else None)
        self.assertEqual(len(self.overview()['history']), 9)
        self.assertEqual([item['topic_count'] for item in self.overview()['status_counts']], [3, 0, 1])

    def test_completed_rejects_missing_forged_and_duplicate_confirmations(self):
        before = self.progress()
        for value in (None, '', 'no', 'true', 'True', '1', 'YES', ['yes', 'no'], ['yes', 'yes']):
            with self.subTest(value=value):
                self.assertEqual(self.change('Completed', value).status_code, 400)
                self.assertEqual(self.progress(), before)
        self.assertEqual(self.change('Completed', 'yes').status_code, 303)
        self.change('Needs Review')
        self.assertEqual(self.change('Completed').status_code, 400)

    def test_invalid_and_multiple_statuses_leave_database_unchanged(self):
        token = self.token()
        before = self.path.read_bytes()
        for status in ('', 'complete', 'All', "Completed'; DROP TABLE topics;--"):
            self.assertEqual(self.change(status, 'yes').status_code, 400)
        response = self.client.post('/progress/sql-select-basics/status', data=MultiDict([
            ('csrf_token', token), ('new_status', 'Completed'), ('new_status', 'Still Learning'), ('user_confirmed', 'yes')]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post('/progress/sql-select-basics/status', data={'csrf_token': token}).status_code, 400)
        self.assertEqual(self.path.read_bytes(), before)

    def test_csrf_missing_forged_and_other_visitor_cannot_submit(self):
        other = self.app.test_client()
        self.start(other)
        foreign_token = self.token(other)
        before = self.path.read_bytes()
        for token in (None, 'forged', foreign_token):
            self.assertEqual(self.client.post('/progress/sql-select-basics/status', data={
                'new_status': 'Needs Review', 'csrf_token': token}).status_code, 400)
        self.assertEqual(self.path.read_bytes(), before)

    def test_same_name_visitors_cannot_share_status_activity_or_results(self):
        other = self.app.test_client()
        self.start(other)
        other_id = self.owner(other)
        result = self.activity(score=4)
        self.change('Completed', 'yes')
        other_before = self.rows('SELECT * FROM topic_progress WHERE visit_id=?', (other_id,))
        # Posted and URL owner identifiers cannot select a different owner.
        self.assertEqual(self.change('Needs Review', visit_id=other_id).status_code, 303)
        self.assertEqual(self.rows('SELECT * FROM topic_progress WHERE visit_id=?', (other_id,)), other_before)
        html = other.get('/progress/?visit_id=' + self.owner()).get_data(as_text=True)
        self.assertNotIn('4 / 5 correct', html)
        self.assertEqual(self.overview(other)['totals']['quiz_attempts'], 0)
        self.assertEqual(len(self.overview(other)['history']), 4)
        self.assertEqual(other.get(result.location).status_code, 404)
        self.assertEqual(self.overview(other)['status_counts'][0]['topic_count'], 4)

    def test_two_active_same_name_visitors_save_their_own_answers_and_history(self):
        other = self.app.test_client()
        self.start(other)
        first_id, second_id = self.owner(), self.owner(other)
        self.assertNotEqual(first_id, second_id)
        first_practice = self.activity('sql', 'practice', 1)
        first_quiz = self.activity('sql', 'quiz', 5)
        second_practice = self.activity('python', 'practice', 0, client=other)
        second_quiz = self.activity('python', 'quiz', 3, client=other)
        self.change('Needs Review')
        self.change('Completed', 'yes', slug='python', client=other)
        first, second = self.overview(), self.overview(other)
        self.assertEqual(first['totals'], dict(practice_attempts=1, exercises_completed=1, quiz_attempts=1))
        self.assertEqual(second['totals'], dict(practice_attempts=1, exercises_completed=0, quiz_attempts=1))
        self.assertEqual([(row['subject_id'], row['score']) for row in first['activity']], [('sql', 5), ('sql', 1)])
        self.assertEqual([(row['subject_id'], row['score']) for row in second['activity']], [('python', 3), ('python', 0)])
        self.assertEqual(len(first['history']), 5)
        self.assertEqual(len(second['history']), 5)
        self.assertEqual(first['history'][0]['new_status'], 'Needs Review')
        self.assertEqual(second['history'][0]['new_status'], 'Completed')
        for own_client, foreign_client, results in ((self.client, other, (first_practice, first_quiz)),
                                                     (other, self.client, (second_practice, second_quiz))):
            for result in results:
                self.assertEqual(own_client.get(result.location).status_code, 200)
                self.assertEqual(foreign_client.get(result.location).status_code, 404)
        self.assertEqual(self.rows('''SELECT a.visit_id, COUNT(b.question_id)
                                     FROM learning_attempts a JOIN learning_answers b USING(attempt_id)
                                     GROUP BY a.visit_id ORDER BY a.visit_id'''), sorted([(first_id, 6), (second_id, 6)]))
        self.assertTrue(all(row[0] for row in self.rows('SELECT submitted_at FROM learning_attempts')))

    def test_returning_tab_resumes_but_explicit_new_visit_starts_empty(self):
        self.activity(kind='practice', score=1)
        self.activity(score=4)
        old_id = self.owner()
        before = self.rows('SELECT * FROM learning_attempts WHERE visit_id=?', (old_id,))
        for path in ('/learn/', '/progress/', '/learn/'):
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn('Current visit started:', html)
            self.assertIn('Start New Visit', html)
            self.assertEqual(self.owner(), old_id)
        self.assertEqual(self.overview()['totals']['quiz_attempts'], 1)
        response = self.client.post('/visits/new', data={'csrf_token': self.token()})
        self.assertEqual(response.status_code, 303)
        self.start(self.client)
        self.assertNotEqual(self.owner(), old_id)
        overview = self.overview()
        self.assertEqual(overview['totals'], dict(practice_attempts=0, exercises_completed=0, quiz_attempts=0))
        self.assertEqual(overview['activity'], [])
        self.assertEqual(len(overview['history']), 4)
        self.assertTrue(all(row['previous_status'] is None and row['new_status'] == 'Still Learning'
                            and row['user_confirmed'] == 0 for row in overview['history']))
        html = self.client.get('/progress/').get_data(as_text=True)
        self.assertIn('These record your starting statuses, not practice', html)
        self.assertIn('No practice or quiz activity yet', html)
        self.assertEqual(self.rows('SELECT * FROM learning_attempts WHERE visit_id=?', (old_id,)), before)

    def test_nonexistent_or_unowned_topic_is_rejected(self):
        other = self.app.test_client()
        self.start(other)
        own_id = self.owner()
        with closing(db.open_database(self.path)) as connection:
            connection.execute('DELETE FROM topic_status_history WHERE visit_id=? AND topic_id=?', (own_id, 'sap-basics'))
            connection.execute('DELETE FROM topic_progress WHERE visit_id=? AND topic_id=?', (own_id, 'sap-basics'))
            connection.commit()
        before = self.path.read_bytes()
        for topic in ('unknown', 'sap-basics', "sql' OR '1'='1"):
            self.assertEqual(self.client.post(f'/progress/{topic}/status', data={
                'csrf_token': self.token(), 'new_status': 'Needs Review'}).status_code, 404)
        self.assertEqual(self.path.read_bytes(), before)

    def test_history_failure_rolls_back_status_and_confirmation(self):
        self.change('Completed', 'yes')
        before = self.progress()
        with closing(db.open_database(self.path)) as connection:
            connection.execute("""CREATE TRIGGER reject_change BEFORE INSERT ON topic_status_history
                                  BEGIN SELECT RAISE(ABORT, 'simulated history failure'); END""")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'simulated history failure'):
            self.change('Needs Review')
        self.assertEqual(self.progress(), before)

    def test_repeated_save_and_reload_do_not_add_status_events(self):
        self.change('Completed', 'yes')
        before = self.progress()
        for _ in range(2):
            self.assertEqual(self.change('Completed', 'yes').status_code, 303)
            self.assertEqual(self.client.get('/progress/').status_code, 200)
        self.assertEqual(self.progress(), before)
        # A repeat of Completed still needs explicit confirmation.
        self.assertEqual(self.change('Completed').status_code, 400)

    def test_concurrent_identical_saves_create_one_history_change(self):
        token = self.token()
        name = self.app.config['SESSION_COOKIE_NAME']
        cookie = self.client.get_cookie(name).value
        def submit(_):
            client = self.app.test_client()
            client.set_cookie(name, cookie)
            return client.post('/progress/sql-select-basics/status', data={
                'csrf_token': token, 'new_status': 'Needs Review'}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(list(executor.map(submit, range(2))), [303, 303])
        self.assertEqual(len(self.overview()['history']), 5)

    def test_perfect_scores_never_change_understanding_or_status_history(self):
        self.change('Needs Review')
        before = self.progress()
        for slug in SUBJECTS:
            self.assertEqual(self.activity(slug, 'practice', 1).status_code, 303)
            self.assertEqual(self.activity(slug, 'quiz', 5).status_code, 303)
        self.assertEqual(self.progress(), before)
        self.assertEqual(self.overview()['totals'], dict(practice_attempts=4, exercises_completed=4, quiz_attempts=4))

    def test_end_visit_old_cookie_and_new_visit_preserve_but_hide_old_records(self):
        self.activity()
        self.change('Completed', 'yes')
        old_id = self.owner()
        token = self.token()
        name = self.app.config['SESSION_COOKIE_NAME']
        cookie = self.client.get_cookie(name).value
        self.client.post('/visits/new', data={'csrf_token': token})
        before = self.progress()
        replay = self.app.test_client()
        replay.set_cookie(name, cookie)
        self.assertEqual(replay.get('/progress/').status_code, 303)
        self.assertEqual(replay.post('/progress/sql-select-basics/status', data={
            'csrf_token': token, 'new_status': 'Needs Review'}).status_code, 303)
        self.assertEqual(self.progress(), before)
        self.start(self.client)
        self.assertNotEqual(old_id, self.owner())
        self.assertEqual(self.overview()['totals']['quiz_attempts'], 0)
        self.assertEqual(self.overview()['status_counts'][0]['topic_count'], 4)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts WHERE visit_id=?', (old_id,)), [(1,)])

    def test_persistence_after_application_restart(self):
        self.activity(score=3)
        self.change('Completed', 'yes')
        cookie_name = self.app.config['SESSION_COOKIE_NAME']
        cookie = self.client.get_cookie(cookie_name).value
        restarted = create_app(self.config).test_client()
        restarted.set_cookie(cookie_name, cookie)
        html = restarted.get('/progress/').get_data(as_text=True)
        self.assertIn('data-learning-status="Completed"', html)
        self.assertIn('3 / 5 correct', html)
        self.assertIn('Confirmed', html)
        self.assertTrue(all('checked' not in item for item in Checkboxes(html).items))

    def test_navigation_across_subjects_and_result_pages_and_unchanged_assets(self):
        self.assertIn('href="/progress/"', self.client.get('/learn/').get_data(as_text=True))
        for slug in SUBJECTS:
            for path in (f'/{slug}/', f'/{slug}/practice', f'/{slug}/quiz'):
                self.assertIn('href="/progress/"', self.client.get(path).get_data(as_text=True))
            result = self.activity(slug)
            self.assertIn('href="/progress/"', self.client.get(result.location).get_data(as_text=True))
        with self.client.get('/static/topics.js') as response:
            self.assertEqual(response.status_code, 200)
            self.assertIn('validateTopicSubmission', response.get_data(as_text=True))

    def test_explicit_visit_controls_and_browser_restore_explanation_on_all_pages(self):
        paths = ['/learn/', '/progress/']
        for slug in SUBJECTS:
            paths.extend((f'/{slug}/', f'/{slug}/practice', f'/{slug}/quiz'))
        paths.append(self.activity('sql').location)
        before = self.path.read_bytes()
        for path in paths:
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertIn('aria-label="Temporary visit controls"', html)
                self.assertIn('action="/visits/end"', html)
                self.assertIn('action="/visits/new"', html)
                self.assertIn('Closing and reopening the browser may restore this visit', html)
                self.assertIn('new identity with zero activity', html)
                self.assertTrue(HiddenFields(html).fields['csrf_token'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_browser_cookie_loss_or_restore_never_retrieves_another_visitors_progress(self):
        self.activity(score=4)
        old_id = self.owner()
        old_rows = self.rows('SELECT * FROM learning_attempts WHERE visit_id=?', (old_id,))
        cookie_name = self.app.config['SESSION_COOKIE_NAME']
        cookie = self.client.get_cookie(cookie_name).value
        # A browser that discards its session cookie must show name entry.
        no_cookie = self.app.test_client()
        self.assertIn('Start your learning visit', no_cookie.get('/learn/').get_data(as_text=True))
        self.assertEqual(no_cookie.get('/progress/').status_code, 303)
        # A browser that restores its cookie continues that same, still-active visit.
        restored = self.app.test_client()
        restored.set_cookie(cookie_name, cookie)
        self.assertEqual(self.overview(restored)['totals']['quiz_attempts'], 1)
        self.assertEqual(self.owner(restored), old_id)
        self.assertEqual(restored.post('/visits/new', data={'csrf_token': self.token(restored)}).status_code, 303)
        self.start(restored)
        self.assertNotEqual(self.owner(restored), old_id)
        self.assertEqual(self.overview(restored)['totals'], dict(practice_attempts=0, exercises_completed=0, quiz_attempts=0))
        self.assertEqual(self.overview(restored)['status_counts'][0]['topic_count'], 4)
        replay = self.app.test_client()
        replay.set_cookie(cookie_name, cookie)
        self.assertEqual(replay.get('/progress/').status_code, 303)
        self.assertEqual(self.rows('SELECT * FROM learning_attempts WHERE visit_id=?', (old_id,)), old_rows)

    def test_unauthenticated_invalid_and_ended_visit_cannot_view_progress(self):
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get('/progress/').status_code, 303)
        with anonymous.session_transaction() as session:
            session['visit_id'] = 'not-a-real-visit'
        self.assertEqual(anonymous.get('/progress/').status_code, 303)
        self.assertEqual(self.client.get('/progress/sql-select-basics/status').status_code, 405)
        token = self.token()
        self.client.post('/visits/end', data={'csrf_token': token})
        self.assertEqual(self.client.get('/progress/').status_code, 303)

    def test_empty_progress_has_helpful_messages_and_error_keeps_summary(self):
        response = self.change('Completed')
        self.assertIn('Your learning summary', response.get_data(as_text=True))
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        own_id = self.owner()
        with closing(db.open_database(self.path)) as connection:
            connection.execute('DELETE FROM topic_status_history WHERE visit_id=?', (own_id,))
            connection.execute('DELETE FROM topic_progress WHERE visit_id=?', (own_id,))
            connection.commit()
        html = self.client.get('/progress/').get_data(as_text=True)
        self.assertIn('No learning topics recorded for this visit', html)
        self.assertNotIn('id="topic-filter"', html)
        self.assertEqual([row['topic_count'] for row in self.overview()['status_counts']], [0, 0, 0])


if __name__ == '__main__':
    unittest.main()
