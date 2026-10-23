"""Free demonstration behavior; all databases are disposable under /tmp."""
from pathlib import Path
from retention_support import learning_snapshot

import unittest

import test_production as production_tests
from test_phase2_sql import HiddenFields
from learning_with_francis import create_app
from learning_with_francis.production import production_config, prepare_database, create_production_app
from learning_with_francis.subjects import SUBJECTS


class FreeDemoTests(unittest.TestCase):
    setUp = production_tests.ProductionTests.setUp
    app = production_tests.ProductionTests.app
    rows = production_tests.ProductionTests.rows
    get = production_tests.ProductionTests.get
    post = production_tests.ProductionTests.post
    start = production_tests.ProductionTests.start

    def test_demo_mode_is_explicit_and_validated_before_storage_creation(self):
        self.assertFalse(production_config(self.env)['DEMO_MODE'])
        self.assertTrue(production_config({**self.env, 'LWF_DEMO_MODE': '1'})['DEMO_MODE'])
        for value in ('true', 'yes', '', '2'):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                prepare_database({**self.env, 'LWF_DEMO_MODE': value})
        self.assertFalse(self.path.exists())

    def test_original_local_factory_does_not_enable_demo_notice(self):
        prepare_database(self.env)
        app = create_app({'TESTING': True, 'DATABASE': str(self.path), 'SECRET_KEY': self.env['LWF_SECRET_KEY']})
        self.assertNotIn('class="demo-notice"', app.test_client().get('/').text)

    def test_notice_appears_before_name_collection_in_both_languages(self):
        self.env['LWF_DEMO_MODE'] = '1'
        client = self.app().test_client()
        before = learning_snapshot(self.path)
        for language, heading in [('en', 'Public learning demonstration'), ('de', 'Öffentliche Lern-Demo')]:
            fields = HiddenFields(self.get(client, '/').text).fields
            response = self.post(client, '/preferences/language', {**fields, 'language': language})
            self.assertEqual(response.status_code, 303)
            for path in ('/', '/learn/'):
                text = self.get(client, path).text
                self.assertIn(heading, text)
                self.assertIn('class="demo-notice"', text)
                if path == '/learn/':
                    self.assertLess(text.index('class="demo-notice"'), text.index('id="visitor-name"'))
        self.assertEqual(learning_snapshot(self.path), before)


    def test_notice_follows_learning_results_progress_and_language_without_data_changes(self):
        self.env['LWF_DEMO_MODE'] = '1'
        client = self.app().test_client()
        self.start(client)
        question = SUBJECTS['sql']['content'].PRACTICE[0]
        fields = HiddenFields(self.get(client, '/sql/practice').text).fields
        result = self.post(client, '/sql/practice', {**fields, question['id']: question['correct']})
        self.assertEqual(result.status_code, 303)
        paths = ['/learn/', '/progress/', result.location]
        paths += [f'/{slug}{suffix}' for slug in SUBJECTS for suffix in ('/', '/practice', '/quiz')]
        before = learning_snapshot(self.path)
        for language, heading in [('de', 'Öffentliche Lern-Demo'), ('en', 'Public learning demonstration')]:
            fields = HiddenFields(self.get(client, '/progress/').text).fields
            self.post(client, '/preferences/language', {**fields, 'language': language})
            for path in paths:
                response = self.get(client, path)
                self.assertEqual(response.status_code, 200, path)
                self.assertIn(heading, response.text, path)
        self.assertEqual(learning_snapshot(self.path), before)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts'), [(1,)])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM topic_progress WHERE learning_status='Completed'"), [(0,)])


    def test_replaced_instance_storage_has_zero_activity_and_old_cookie_cannot_recover_by_name(self):
        self.env['LWF_DEMO_MODE'] = '1'
        first_app = self.app()
        client = first_app.test_client()
        self.start(client)
        fields = HiddenFields(self.get(client, '/sql/quiz').text).fields
        answers = {q['id']: q['correct'] for q in SUBJECTS['sql']['content'].QUIZ}
        result = self.post(client, '/sql/quiz', {**fields, **answers})
        old_result_path = result.location
        cookie_name = first_app.config['SESSION_COOKIE_NAME']
        old_cookie = client.get_cookie(cookie_name).value
        old_id = self.rows('SELECT visit_id FROM visits')[0][0]
        original = learning_snapshot(self.path)
        replacement_env = {**self.env, 'LWF_DATA_DIR': str(self.directory / 'replacement-instance')}
        self.assertTrue(prepare_database(replacement_env))
        replacement = create_production_app(replacement_env)
        fresh = replacement.test_client()
        fresh.set_cookie(cookie_name, old_cookie)
        self.assertEqual(self.get(fresh, '/progress/').status_code, 303)
        self.assertEqual(self.get(fresh, old_result_path).status_code, 303)
        with fresh.session_transaction(base_url='https://localhost') as session:
            self.assertNotIn('visit_id', session)
        old_path = self.path
        self.path = Path(production_config(replacement_env)['DATABASE'])
        for table in ('visits', 'learning_attempts', 'learning_answers', 'topic_progress', 'topic_status_history'):
            self.assertEqual(self.rows('SELECT COUNT(*) FROM ' + table), [(0,)])
        self.start(fresh)
        self.assertNotEqual(self.rows('SELECT visit_id FROM visits')[0][0], old_id)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM topic_progress WHERE learning_status='Still Learning'"), [(4,)])
        self.assertIn('id="no-activity"', self.get(fresh, '/progress/').text)
        self.assertEqual(self.get(fresh, old_result_path).status_code, 404)
        self.assertEqual(learning_snapshot(old_path), original)
        self.assertEqual(self.rows('PRAGMA integrity_check'), [('ok',)])
        self.assertEqual(self.rows('PRAGMA foreign_key_check'), [])



if __name__ == '__main__':
    unittest.main()
