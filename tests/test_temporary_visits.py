"""Temporary retention: only disposable databases, with a controlled server clock."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from learning_with_francis import create_app, db, visitors
from learning_with_francis.production import production_config
from learning_with_francis.subjects import SUBJECTS
from test_phase2_sql import HiddenFields, SQLFlowSupport
from retention_support import learning_snapshot


class TemporaryVisitTests(SQLFlowSupport, unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        clock = patch.object(visitors, 'utc_now', side_effect=lambda: self.now)
        clock.start(); self.addCleanup(clock.stop)
        super().setUp()

    def owner(self, client=None):
        with (client or self.client).session_transaction() as session:
            return session.get('visit_id')

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)

    def activity_at(self, owner=None):
        return self.rows('SELECT last_activity_at FROM visits WHERE visit_id=?', (owner or self.owner(),))

    def csrf(self, client=None):
        client = client or self.client
        with client.session_transaction() as session:
            return session['csrf_token']

    def populate(self, client=None):
        client = client or self.client
        results = []
        for slug, subject in SUBJECTS.items():
            for kind in ('practice', 'quiz'):
                fields = HiddenFields(client.get(f'/{slug}/{kind}').text).fields
                questions = subject['content'].QUIZ if kind == 'quiz' else (subject['content'].PRACTICE[0],)
                data = {**fields, **{q['id']: q['correct'] for q in questions}}
                response = client.post(f'/{slug}/{kind}', data=data)
                self.assertEqual(response.status_code, 303)
                results.append((response.location, f'/{slug}/{kind}', data))
            fields = HiddenFields(client.get('/progress/').text).fields
            topic = subject['content'].TOPIC_ID
            self.assertEqual(client.post(f'/progress/{topic}/status', data={**fields,
                'new_status': 'Completed', 'user_confirmed': 'yes'}).status_code, 303)
        return results

    def assert_removed(self, owner):
        for table in ('visits', 'topic_progress', 'topic_status_history', 'learning_attempts'):
            self.assertEqual(self.rows(f'SELECT COUNT(*) FROM {table} WHERE visit_id=?', (owner,)), [(0,)], table)
        self.assertEqual(self.rows('PRAGMA foreign_key_check'), [])
        self.assertEqual(self.rows('PRAGMA integrity_check'), [('ok',)])

    def test_end_deletes_all_four_subjects_answers_scores_confirmation_history(self):
        self.populate(); owner = self.owner()
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_answers'), [(24,)])
        self.assertEqual(self.client.post('/visits/end', data={'csrf_token': self.csrf()}).status_code, 303)
        self.assert_removed(owner)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_answers'), [(0,)])
        self.assertIsNone(self.owner())
        self.assertEqual(self.rows('SELECT COUNT(*) FROM subjects'), [(4,)])
        self.assertEqual(self.rows('SELECT COUNT(*) FROM topics'), [(4,)])

    def test_new_visit_deletes_previous_before_name_entry_and_starts_zero(self):
        self.populate(); owner = self.owner()
        self.assertEqual(self.client.post('/visits/new', data={'csrf_token': self.csrf()}).status_code, 303)
        self.assert_removed(owner)
        self.start(self.client)
        self.assertNotEqual(self.owner(), owner)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_answers'), [(0,)])
        self.assertEqual(self.rows('SELECT learning_status FROM topic_progress'), [('Still Learning',)] * 4)

    def test_direct_start_replacement_is_atomic_and_deletes_previous(self):
        self.populate(); owner = self.owner()
        self.start(self.client)
        self.assert_removed(owner)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM visits'), [(1,)])
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts'), [(0,)])

    def test_same_name_other_visitor_survives_end_and_cleanup_exactly(self):
        other = self.app.test_client(); self.start(other)
        self.populate(); self.populate(other)
        other_id = self.owner(other)
        with closing(db.open_database(self.path)) as conn:
            tables = ('visits', 'topic_progress', 'topic_status_history', 'learning_attempts')
            before = {t: [tuple(row) for row in conn.execute(f'SELECT * FROM {t} WHERE visit_id=?', (other_id,))] for t in tables}
            answers = [tuple(row) for row in conn.execute('SELECT * FROM learning_answers WHERE attempt_id IN (SELECT attempt_id FROM learning_attempts WHERE visit_id=?)', (other_id,))]
        self.client.post('/visits/end', data={'csrf_token': self.csrf()})
        for t in tables:
            self.assertEqual(self.rows(f'SELECT * FROM {t} WHERE visit_id=?', (other_id,)), before[t])
        self.assertEqual(sorted(self.rows('SELECT * FROM learning_answers')), sorted(answers))
        self.assertEqual(other.get('/progress/').status_code, 200)

    def test_end_rollback_keeps_entire_visit_and_cookie_when_any_delete_fails(self):
        self.populate(); owner = self.owner(); before = learning_snapshot(self.path)
        with closing(db.open_database(self.path)) as conn:
            conn.execute("CREATE TRIGGER fail_visit_delete BEFORE DELETE ON visits BEGIN SELECT RAISE(ABORT,'test rollback'); END")
        before = learning_snapshot(self.path)
        with self.assertRaises(sqlite3.IntegrityError):
            self.client.post('/visits/end', data={'csrf_token': self.csrf()})
        self.assertEqual(learning_snapshot(self.path), before)
        self.assertEqual(self.owner(), owner)

    def test_replacement_rollback_restores_old_answers_and_progress(self):
        self.populate(); owner = self.owner()
        with closing(db.open_database(self.path)) as conn:
            conn.execute("CREATE TRIGGER fail_new_visit BEFORE INSERT ON visits BEGIN SELECT RAISE(ABORT,'test rollback'); END")
        before = learning_snapshot(self.path)
        with self.assertRaises(sqlite3.IntegrityError): self.start(self.client)
        self.assertEqual(learning_snapshot(self.path), before)
        self.assertEqual(self.owner(), owner)

    def test_cleanup_rollback_restores_all_expired_data(self):
        self.populate(); owner = self.owner(); self.advance(1800)
        with closing(db.open_database(self.path)) as conn:
            conn.execute("CREATE TRIGGER fail_cleanup BEFORE DELETE ON visits BEGIN SELECT RAISE(ABORT,'test rollback'); END")
        before = learning_snapshot(self.path)
        with self.app.app_context():
            with self.assertRaises(sqlite3.IntegrityError): visitors.cleanup_expired_visits()
        self.assertEqual(learning_snapshot(self.path), before)

    def test_exact_30_minute_boundary_expires_before_timestamp_can_be_renewed(self):
        self.populate(); owner = self.owner(); self.advance(1800)
        response = self.client.get('/progress/')
        self.assertEqual(response.status_code, 303)
        self.assert_removed(owner)
        self.assertIsNone(self.owner())
        self.assertIn('visit expired or ended', self.client.get('/learn/').text)

    def test_request_at_29_minutes_59_seconds_renews(self):
        owner = self.owner(); self.advance(1799)
        self.assertEqual(self.client.get('/sql/').status_code, 200)
        self.assertEqual(self.activity_at(owner), [(self.now.strftime('%Y-%m-%d %H:%M:%S'),)])
        self.advance(1799)
        self.assertEqual(self.client.get('/progress/').status_code, 200)
        self.assertEqual(self.owner(), owner)

    def test_active_learning_can_continue_longer_than_30_minutes_and_12_hours(self):
        owner = self.owner()
        # The 12-hour signed-cookie age window is renewed on successful requests.
        for _ in range(40):
            self.advance(1200)
            self.assertEqual(self.client.get('/sql/quiz').status_code, 200)
        self.assertEqual(self.owner(), owner)
        self.assertGreater((self.now - datetime.strptime(self.rows('SELECT started_at FROM visits')[0][0], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)).total_seconds(), 12*3600)
        self.assertIn('Set-Cookie', self.client.get('/progress/').headers)

    def test_signature_age_remains_sliding_during_13_hours_of_active_learning(self):
        import time
        real_epoch = time.time()
        for hour in range(1, 27):
            self.advance(1200)
            with patch('itsdangerous.timed.time.time', return_value=real_epoch + hour * 1200):
                self.assertEqual(self.client.get('/progress/').status_code, 200)
                self.assertIn('Set-Cookie', self.client.get('/progress/').headers)
        # More than 12 actual signing-clock hours, reached in sub-30-minute steps.
        for interval in range(27, 40):
            self.advance(1200)
            with patch('itsdangerous.timed.time.time', return_value=real_epoch + interval * 1200):
                self.assertEqual(self.client.get('/sql/quiz').status_code, 200)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM visits'), [(1,)])

    def test_activity_timestamp_never_moves_backwards(self):
        self.advance(60)
        self.client.get('/sql/')
        last = self.activity_at()
        self.advance(-30)
        self.client.get('/progress/')
        self.assertEqual(self.activity_at(), last)

    def test_all_subject_lesson_practice_quiz_and_progress_gets_renew(self):
        for slug in SUBJECTS:
            for path in (f'/{slug}/', f'/{slug}/practice', f'/{slug}/quiz', '/progress/', '/learn/'):
                self.advance(60);self.assertEqual(self.client.get(path).status_code, 200)
                self.assertEqual(self.activity_at(), [(self.now.strftime('%Y-%m-%d %H:%M:%S'),)])

    def test_successful_answer_and_status_posts_renew_without_automatic_completion(self):
        data = self.payload(); self.advance(60)
        self.assertEqual(self.client.post('/sql/quiz', data=data).status_code, 303)
        self.assertEqual(self.activity_at(), [(self.now.strftime('%Y-%m-%d %H:%M:%S'),)])
        self.assertEqual(self.rows('SELECT DISTINCT learning_status FROM topic_progress'), [('Still Learning',)])
        self.advance(60)
        self.assertEqual(self.client.post('/progress/sql-select-basics/status', data={
            'csrf_token': self.csrf(), 'new_status': 'Needs Review'}).status_code, 303)
        self.assertEqual(self.activity_at(), [(self.now.strftime('%Y-%m-%d %H:%M:%S'),)])

    def test_cover_privacy_language_assets_and_health_do_not_renew(self):
        before = self.activity_at();self.advance(1799)
        for path in ('/', '/privacy/', '/static/cover.js', '/healthz'):
            with self.client.get(path):
                pass
        fields = HiddenFields(self.client.get('/privacy/').text).fields
        self.assertEqual(self.client.post('/preferences/language', data={**fields, 'language':'de'}).status_code, 303)
        self.assertEqual(self.activity_at(), before)
        self.advance(1)
        self.assertEqual(self.client.get('/sql/').status_code, 303)
        self.assertIn('Dein Besuch ist abgelaufen', self.client.get('/learn/').text)

    def test_invalid_answers_csrf_confirmation_foreign_result_and_unknown_route_do_not_renew(self):
        self.client.get('/sql/quiz');before=self.activity_at();self.advance(60)
        for path, data in (('/sql/quiz', {}), ('/progress/sql-select-basics/status', {'csrf_token':self.csrf(), 'new_status':'Completed'}), ('/visits/end', {'csrf_token':'forged'}), ('/visits/start', {'csrf_token':self.csrf(), 'visitor_name':'   '})):
            self.assertEqual(self.client.post(path, data=data).status_code, 400)
        self.assertEqual(self.client.get('/sql/results/unknown').status_code, 404)
        self.assertEqual(self.client.get('/unknown/').status_code, 404)
        self.assertEqual(self.activity_at(), before)

    def test_expired_cookie_saved_result_back_url_and_duplicate_post_cannot_restore(self):
        result = self.submit();data=self.payload();owner=self.owner()
        name=self.app.config['SESSION_COOKIE_NAME'];cookie=self.client.get_cookie(name).value
        self.advance(1800)
        for path, method, payload in ((result.location,'get',None),('/sql/quiz','post',data),('/progress/sql-select-basics/status','post',{'new_status':'Completed','user_confirmed':'yes','csrf_token':self.csrf()})):
            replay=self.app.test_client();replay.set_cookie(name,cookie)
            response=getattr(replay,method)(path, **({'data':payload} if payload else {}))
            self.assertEqual(response.status_code, 303)
            self.assertIsNone(self.owner(replay))
        self.assert_removed(owner)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_answers'), [(0,)])

    def test_expiry_discards_drafts_tokens_but_preserves_selected_language(self):
        with self.client.session_transaction() as session:
            session['language']='de';session['language_draft']={'secret':'old answer'}
        self.advance(1800);self.client.get('/learn/')
        with self.client.session_transaction() as session:
            self.assertEqual(session['language'],'de')
            self.assertNotIn('visit_id',session)
            self.assertNotIn('language_draft',session)
        self.assertIn('Dein Name',self.client.get('/learn/').text)

    def test_cleanup_from_other_request_removes_only_expired_visitor(self):
        owner=self.owner();self.advance(1700)
        other=self.app.test_client();self.start(other)
        other_id=self.owner(other);self.advance(100)
        self.assertEqual(other.get('/progress/').status_code,200)
        self.assert_removed(owner)
        self.assertEqual(self.owner(other),other_id)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM topic_progress'), [(4,)])

    def test_restart_cleans_inactive_data_but_keeps_active_data(self):
        owner=self.owner();self.advance(1700)
        other=self.app.test_client();self.start(other);other_id=self.owner(other)
        self.advance(100); restarted=create_app(self.config)
        self.assert_removed(owner)
        with restarted.app_context():self.assertIsNotNone(visitors.active_visit(other_id))

    def test_sleep_does_not_promise_timed_deletion_then_next_request_cleans(self):
        owner=self.owner();self.advance(8*3600)
        # No process/request has run cleanup: merely passing time does not run Python.
        self.assertEqual(self.rows('SELECT COUNT(*) FROM visits'),[(1,)])
        self.client.get('/')  # Cover is independent; does not count as learning activity.
        self.assertEqual(self.rows('SELECT COUNT(*) FROM visits'),[(1,)])
        self.client.get('/learn/');self.assert_removed(owner)

    def test_end_and_expiry_do_not_delete_shared_curriculum(self):
        before=(self.rows('SELECT * FROM subjects'),self.rows('SELECT * FROM topics'))
        self.client.get('/learn/')
        self.client.post('/visits/end',data={'csrf_token':self.csrf()})
        self.start(self.client);self.advance(1800);self.client.get('/learn/')
        self.assertEqual((self.rows('SELECT * FROM subjects'),self.rows('SELECT * FROM topics')),before)

    def test_write_transaction_rechecks_inactivity_and_cannot_save_late_answers(self):
        data=self.payload();owner=self.owner()
        original=visitors.active_visit
        def expire_inside_write(visit_id):
            if db.get_db().in_transaction:self.advance(1800)
            return original(visit_id)
        with patch.object(visitors,'active_visit',side_effect=expire_inside_write):
            self.assertEqual(self.client.post('/sql/quiz',data=data).status_code,403)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts'),[(0,)])
        self.client.get('/learn/');self.assert_removed(owner)

    def test_configurable_timeout_and_bad_configuration_rejected(self):
        for value in (0,-1,True,'1800'):
            with self.assertRaises(ValueError):create_app({**self.config,'VISIT_IDLE_SECONDS':value})
        short=create_app({**self.config,'VISIT_IDLE_SECONDS':60}).test_client()
        name=self.app.config['SESSION_COOKIE_NAME'];short.set_cookie(name,self.client.get_cookie(name).value)
        self.advance(60);self.assertEqual(short.get('/progress/').status_code,303)
        env={'LWF_SECRET_KEY':'x'*40,'LWF_DATA_DIR':str(self.root/'runtime'),'LWF_ALLOWED_HOSTS':'localhost'}
        self.assertEqual(production_config(env)['VISIT_IDLE_SECONDS'],1800)
        self.assertEqual(production_config({**env,'LWF_VISIT_IDLE_SECONDS':'60'})['VISIT_IDLE_SECONDS'],60)
        for value in ('0','-1','nan','1.5','9'*5000):
            with self.assertRaises((RuntimeError,ValueError)):production_config({**env,'LWF_VISIT_IDLE_SECONDS':value})

    def test_secure_delete_and_foreign_keys_enabled(self):
        with closing(db.open_database(self.path)) as conn:
            self.assertEqual(conn.execute('PRAGMA secure_delete').fetchone()[0],1)
            self.assertEqual(conn.execute('PRAGMA foreign_keys').fetchone()[0],1)

    def test_schema3_is_not_silently_upgraded_or_cleaned(self):
        old=self.root/'old-schema3.db'
        with closing(sqlite3.connect(old)) as conn:
            for file in (db.SCHEMA_PATH,db.MIGRATION_PATH,db.ACTIVITY_MIGRATION_PATH):conn.executescript(file.read_text())
        before=old.read_bytes()
        with self.assertRaises(db.DatabaseSetupError):db.initialize_database(old)
        create_app({**self.config,'DATABASE':str(old)})
        self.assertEqual(old.read_bytes(),before)

    def test_explicit_disposable_schema3_upgrade_preserves_existing_fields(self):
        old=self.root/'disposable-upgrade.db'
        with closing(sqlite3.connect(old)) as conn:
            for file in (db.SCHEMA_PATH,db.MIGRATION_PATH,db.ACTIVITY_MIGRATION_PATH):conn.executescript(file.read_text())
            conn.execute("INSERT INTO visits(visit_id,display_name) VALUES ('disposable','Learner')");conn.commit()
            before=conn.execute('SELECT * FROM visits').fetchall()
        backup=db.upgrade_database(old)
        self.assertTrue(backup.is_file())
        with closing(db.open_database(old)) as conn:
            self.assertEqual([tuple(row)[:4] for row in conn.execute('SELECT * FROM visits')],before)
            self.assertEqual(conn.execute('SELECT started_at=last_activity_at FROM visits').fetchone()[0],1)


if __name__=='__main__':unittest.main()
