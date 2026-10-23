"""Integrated legal-document checks with disposable storage only."""
from retention_support import learning_snapshot

import unittest
from unittest.mock import patch

from learning_with_francis import create_app, db
from learning_with_francis.subjects import SUBJECTS
import test_production as production_tests
from test_phase2_sql import HiddenFields


class PrivacyTests(unittest.TestCase):
    setUp = production_tests.ProductionTests.setUp
    app = production_tests.ProductionTests.app
    rows = production_tests.ProductionTests.rows
    get = production_tests.ProductionTests.get
    post = production_tests.ProductionTests.post
    start = production_tests.ProductionTests.start

    def switch(self, client, language, path='/privacy/'):
        fields = HiddenFields(self.get(client, path).text).fields
        return self.post(client, '/preferences/language', {**fields, 'language': language})

    def test_privacy_and_language_switch_work_without_a_database(self):
        app = create_app({'TESTING': True, 'DATABASE': str(self.path), 'SECRET_KEY': self.env['LWF_SECRET_KEY']})
        client = app.test_client()
        with patch.object(db, 'get_db', side_effect=AssertionError('Privacy must not access the database')):
            self.assertEqual(self.get(client, '/privacy/').status_code, 200)
            self.assertEqual(self.switch(client, 'de').location, '/privacy/')
            self.assertIn('<html lang="de">', self.get(client, '/privacy/').text)
        self.assertFalse(self.path.exists())

    def test_default_english_and_german_show_confirmed_operator_details(self):
        client = self.app().test_client()
        response = client.get('/privacy/', base_url='https://localhost', headers={'Accept-Language': 'de'})
        self.assertIn('<html lang="en">', response.text)
        self.assertIn('Francis Furio', response.text)
        self.assertIn('29664 Walsrode', response.text)
        self.assertIn('mailto:', response.text)
        self.assertNotIn('Operator and contact details pending', response.text)
        self.assertNotIn('Not yet approved for public launch', response.text)
        self.assertEqual(self.switch(client, 'de').location, '/privacy/')
        text = self.get(client, '/privacy/').text
        for phrase in ('Datenschutzerklärung', 'nichtkommerzielles Bildungsprojekt', 'Prüfung des Hosting-Kontos', '30 Minuten', 'Inaktivitätsregel', 'E-Mail:'):
            self.assertIn(phrase, text)

    def test_policy_describes_approved_retention_without_invented_erasure_promises(self):
        client = self.app().test_client()
        text = self.get(client, '/privacy/').text
        for phrase in ('nickname', 'randomly generated visit ID', 'answers', 'scores', 'completion confirmation', 'learning_with_francis_visit', 'not encrypted', '12-hour', '30 minutes', 'database transaction', 'before activity renewal', 'no exact 30-minute physical-deletion guarantee', 'no automatic email deletion', 'Article 6(1)(f)', 'Standard Contractual Clauses', 'outside the EEA', 'not been independently checked'):
            self.assertIn(phrase, text)
        for stale in ('no automatic deletion schedule', 'does not erase SQLite rows', 'contact for requests is still pending', 'Proposed legal basis, subject to operator approval'):
            self.assertNotIn(stale, text)
        for url in ('https://render.com/privacy', 'https://render.com/dpa', 'https://render.com/docs/free', 'https://render.com/docs/logging'):
            self.assertIn(url, text)

    def test_cover_and_name_entry_links_do_not_create_visits(self):
        client = self.app().test_client()
        before = learning_snapshot(self.path)
        for path in ('/', '/learn/', '/privacy/', '/impressum/'):
            response = self.get(client, path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('href="/privacy/"', response.text)
            self.assertIn('href="/impressum/"', response.text)
        home = self.get(client, '/learn/').text
        self.assertLess(home.index('href="/privacy/"'), home.index('id="visitor-name"'))
        self.assertEqual(learning_snapshot(self.path), before)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM visits'), [(0,)])


    def test_all_learning_pages_results_progress_and_errors_link_to_policy(self):
        client = self.app().test_client()
        self.start(client)
        fields = HiddenFields(self.get(client, '/sql/quiz').text).fields
        answers = {q['id']: q['correct'] for q in SUBJECTS['sql']['content'].QUIZ}
        result = self.post(client, '/sql/quiz', {**fields, **answers})
        paths = ['/learn/', '/progress/', result.location, '/missing-page/']
        paths += [f'/{slug}{suffix}' for slug in SUBJECTS for suffix in ('/', '/practice', '/quiz')]
        before = learning_snapshot(self.path)
        for path in paths:
            html = self.get(client, path).text
            self.assertIn('href="/privacy/"', html, path)
            self.assertIn('href="/impressum/"', html, path)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_policy_language_switch_preserves_identity_saved_answers_and_statuses(self):
        app = self.app();client = app.test_client();self.start(client)
        fields = HiddenFields(self.get(client, '/sql/quiz').text).fields
        answers = {q['id']: q['correct'] for q in SUBJECTS['sql']['content'].QUIZ}
        result = self.post(client, '/sql/quiz', {**fields, **answers})
        fields = HiddenFields(self.get(client, '/progress/').text).fields
        response = self.post(client, '/progress/sql-select-basics/status', {**fields, 'new_status': 'Completed', 'user_confirmed': 'yes'})
        self.assertEqual(response.status_code, 303)
        with client.session_transaction(base_url='https://localhost') as session:
            visit_id = session['visit_id']
        before = learning_snapshot(self.path)
        for language in ('de', 'en'):
            self.assertEqual(self.switch(client, language).location, '/privacy/')
            self.assertEqual(self.get(client, '/privacy/').status_code, 200)
            with client.session_transaction(base_url='https://localhost') as session:
                self.assertEqual(session['visit_id'], visit_id)
            self.assertEqual(self.get(client, result.location).status_code, 200)
        self.assertEqual(learning_snapshot(self.path), before)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_answers'), [(5,)])
        self.assertEqual(self.rows("SELECT learning_status FROM topic_progress WHERE topic_id='sql-select-basics'"), [('Completed',)])


    def test_language_form_still_rejects_missing_csrf_and_external_redirects(self):
        from learning_with_francis.i18n import navigation_signer
        app = self.app();client = app.test_client()
        self.assertEqual(self.post(client, '/preferences/language', {'language': 'de'}).status_code, 400)
        fields = HiddenFields(self.get(client, '/privacy/').text).fields
        with app.app_context():
            forged = navigation_signer().dumps({'path': 'https://attacker.invalid/', 'visit': None})
        self.assertEqual(self.post(client, '/preferences/language', {**fields, 'return_token': forged, 'language': 'de'}).status_code, 400)
        self.assertIn('<html lang="en">', self.get(client, '/privacy/').text)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM visits'), [(0,)])

    def test_legal_documents_remain_public_after_visit_deletion(self):
        app = self.app();client = app.test_client();self.start(client)
        fields = HiddenFields(self.get(client, '/learn/').text).fields
        self.assertEqual(self.post(client, '/visits/end', fields).status_code, 303)
        before = learning_snapshot(self.path)
        for path in ('/privacy/', '/impressum/'):
            self.assertEqual(self.get(client, path).status_code, 200)
        self.assertEqual(self.get(client, '/progress/').status_code, 303)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM visits'), [(0,)])
        self.assertEqual(self.rows('SELECT COUNT(*) FROM topic_status_history'), [(0,)])
        self.assertEqual(learning_snapshot(self.path), before)


    def test_policy_isolation_and_python_confirmation_still_hold(self):
        app = self.app();first = app.test_client();second = app.test_client();self.start(first);self.start(second)
        fields = HiddenFields(self.get(first, '/sql/quiz').text).fields
        answers = {q['id']: q['correct'] for q in SUBJECTS['sql']['content'].QUIZ}
        result = self.post(first, '/sql/quiz', {**fields, **answers})
        self.get(second, '/privacy/');self.switch(second, 'de')
        self.assertEqual(self.get(second, result.location).status_code, 404)
        fields = HiddenFields(self.get(second, '/progress/').text).fields
        self.assertEqual(self.post(second, '/progress/sql-select-basics/status', {**fields, 'new_status': 'Completed'}).status_code, 400)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM topic_progress WHERE learning_status='Completed'"), [(0,)])
        self.assertEqual(self.rows('PRAGMA integrity_check'), [('ok',)])
        self.assertEqual(self.rows('PRAGMA foreign_key_check'), [])

    def test_production_security_and_no_external_embeds(self):
        client = self.app().test_client();response = self.get(client, '/privacy/')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertIn("form-action 'self'", response.headers['Content-Security-Policy'])
        self.assertIn('Secure', response.headers.get('Set-Cookie', ''))
        for tag in ('<iframe', '<audio', '<script'):
            self.assertNotIn(tag, response.text)
        self.assertIn('name="robots" content="noindex"', response.text)

    def test_impressum_is_bilingual_database_independent_and_links_back_safely(self):
        app = create_app({'TESTING': True, 'DATABASE': str(self.path), 'SECRET_KEY': self.env['LWF_SECRET_KEY']})
        client = app.test_client()
        with patch.object(db, 'get_db', side_effect=AssertionError('Legal pages must not query storage')):
            for language in ('en', 'de'):
                self.assertEqual(self.switch(client, language, '/impressum/').location, '/impressum/')
                page = self.get(client, '/impressum/')
                self.assertEqual(page.status_code, 200)
                self.assertIn('Francis Furio', page.text)
                self.assertIn('29664 Walsrode', page.text)
                self.assertIn('mailto:', page.text)
                self.assertIn('href="/privacy/"', page.text)
                self.assertIn('aria-current="page">Impressum', page.text)
                self.assertIn('Anbieter und Kontakt' if language == 'de' else 'Operator and contact', page.text)
        self.assertFalse(self.path.exists())

    def test_legal_gets_and_language_changes_do_not_renew_visit_activity(self):
        from datetime import timedelta
        from learning_with_francis import visitors
        app = self.app();client = app.test_client();self.start(client)
        before = self.rows('SELECT last_activity_at FROM visits')
        now = visitors.utc_now() + timedelta(minutes=5)
        with patch.object(visitors, 'utc_now', return_value=now):
            for path in ('/privacy/', '/impressum/'):
                for language in ('de', 'en'):
                    self.assertEqual(self.switch(client, language, path).location, path)
                    self.assertEqual(self.get(client, path).status_code, 200)
                    self.assertEqual(self.rows('SELECT last_activity_at FROM visits'), before)

    def test_impressum_switch_preserves_quiz_drafts_then_actual_saved_results(self):
        app = self.app();client = app.test_client();self.start(client)
        fields = HiddenFields(self.get(client, '/sql/quiz').text).fields
        answers = {q['id']: q['correct'] for q in SUBJECTS['sql']['content'].QUIZ}
        self.assertEqual(self.switch(client, 'de', '/impressum/').location, '/impressum/')
        self.assertEqual(self.get(client, '/impressum/').status_code, 200)
        result = self.post(client, '/sql/quiz', {**fields, **answers})
        self.assertEqual(result.status_code, 303)
        before = learning_snapshot(self.path)
        for path in ('/privacy/', '/impressum/'):
            self.switch(client, 'en', path)
            self.get(client, path)
        self.assertEqual(learning_snapshot(self.path), before)
        self.assertEqual(self.rows('SELECT score,total_questions FROM learning_attempts'), [(5,5)])

    def test_impressum_return_tokens_reject_external_and_cross_visit_targets(self):
        from learning_with_francis.i18n import navigation_signer
        app=self.app();client=app.test_client();other=app.test_client();self.start(client);self.start(other)
        fields=HiddenFields(self.get(client, '/impressum/').text).fields
        self.assertEqual(self.post(other, '/preferences/language', {**fields, 'language':'de'}).status_code, 400)
        with app.app_context():
            with client.session_transaction(base_url='https://localhost') as session:
                forged=navigation_signer().dumps({'path':'//attacker.invalid/','visit':session['visit_id']})
        self.assertEqual(self.post(client, '/preferences/language', {**fields,'return_token':forged,'language':'de'}).status_code,400)

    def test_posting_to_legal_pages_never_mutates_learning_data(self):
        client=self.app().test_client();self.start(client)
        before=learning_snapshot(self.path)
        for path in ('/privacy/','/impressum/'):
            self.assertEqual(self.post(client,path,{'visit_id':'other','new_status':'Completed','user_confirmed':'yes'}).status_code,405)
        self.assertEqual(learning_snapshot(self.path),before)



if __name__ == '__main__':
    unittest.main()
