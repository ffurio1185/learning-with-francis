"""L4 localization flows: disposable current-schema, canonical records, private visits."""
from contextlib import closing
from html import unescape
from retention_support import learning_snapshot

import json
import re
import unittest

from flask import session
from werkzeug.datastructures import MultiDict
from learning_with_francis import create_app, db, sql_display
from learning_with_francis.subjects import SUBJECTS
from test_interface_language import CheckedAnswers
from test_phase2_sql import HiddenFields, SQLFlowSupport
from test_sql_language import CodeBlocks

SLUGS = ('python', 'javascript', 'sap')
TITLES = {'python': 'Variablen und einfache Funktionen',
          'javascript': 'Werte, DOM-Elemente und Ereignisse',
          'sap': 'ERP-Grundlagen und Geschäftsprozessbeispiele'}


class SubjectLanguageTests(SQLFlowSupport, unittest.TestCase):
    def fields_at(self, path, client=None):
        return HiddenFields((client or self.client).get(path).text).fields

    def switch(self, language='de', path='/learn/', client=None, **draft):
        client = client or self.client
        fields = self.fields_at(path, client)
        return client.post('/preferences/language', data={**fields, **draft, 'language': language})

    def quiz_data(self, slug, score=5, client=None):
        data = self.fields_at(f'/{slug}/quiz', client)
        for index, q in enumerate(SUBJECTS[slug]['content'].QUIZ):
            data[q['id']] = q['correct'] if index < score else next(k for k in q['choices'] if k != q['correct'])
        return data

    def quiz_result(self, slug, score=5, client=None):
        client = client or self.client
        response = client.post(f'/{slug}/quiz', data=self.quiz_data(slug, score, client))
        self.assertEqual(response.status_code, 303)
        return response.location

    def test_lessons_both_languages_keep_exact_code_and_do_not_write_metadata(self):
        english = {s: self.client.get(f'/{s}/').text for s in SLUGS}
        before = learning_snapshot(self.path); self.switch()
        for slug in SLUGS:
            with self.subTest(subject=slug):
                german = self.client.get(f'/{slug}/').text
                self.assertIn(f'{SUBJECTS[slug]["name"]}: {TITLES[slug]}', german)
                self.assertIn('class="lesson-material" lang="de"', german)
                self.assertNotIn('interface-scope', german)
                self.assertEqual(CodeBlocks(english[slug]).blocks, CodeBlocks(german).blocks)
                self.assertIn(SUBJECTS[slug]['title'], english[slug])
                for path in ('/learn/', '/progress/'):
                    self.assertIn(TITLES[slug], self.client.get(path).text)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_all_forty_five_questions_translate_without_leaking_explanations_or_keys(self):
        self.switch()
        for slug in SLUGS:
            content = SUBJECTS[slug]['content']
            with self.app.test_request_context('/'):
                session['language'] = 'de'
                for kind in ('practice', 'quiz'):
                    public = sql_display.public_questions(content, kind)
                    for source, shown in zip(content.questions_for(kind), public):
                        self.assertEqual(set(shown), {'id', 'prompt', 'choices'})
                        self.assertEqual(shown['id'], source['id'])
                        self.assertNotEqual(shown['prompt'], source['prompt'])
                        self.assertEqual(set(shown['choices']), set(source['choices']))
                        self.assertEqual(len(set(shown['choices'].values())), 3)
                        self.assertNotEqual(sql_display.gettext(source['explanation']), source['explanation'])
            for kind in ('practice', 'quiz'):
                html = unescape(self.client.get(f'/{slug}/{kind}').text)
                self.assertNotIn('correct_option', html)
                with self.app.test_request_context('/'):
                    session['language'] = 'de'
                    for q in content.questions_for(kind):
                        self.assertNotIn(sql_display.gettext(q['explanation']), html)

    def test_all_six_quiz_scores_each_subject_localize_feedback_and_save_canonical_answers(self):
        self.switch()
        for slug in SLUGS:
            content = SUBJECTS[slug]['content']
            for score in range(6):
                with self.subTest(subject=slug, score=score):
                    url = self.quiz_result(slug, score)
                    html = self.client.get(url).text
                    self.assertIn(f'{score} von 5', html)
                    self.assertIn('Übe weiter' if score <= 2 else 'Quiz bestanden' if score < 5 else 'Volle Punktzahl', html)
                    self.assertIn('Francis!', html)
                    self.assertEqual(html.count('class="answer-result correct-answer"'), score)
                    answers = self.rows('SELECT question_id,prompt,correct_option,explanation FROM learning_answers WHERE attempt_id=? ORDER BY position', (url.rsplit('/', 1)[1],))
                    self.assertEqual(answers, [(q['id'], q['prompt'], q['correct'], q['explanation']) for q in content.QUIZ])
            self.assertEqual(self.rows('SELECT score FROM learning_attempts WHERE topic_id=? ORDER BY rowid', (content.TOPIC_ID,)), [(i,) for i in range(6)])
        self.assertEqual(self.rows('SELECT DISTINCT learning_status FROM topic_progress'), [('Still Learning',)])

    def test_all_thirty_practice_questions_feedback_round_switch_finish_restart_and_totals(self):
        self.switch()
        for slug in SLUGS:
            path = f'/{slug}/practice'
            for index, q in enumerate(SUBJECTS[slug]['content'].PRACTICE):
                html = self.client.get(path).text
                fields = HiddenFields(html).fields
                self.assertIn(f'Frage {index + 1} von 10', html)
                choice = q['correct'] if index % 2 == 0 else next(k for k in q['choices'] if k != q['correct'])
                if index == 3:
                    before = learning_snapshot(self.path)
                    response = self.client.post('/preferences/language', data={**fields, q['id']: choice, 'language': 'en'})
                    html = self.client.get(response.location).text
                    self.assertEqual(CheckedAnswers(html).answers, {q['id']: choice})
                    self.assertEqual(HiddenFields(html).fields['position'], '3')
                    response = self.client.post('/preferences/language', data={**HiddenFields(html).fields, q['id']: choice, 'language': 'de'})
                    fields = HiddenFields(self.client.get(response.location).text).fields
                    self.assertEqual(learning_snapshot(self.path), before)
                response = self.client.post(f'/{slug}/practice', data={**fields, q['id']: choice})
                self.assertEqual(response.status_code, 303)
                html = unescape(self.client.get(response.location).text)
                self.assertIn('richtig gelöst' if index % 2 == 0 else 'Lies die Erklärung', html)
                self.assertIn('Richtige Antwort:', html)
                self.assertNotIn(q['explanation'], html)
                before = learning_snapshot(self.path); self.client.get(response.location)
                self.assertEqual(learning_snapshot(self.path), before)
                path = unescape(re.search(r'id="practice-next" href="([^"]+)"', html)[1])
            self.assertIn('Übungsrunde abgeschlossen!', self.client.get(path).text)
            self.assertIn('Frage 1 von 10', self.client.get(f'/{slug}/practice').text)
            self.assertEqual(self.rows('SELECT COUNT(*),SUM(score) FROM learning_attempts WHERE topic_id=?', (SUBJECTS[slug]['content'].TOPIC_ID,)), [(10, 5)])
        self.assertEqual(self.rows('SELECT DISTINCT learning_status FROM topic_progress'), [('Still Learning',)])


    def test_quiz_drafts_keep_original_identity_answers_and_database_unchanged_both_ways(self):
        for slug in SLUGS:
            data = self.quiz_data(slug, 3); before = learning_snapshot(self.path)
            for language in ('de', 'en', 'de'):
                response = self.client.post('/preferences/language', data={**data, 'language': language})
                html = self.client.get(response.location).text
                self.assertEqual(CheckedAnswers(html).answers, {q['id']: data[q['id']] for q in SUBJECTS[slug]['content'].QUIZ})
                fields = HiddenFields(html).fields
                self.assertEqual(fields['submission_token'], data['submission_token'])
                data.update(fields)
            self.assertEqual(learning_snapshot(self.path), before)


    def test_existing_english_results_switch_to_german_and_back_read_only(self):
        for slug in SLUGS:
            self.switch('en'); url = self.quiz_result(slug, 4)
            english = self.client.get(url).text; before = learning_snapshot(self.path)
            self.switch(path=url)
            german = self.client.get(url).text
            self.assertIn('Quiz bestanden', german)
            self.assertNotIn(SUBJECTS[slug]['content'].QUIZ[0]['prompt'], unescape(german))
            self.switch('en', path=url)
            self.assertEqual(self.client.get(url).text.count('class="answer-result correct-answer"'), 4)
            self.assertIn(SUBJECTS[slug]['content'].QUIZ[0]['prompt'], unescape(english))
            self.assertEqual(learning_snapshot(self.path), before)


    def test_cross_language_duplicates_are_idempotent_and_changed_answers_rejected(self):
        for slug in SLUGS:
            data = self.quiz_data(slug); response = self.client.post(f'/{slug}/quiz', data=data)
            self.switch(path=response.location); before = learning_snapshot(self.path)
            duplicate = self.client.post(f'/{slug}/quiz', data=data)
            self.assertEqual(duplicate.location, response.location)
            data['q1'] = next(k for k in SUBJECTS[slug]['content'].QUIZ[0]['choices'] if k != data['q1'])
            self.assertEqual(self.client.post(f'/{slug}/quiz', data=data).status_code, 409)
            self.assertEqual(learning_snapshot(self.path), before)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts'), [(3,)])


    def test_unknown_saved_wording_keeps_original_english_without_rewriting_records(self):
        for slug in SLUGS:
            url = self.quiz_result(slug)
            with closing(db.open_database(self.path)) as connection:
                connection.execute('UPDATE learning_answers SET prompt=? WHERE attempt_id=? AND question_id=?', ('Earlier lesson wording', url.rsplit('/', 1)[1], 'q1'))
                connection.commit()
            self.switch(path=url); before = learning_snapshot(self.path)
            html = self.client.get(url).text
            self.assertIn('Earlier lesson wording', html)
            self.assertIn('frühere Formulierung', html)
            self.assertIn('<h2 lang="en">Earlier lesson wording', html)
            self.assertEqual(learning_snapshot(self.path), before)


    def test_subject_scoped_lookup_does_not_confuse_reused_question_ids(self):
        self.switch()
        for slug in SLUGS:
            content = SUBJECTS[slug]['content']; q = content.QUIZ[0]
            row = {'question_id': q['id'], 'prompt': q['prompt'], 'choices': q['choices'], 'explanation': q['explanation']}
            with self.app.test_request_context('/'):
                session['language'] = 'de'
                self.assertEqual(sql_display.saved_answers([row], content)[0]['language'], 'de')
                for other in SUBJECTS:
                    if other != slug:
                        view = sql_display.saved_answers([row], SUBJECTS[other]['content'])[0]
                        self.assertEqual(view['prompt'], q['prompt'])
                        self.assertTrue(view['translation_fallback'])
            url = self.quiz_result(slug)
            for other in SLUGS:
                if other != slug:
                    self.assertEqual(self.client.get(url.replace(f'/{slug}/', f'/{other}/')).status_code, 404)

    def test_same_name_visitors_have_private_results_and_independent_languages(self):
        other = self.app.test_client(); self.start(other); self.switch()
        for slug in SLUGS:
            url = self.quiz_result(slug)
            self.assertEqual(other.get(url).status_code, 404)
            self.assertIn(SUBJECTS[slug]['content'].QUIZ[0]['prompt'], unescape(other.get(f'/{slug}/quiz').text))
        self.assertIn('id="total-quizzes">0', other.get('/progress/').text)
        self.assertIn('<html lang="en">', other.get('/learn/').text)
        self.assertEqual(self.rows('SELECT COUNT(DISTINCT visit_id) FROM learning_attempts'), [(1,)])

    def test_untrusted_saved_names_are_escaped_in_all_personalized_feedback(self):
        with closing(db.open_database(self.path)) as connection:
            connection.execute('UPDATE visits SET display_name=?', ('<img src=x onerror=alert(1)>',)); connection.commit()
        self.switch()
        for slug in SLUGS:
            html = self.client.get(self.quiz_result(slug)).text
            self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)
            self.assertNotIn('<img src=x', html)
            self.assertIn('Herzlichen Glückwunsch', html)

    def test_invalid_answers_tokens_and_forged_scores_never_bypass_python_grading(self):
        self.switch()
        for slug in SLUGS:
            data = self.quiz_data(slug, 0); before = learning_snapshot(self.path)
            for invalid in (MultiDict({**data, 'q1': ['a', 'b']}), {**data, 'q1': 'foreign'}, {**data, 'csrf_token': 'forged'}):
                self.assertEqual(self.client.post(f'/{slug}/quiz', data=invalid).status_code, 400)
                self.assertEqual(learning_snapshot(self.path), before)
            data.update(score='5', total_questions='1', visit_id='foreign')
            response = self.client.post(f'/{slug}/quiz', data=data)
            self.assertEqual(response.status_code, 303)
        self.assertEqual(self.rows('SELECT score,total_questions FROM learning_attempts'), [(0, 5)] * 3)


    def test_personal_completion_required_for_each_subject_and_reversible_across_languages(self):
        self.switch()
        for slug in SLUGS:
            topic = SUBJECTS[slug]['content'].TOPIC_ID
            fields = self.fields_at('/progress/'); before = learning_snapshot(self.path)
            for confirmation in ('', 'true', '1'):
                response = self.client.post(f'/progress/{topic}/status', data={**fields, 'new_status': 'Completed', 'user_confirmed': confirmation})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(learning_snapshot(self.path), before)
            self.assertEqual(self.client.post(f'/progress/{topic}/status', data={**fields, 'new_status': 'Completed', 'user_confirmed': 'yes'}).status_code, 303)
            self.switch('en'); fields = self.fields_at('/progress/')
            self.assertEqual(self.client.post(f'/progress/{topic}/status', data={**fields, 'new_status': 'Needs Review'}).status_code, 303)
            self.assertEqual(self.rows('SELECT learning_status,understanding_confirmed_at FROM topic_progress WHERE topic_id=?', (topic,)), [('Needs Review', None)])
            self.switch()


    def test_language_preference_and_saved_results_survive_application_restart(self):
        self.switch(); urls = [self.quiz_result(s) for s in SLUGS]; before = learning_snapshot(self.path)
        name = self.app.config['SESSION_COOKIE_NAME']; cookie = self.client.get_cookie(name).value
        restarted = create_app(self.config).test_client(); restarted.set_cookie(name, cookie)
        for url in urls:
            self.assertIn('Volle Punktzahl', restarted.get(url).text)
        self.assertIn('id="total-quizzes">3', restarted.get('/progress/').text)
        self.assertEqual(learning_snapshot(self.path), before)


    def test_new_and_ended_visits_clear_drafts_keep_language_and_delete_previous_results(self):
        self.switch(); urls = [self.quiz_result(s) for s in SLUGS]
        fields = self.fields_at('/learn/')
        self.assertEqual(self.client.post('/visits/new', data=fields).status_code, 303)
        self.start(self.client)
        self.assertIn('id="total-quizzes">0', self.client.get('/progress/').text)
        self.assertIn('<html lang="de">', self.client.get('/learn/').text)
        for url in urls: self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts'), [(0,)])
        fields = self.fields_at('/learn/')
        self.assertEqual(self.client.post('/visits/end', data=fields).status_code, 303)
        with self.client.session_transaction() as saved:
            self.assertNotIn('visit_id', saved)
            self.assertNotIn('language_draft', saved)
            self.assertEqual(saved['language'], 'de')

    def test_technical_choices_keep_exact_syntax_in_both_languages(self):
        code_choices = {
            'python': ('def add_one(value):\n    return value + 1', 'add_one(6)', "'Hello'", 'False'),
            'javascript': ("document.querySelector('#greeting')", "message.textContent = 'Ready';", 'true', 'textContent'),
        }
        for language in ('en', 'de'):
            with self.app.test_request_context('/'):
                session['language'] = language
                for slug, literals in code_choices.items():
                    content = SUBJECTS[slug]['content']
                    choices = [value for kind in ('practice', 'quiz') for q in sql_display.public_questions(content, kind) for value in q['choices'].values()]
                    for literal in literals: self.assertIn(literal, choices)

    def test_unknown_titles_remain_original_and_known_titles_are_display_only(self):
        with self.app.test_request_context('/'):
            session['language'] = 'de'
            for slug in SLUGS:
                self.assertEqual(sql_display.title_text(slug, SUBJECTS[slug]['title']), TITLES[slug])
                self.assertEqual(sql_display.title_text(slug, 'An earlier topic title'), 'An earlier topic title')
                self.assertEqual(sql_display.title_language(slug, 'An earlier topic title'), 'en')
        self.assertEqual(self.rows('SELECT title FROM topics WHERE subject_id != ? ORDER BY subject_id', ('sql',)), [(SUBJECTS[s]['title'],) for s in sorted(SLUGS)])

    def test_every_saved_choice_and_explanation_translates_without_mutating_source(self):
        with self.app.test_request_context('/'):
            session['language'] = 'de'
            for slug in SLUGS:
                content = SUBJECTS[slug]['content']
                original = json.dumps((content.PRACTICE, content.QUIZ), sort_keys=True)
                for q in (*content.PRACTICE, *content.QUIZ):
                    answer = {'question_id': q['id'], 'prompt': q['prompt'], 'choices': q['choices'], 'explanation': q['explanation']}
                    view = sql_display.saved_answers([answer], content)[0]
                    self.assertEqual(view['language'], 'de')
                    self.assertFalse(view['translation_fallback'])
                    self.assertNotEqual(view['prompt'], q['prompt'])
                    self.assertNotEqual(view['explanation'], q['explanation'])
                self.assertEqual(json.dumps((content.PRACTICE, content.QUIZ), sort_keys=True), original)


if __name__ == '__main__': unittest.main()
