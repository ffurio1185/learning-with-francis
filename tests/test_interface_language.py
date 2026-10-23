"""L2 interface, drafts and security. All data is disposable current-schema under /tmp."""

from html import unescape
from html.parser import HTMLParser
from retention_support import learning_snapshot

import re
import unittest
from unittest.mock import patch

from werkzeug.datastructures import MultiDict
from itsdangerous import URLSafeTimedSerializer

from learning_with_francis import create_app
from learning_with_francis.i18n import navigation_signer
from learning_with_francis.subjects import SUBJECTS
from test_phase2_sql import HiddenFields, SQLFlowSupport


class CheckedAnswers(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.answers = {}
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == 'input' and attributes.get('type') == 'radio' and 'checked' in attributes:
            self.answers[attributes['name']] = attributes['value']


class InterfaceLanguageTests(SQLFlowSupport, unittest.TestCase):
    def fields_at(self, path, client=None):
        return HiddenFields((client or self.client).get(path).text).fields

    def switch(self, path='/progress/', language='de', client=None, **extra):
        client = client or self.client
        data = self.fields_at(path, client)
        return client.post('/preferences/language', data={**data, **extra, 'language': language})

    def test_default_english_interface_and_canonical_form_values(self):
        for path, text in (('/learn/', 'Your learning subjects'), ('/progress/', 'My Progress'),
                           ('/sql/quiz', 'Submit quiz')):
            html = self.client.get(path, headers={'Accept-Language': 'de-DE'}).text
            self.assertIn('<html lang="en">', html)
            self.assertIn(text, html)
        self.assertIn('value="Completed"', self.client.get('/progress/').text)

    def test_german_navigation_status_labels_history_and_zero_activity(self):
        response = self.switch()
        self.assertEqual(response.location, '/progress/')
        before = learning_snapshot(self.path)
        for path in ('/learn/', '/progress/', '/sql/', '/python/', '/javascript/', '/sap/', '/sql/quiz'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('<html lang="de">', response.text)
            self.assertIn('Besuch beenden', response.text)
            self.assertNotIn('>End Visit<', response.text)
        html = self.client.get('/progress/').text
        for text in ('Mein Fortschritt', 'Übungsversuche', 'Quizversuche', 'Noch am Lernen',
                     'Lernstatusverlauf', 'Besuch begonnen', 'Nicht zutreffend'):
            self.assertIn(text, html)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts'), [(0,)])
        self.assertEqual(learning_snapshot(self.path), before)


    def test_german_name_entry_validation_and_native_draft_preservation(self):
        client = self.app.test_client()
        fields = self.fields_at('/learn/', client)
        before = learning_snapshot(self.path)
        response = client.post('/preferences/language', data={**fields, 'visitor_name': "O'Neil", 'language': 'de'})
        self.assertEqual(response.location, '/learn/')
        html = client.get(response.location).text
        self.assertIn('value="O&#39;Neil"', html)
        self.assertIn('Dein Name', html)
        self.assertEqual(learning_snapshot(self.path), before)
        fields = self.fields_at('/learn/', client)
        for name in ('', '123', 'A' * 51, '<script>bad</script>'):
            response = client.post('/visits/start', data={**fields, 'visitor_name': name})
            self.assertEqual(response.status_code, 400)
            self.assertIn('role="alert"', response.text)
            self.assertNotIn('Please enter', response.text)
            self.assertNotIn('<script>bad</script>', response.text)
        response = client.post('/visits/start', data={**fields, 'visitor_name': 'Francis'})
        self.assertEqual(response.status_code, 303)
        self.assertIn('Willkommen bei Learning with Francis, Francis!', client.get('/learn/').text)


    def test_german_confirmation_enforced_without_javascript_and_statuses_reversible(self):
        self.switch()
        path = '/progress/sql-select-basics/status'
        fields = self.fields_at('/progress/')
        before = learning_snapshot(self.path)
        for status, confirmation in (('Completed', None), ('Completed', 'true'), ('Abgeschlossen', 'yes')):
            data = {**fields, 'new_status': status}
            if confirmation is not None:
                data['user_confirmed'] = confirmation
            response = self.client.post(path, data=data)
            self.assertEqual(response.status_code, 400)
            self.assertNotIn('Please confirm', response.text)
            self.assertEqual(learning_snapshot(self.path), before)
        self.assertEqual(self.client.post(path, data={**fields, 'new_status': 'Completed', 'user_confirmed': 'yes'}).status_code, 303)
        html = self.client.get('/progress/').text
        self.assertIn('Dein Lernstatus wurde gespeichert.', html)
        self.assertIn('data-learning-status="Completed"', html)
        self.assertIn('Bestätigt', html)
        self.assertEqual(self.client.post(path, data={**fields, 'new_status': 'Needs Review'}).status_code, 303)
        self.assertEqual(self.rows("SELECT learning_status,understanding_confirmed_at FROM topic_progress WHERE topic_id='sql-select-basics'"), [('Needs Review', None)])
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts'), [(0,)])


    def test_german_csrf_and_activity_errors_are_translated(self):
        self.switch()
        before = learning_snapshot(self.path)
        self.assertIn('Dieses Formular ist abgelaufen', self.client.post('/visits/end').text)
        self.assertIn('Bitte lade', self.client.post('/progress/sql-select-basics/status').text)
        for slug in SUBJECTS:
            data = self.fields_at(f'/{slug}/quiz')
            response = self.client.post(f'/{slug}/quiz', data=data)
            self.assertEqual(response.status_code, 400)
            self.assertIn('Bitte wähle für jede Frage', response.text)
            data['submission_token'] = 'forged'
            response = self.client.post(f'/{slug}/quiz', data=data)
            self.assertIn('Aufgabenformular ist abgelaufen', response.text)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_language_change_preserves_saved_results_and_utc_dates_exactly(self):
        result = self.submit(3)
        self.submit(1, 'practice')
        before = learning_snapshot(self.path)
        response = self.switch(result.location)
        self.assertEqual(response.location, result.location)
        html = self.client.get(response.location).text
        self.assertIn('3 von 5', html)
        self.assertIn('Deine Antwort:', html)
        self.assertIn('Richtige Antwort:', html)
        self.assertIn('Europe/Berlin', html)
        response = self.switch('/progress/', 'en')
        self.assertIn('3 / 5 correct', self.client.get(response.location).text)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_all_subject_quiz_drafts_keep_answers_and_submission_identity(self):
        for slug, subject in SUBJECTS.items():
            with self.subTest(subject=slug):
                path = f'/{slug}/quiz'
                fields = self.fields_at(path)
                choices = {q['id']: q['correct'] for q in subject['content'].QUIZ}
                before = learning_snapshot(self.path)
                response = self.client.post('/preferences/language', data={**fields, **choices, 'language': 'de', 'score': '999'})
                self.assertEqual(response.location, path)
                html = self.client.get(response.location).text
                self.assertEqual(CheckedAnswers(html).answers, choices)
                new_fields = HiddenFields(html).fields
                self.assertEqual(new_fields['submission_token'], fields['submission_token'])
                self.assertEqual(learning_snapshot(self.path), before)
                response = self.client.post(path, data={**new_fields, **choices})
                self.assertEqual(response.status_code, 303)
                self.assertEqual(self.client.post(path, data={**new_fields, **choices}).location, response.location)
        self.assertEqual(self.rows('SELECT score, total_questions FROM learning_attempts'), [(5,5)] * 4)
        self.assertEqual(self.rows('SELECT DISTINCT learning_status FROM topic_progress'), [('Still Learning',)])


    def test_practice_draft_retains_current_question_and_round(self):
        path = '/sql/practice'
        for _ in range(2):
            fields = self.fields_at(path)
            position = int(fields['position'])
            question = SUBJECTS['sql']['content'].PRACTICE[position]
            response = self.client.post('/sql/practice', data={**fields, question['id']: question['correct']})
            html = self.client.get(response.location).text
            path = unescape(re.search(r'id="practice-next" href="([^"]+)"', html)[1])
        fields = self.fields_at(path)
        self.assertEqual(fields['position'], '2')
        question = SUBJECTS['sql']['content'].PRACTICE[2]
        before = learning_snapshot(self.path)
        response = self.client.post('/preferences/language', data={**fields, question['id']: question['correct'], 'language': 'de'})
        html = self.client.get(response.location).text
        self.assertIn('Frage 3 von 10', html)
        self.assertEqual(CheckedAnswers(html).answers, {question['id']: question['correct']})
        self.assertEqual(learning_snapshot(self.path), before)
        response = self.client.post('/sql/practice', data={**HiddenFields(html).fields, question['id']: question['correct']})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts'), [(3,)])


    def test_tampered_duplicate_expired_and_cross_visit_return_tokens_are_rejected(self):
        fields = self.fields_at('/progress/')
        other = self.app.test_client()
        self.start(other)
        foreign = self.fields_at('/progress/', other)['return_token']
        with self.app.app_context():
            with patch('itsdangerous.timed.TimestampSigner.get_timestamp', return_value=1):
                expired = navigation_signer().dumps({'path': '/progress/', 'visit': 'old'})
        cases = [fields['return_token'] + 'tampered', foreign, expired, '']
        before = learning_snapshot(self.path)
        for token in cases:
            response = self.client.post('/preferences/language', data={**fields, 'return_token': token, 'language': 'de'})
            self.assertEqual(response.status_code, 400)
            with self.client.session_transaction() as session:
                self.assertNotIn('language', session)
        data = MultiDict([('csrf_token', fields['csrf_token']), ('return_token', fields['return_token']),
                          ('return_token', fields['return_token']), ('language', 'de')])
        self.assertEqual(self.client.post('/preferences/language', data=data).status_code, 400)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_only_local_application_get_destinations_are_accepted(self):
        fields = self.fields_at('/progress/')
        with self.client.session_transaction() as session:
            owner = session['visit_id']
        for path in ('https://example.invalid/', '//example.invalid/', '/\\example.invalid/',
                     '/static/cover.css', '/visits/end', '/progress/#fragment'):
            with self.app.app_context():
                token = navigation_signer().dumps({'path': path, 'visit': owner})
            response = self.client.post('/preferences/language', data={**fields, 'return_token': token, 'language': 'de'})
            self.assertEqual(response.status_code, 400, path)

    def test_drafts_are_small_escaped_and_cannot_save_scores_or_change_owner(self):
        path = '/sql/practice'
        fields = self.fields_at(path)
        before = learning_snapshot(self.path)
        for position in ('²', '９', '-1', '999999999999999999999', ['1', '2']):
            data = {**fields, 'position': position, 'q1': '<script>bad</script>', 'language': 'de',
                    'score': '5', 'visit_id': 'foreign-owner'}
            response = self.client.post('/preferences/language', data=data)
            self.assertEqual(response.status_code, 303)
            self.assertNotIn('<script>bad</script>', self.client.get(response.location).text)
        self.assertEqual(learning_snapshot(self.path), before)
        with self.client.session_transaction() as session:
            self.assertNotEqual(session['visit_id'], 'foreign-owner')


    def test_same_name_visitors_have_independent_languages_results_and_statuses(self):
        other = self.app.test_client()
        self.start(other)
        self.switch()
        result = self.submit(5)
        fields = self.fields_at('/progress/')
        self.client.post('/progress/sql-select-basics/status', data={**fields, 'new_status': 'Needs Review'})
        before = learning_snapshot(self.path)
        self.assertIn('5 / 5 richtig', self.client.get('/progress/').text)
        self.assertIn('No practice or quiz activity yet', other.get('/progress/').text)
        self.assertEqual(other.get(result.location).status_code, 404)
        self.assertNotIn('5 von 5', other.get(result.location).text)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_end_and_new_visit_keep_locale_but_discard_drafts_and_old_return_tokens(self):
        self.switch()
        for route in ('end', 'new'):
            fields = self.fields_at('/progress/')
            with self.client.session_transaction() as session:
                session['language_draft'] = {'fields': {'q1': 'a'}, 'path': '/sql/quiz', 'visit': session['visit_id']}
            response = self.client.post('/visits/' + route, data={'csrf_token': fields['csrf_token']})
            html = self.client.get(response.location).text
            self.assertIn('Besuch', html)
            with self.client.session_transaction() as session:
                self.assertNotIn('visit_id', session)
                self.assertNotIn('language_draft', session)
                self.assertEqual(session['language'], 'de')
            self.start(self.client)
            fresh = self.fields_at('/progress/')
            response = self.client.post('/preferences/language', data={**fresh, 'language': 'en', 'return_token': fields['return_token']})
            self.assertEqual(response.status_code, 400)

    def test_empty_database_setup_and_http_errors_are_localized_without_writes(self):
        self.switch()
        before = learning_snapshot(self.path)
        for path in ('/unknown/', '/sql/results/not-owned'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertIn('Fehler bei der Anfrage', response.text)
            self.assertIn('nicht verfügbar', response.text)
        response = self.client.get('/preferences/language')
        self.assertEqual(response.status_code, 405)
        self.assertIn('Allow', response.headers)
        self.assertEqual(learning_snapshot(self.path), before)
        missing = create_app({**self.config, 'DATABASE': str(self.root/'missing.db')}).test_client()
        missing.get('/')
        with missing.session_transaction() as session:
            session['language'] = 'de'
        response = missing.get('/learn/')
        self.assertEqual(response.status_code, 503)
        self.assertIn('Datenbank eingerichtet', response.text)
        self.assertFalse((self.root/'missing.db').exists())


    def test_german_timezone_labels_keep_dst_and_machine_readable_offsets(self):
        from flask import render_template_string, session
        before = learning_snapshot(self.path)
        with self.app.test_request_context("/"):
            session["language"] = "de"
            html = render_template_string("{% from '_time.html' import local_time %}{{ local_time('2026-01-15 12:00:00') }} {{ local_time('2026-07-15 12:00:00') }}")
            self.assertIn("13:00:00 MEZ", html)
            self.assertIn("14:00:00 MESZ", html)
            self.assertIn("2026-01-15T13:00:00+01:00", html)
            self.assertIn("2026-07-15T14:00:00+02:00", html)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_all_subject_content_is_translated_after_l4(self):
        self.switch()
        html = self.client.get('/sql/').text
        self.assertIn('SQL: SELECT und WHERE', html)
        self.assertIn('SELECT name, city FROM learners;', html)
        self.assertIn('class="lesson-material" lang="de"', html)
        for slug, subject in SUBJECTS.items():
            html = self.client.get(f'/{slug}/quiz').text
            if slug != 'sql':
                self.assertNotIn(subject['content'].QUIZ[0]['prompt'], unescape(html))
            self.assertIn('Quiz abschicken', html)


if __name__ == '__main__':
    unittest.main()
