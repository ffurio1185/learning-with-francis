"""Berlin display conversion: UTC storage stays unchanged, including across DST."""

from contextlib import closing
from datetime import datetime, timezone
import unittest

from learning_with_francis import db
from learning_with_francis.display_time import berlin_datetime
from learning_with_francis.subjects import SUBJECTS
from test_phase2_sql import HiddenFields, SQLFlowSupport


class BerlinConversionTests(unittest.TestCase):
    def test_winter_and_summer_use_the_correct_offset(self):
        for stored, expected in (
            ('2026-01-15 12:30:00', '15.01.2026 13:30:00 CET'),
            ('2026-07-15 12:30:00', '15.07.2026 14:30:00 CEST'),
            ('2026-10-22 00:29:38', '22.10.2026 02:29:38 CEST'),
        ):
            with self.subTest(stored=stored):
                self.assertEqual(berlin_datetime(stored).strftime('%d.%m.%Y %H:%M:%S %Z'), expected)

    def test_spring_transition_skips_the_nonexistent_local_hour(self):
        self.assertEqual(berlin_datetime('2026-03-29 00:59:59').isoformat(), '2026-03-29T01:59:59+01:00')
        self.assertEqual(berlin_datetime('2026-03-29 01:00:00').isoformat(), '2026-03-29T03:00:00+02:00')

    def test_autumn_repeated_hour_keeps_distinct_offsets(self):
        before = berlin_datetime('2026-10-25 00:30:00')
        after = berlin_datetime('2026-10-25 01:30:00')
        self.assertEqual(before.isoformat(), '2026-10-25T02:30:00+02:00')
        self.assertEqual(after.isoformat(), '2026-10-25T02:30:00+01:00')
        self.assertEqual((before.tzname(), after.tzname()), ('CEST', 'CET'))

    def test_midnight_and_year_rollover_show_the_local_date(self):
        self.assertEqual(berlin_datetime('2026-12-31 23:30:00').isoformat(), '2027-01-01T00:30:00+01:00')
        self.assertEqual(berlin_datetime('2026-07-01 22:30:00').isoformat(), '2026-07-02T00:30:00+02:00')

    def test_explicit_offsets_are_not_interpreted_as_naive_utc(self):
        self.assertEqual(berlin_datetime('2026-07-15T14:30:00+02:00').isoformat(), '2026-07-15T14:30:00+02:00')
        self.assertEqual(berlin_datetime('2026-07-15T12:30:00Z').isoformat(), '2026-07-15T14:30:00+02:00')


class BerlinPageTests(SQLFlowSupport, unittest.TestCase):
    def test_existing_utc_activity_and_status_records_render_locally_without_writes(self):
        result = self.submit(5)
        owner = self.rows('SELECT visit_id FROM visits')[0][0]
        with closing(db.open_database(self.path)) as connection:
            connection.execute("UPDATE visits SET started_at='2026-01-15 12:30:00'")
            connection.execute("UPDATE learning_attempts SET submitted_at='2026-10-22 00:29:38'")
            connection.execute("UPDATE topic_progress SET learning_status='Completed', understanding_confirmed_at='2026-07-15 12:30:00' WHERE visit_id=? AND topic_id='sql-select-basics'", (owner,))
            connection.execute("""INSERT INTO topic_status_history
                (visit_id,topic_id,previous_status,new_status,changed_at,user_confirmed)
                VALUES (?,'sql-select-basics','Still Learning','Completed','2026-07-15 12:30:00',1)""", (owner,))
            connection.commit()
        before = self.path.read_bytes()
        home = self.client.get('/learn/').get_data(as_text=True)
        progress = self.client.get('/progress/').get_data(as_text=True)
        lesson = self.client.get('/sql/').get_data(as_text=True)
        saved_result = self.client.get(result.location).get_data(as_text=True)
        for html in (home, progress):
            self.assertIn('15.01.2026 13:30:00 CET', html)
        for html in (progress, lesson, saved_result):
            self.assertIn('22.10.2026 02:29:38 CEST', html)
            self.assertIn('datetime="2026-10-22T02:29:38+02:00"', html)
            self.assertNotIn('Date (UTC)', html)
        self.assertEqual(progress.count('15.07.2026 14:30:00 CEST'), 2)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.rows('SELECT submitted_at FROM learning_attempts'), [('2026-10-22 00:29:38',)])

    def test_shared_result_and_subject_lesson_show_practice_in_local_time(self):
        # A real submitted practice attempt, then an old UTC fixture date in this disposable DB.
        data = HiddenFields(self.client.get('/python/practice').get_data(as_text=True)).fields
        question = SUBJECTS['python']['content'].PRACTICE[0]
        data[question['id']] = question['correct']
        result = self.client.post('/python/practice', data=data)
        with closing(db.open_database(self.path)) as connection:
            connection.execute("UPDATE learning_attempts SET submitted_at='2026-12-31 23:30:00'")
            connection.commit()
        attempt_id = result.location.rsplit('/', 1)[1]
        before = self.path.read_bytes()
        for path in ('/python/', f'/python/results/{attempt_id}', '/progress/'):
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn('01.01.2027 00:30:00 CET', html)
            self.assertIn('datetime="2027-01-01T00:30:00+01:00"', html)
        self.assertEqual(self.path.read_bytes(), before)

    def test_newly_submitted_activity_is_stored_in_utc_and_displayed_in_berlin(self):
        before = datetime.now(timezone.utc)
        result = self.submit(5)
        after = datetime.now(timezone.utc)
        stored = self.rows('SELECT submitted_at FROM learning_attempts')[0][0]
        instant = datetime.fromisoformat(stored).replace(tzinfo=timezone.utc)
        self.assertGreaterEqual(instant.timestamp(), before.timestamp() - 1)
        self.assertLessEqual(instant.timestamp(), after.timestamp())
        expected = berlin_datetime(stored).strftime('%d.%m.%Y %H:%M:%S %Z')
        self.assertIn(expected, self.client.get(result.location).get_data(as_text=True))
        self.assertIn(expected, self.client.get('/progress/').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
