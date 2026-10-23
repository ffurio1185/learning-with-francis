"""L3 SQL localization; original snapshots/answer keys remain canonical English."""

from contextlib import closing
from html import unescape
from html.parser import HTMLParser
from retention_support import learning_snapshot

import re
import unittest

from flask import session
from werkzeug.datastructures import MultiDict

from learning_with_francis import create_app, db, sql_content, sql_display
from learning_with_francis.subjects import SUBJECTS
from test_interface_language import CheckedAnswers
from test_phase2_sql import HiddenFields, SQLFlowSupport


class CodeBlocks(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.in_pre=False; self.blocks=[]
        self.feed(html)
    def handle_starttag(self, tag, attributes):
        if tag=='pre': self.in_pre=True;self.blocks.append('')
    def handle_endtag(self, tag):
        if tag=='pre': self.in_pre=False
    def handle_data(self,data):
        if self.in_pre:self.blocks[-1]+=data


class SQLLanguageTests(SQLFlowSupport, unittest.TestCase):
    def switch(self, language='de', path='/sql/', client=None, **extra):
        client=client or self.client
        fields=HiddenFields(client.get(path).text).fields
        return client.post('/preferences/language',data={**fields,'language':language,**extra})

    def test_english_default_and_german_lesson_keep_exact_executable_examples(self):
        english=self.client.get('/sql/').text
        self.assertIn('SQL: SELECT and WHERE',english)
        before=learning_snapshot(self.path)
        self.switch()
        german=self.client.get('/sql/').text
        for text in ('SQL: SELECT und WHERE','Spalten mit SELECT auswählen','Zeilen mit WHERE auswählen','Willkommen, Francis!'):
            self.assertIn(text,german)
        self.assertEqual(CodeBlocks(english).blocks,CodeBlocks(german).blocks)
        self.assertNotIn('interface-scope',german)
        self.assertEqual(learning_snapshot(self.path),before)


    def test_sql_titles_translate_on_home_progress_and_lesson_without_metadata_writes(self):
        before=learning_snapshot(self.path);self.switch()
        for path in ('/learn/','/progress/'):
            self.assertIn('Tabellen mit SELECT und WHERE lesen',self.client.get(path).text)
        self.assertIn('<title>SELECT und WHERE',self.client.get('/sql/').text)
        self.assertEqual(learning_snapshot(self.path),before)


    def test_all_fifteen_public_questions_are_localized_without_keys_or_explanations(self):
        with self.app.test_request_context('/'):
            session['language']='de'
            for kind in ('practice','quiz'):
                source=sql_content.questions_for(kind)
                shown=sql_display.public_questions(sql_content,kind)
                self.assertEqual(len(shown),len(source))
                for original,question in zip(source,shown):
                    self.assertEqual(set(question),{'id','prompt','choices'})
                    self.assertEqual(question['id'],original['id'])
                    self.assertNotEqual(question['prompt'],original['prompt'])
                    self.assertEqual(set(question['choices']),set(original['choices']))
                    for key,value in original['choices'].items():
                        if value.startswith(('SELECT','WHERE')) or value in ('Alex','Mia','Sam'):
                            self.assertEqual(question['choices'][key],value)
        self.switch()
        for kind in ('practice','quiz'):
            html=self.client.get('/sql/'+kind).text
            self.assertNotIn('correct_option',html)
            for q in sql_content.questions_for(kind):
                self.assertNotIn(q['explanation'],html)
                with self.app.test_request_context('/'):
                    session['language']='de'
                    translated=sql_display.gettext(q['explanation'])
                self.assertNotIn(translated,unescape(html))

    def test_all_six_scores_receive_correct_personalized_german_feedback(self):
        self.switch()
        for score in range(6):
            response=self.submit(score)
            self.assertEqual(response.status_code,303)
            html=self.client.get(response.location).text
            self.assertIn(f'{score} von 5',html)
            self.assertIn('Francis!',html)
            self.assertIn('Übe weiter' if score<=2 else 'Quiz bestanden' if score<5 else 'Volle Punktzahl',html)
            self.assertEqual(html.count('class="answer-result correct-answer"'),score)
        self.assertEqual(self.rows('SELECT score FROM learning_attempts ORDER BY rowid'),[(i,) for i in range(6)])
        self.assertEqual(self.rows('SELECT DISTINCT learning_status FROM topic_progress'),[('Still Learning',)])

    def test_german_quiz_saves_english_snapshots_and_original_answer_ids(self):
        self.switch();response=self.submit(5)
        rows=self.rows('SELECT question_id,prompt,selected_option,correct_option,explanation FROM learning_answers ORDER BY position')
        self.assertEqual(rows,[(q['id'],q['prompt'],q['correct'],q['correct'],q['explanation']) for q in sql_content.QUIZ])
        html=unescape(self.client.get(response.location).text)
        self.assertIn('Die anzuzeigenden Spalten',html)
        self.assertIn('Die Spaltennamen hinter SELECT',html)
        self.assertNotIn(sql_content.QUIZ[0]['prompt'],html)

    def test_ten_practice_questions_give_localized_feedback_and_keep_round_counts(self):
        self.switch();path='/sql/practice'
        for position,question in enumerate(sql_content.PRACTICE):
            html=self.client.get(path).text
            self.assertIn(f'Frage {position+1} von 10',html)
            self.assertNotIn(question['prompt'],unescape(html))
            fields=HiddenFields(html).fields
            option=question['correct'] if position%2==0 else next(k for k in question['choices'] if k!=question['correct'])
            response=self.client.post('/sql/practice',data={**fields,question['id']:option})
            html=unescape(self.client.get(response.location).text)
            self.assertIn('Du hast die Übungsaufgabe richtig gelöst.' if position%2==0 else 'Lies die Erklärung',html)
            self.assertNotIn(question['explanation'],html)
            path=unescape(re.search(r'id="practice-next" href="([^"]+)"',html)[1])
        self.assertIn('Übungsrunde abgeschlossen!',self.client.get(path).text)
        self.assertEqual(self.rows("SELECT COUNT(*),SUM(score) FROM learning_attempts WHERE activity_kind='practice'"),[(10,5)])
        self.assertEqual(self.rows('SELECT DISTINCT learning_status FROM topic_progress'),[('Still Learning',)])

    def test_quiz_draft_switches_languages_without_changing_token_or_selected_answers(self):
        data=self.payload(3)
        before=learning_snapshot(self.path)
        response=self.client.post('/preferences/language',data={**data,'language':'de'})
        html=self.client.get(response.location).text
        expected={q['id']:data[q['id']] for q in sql_content.QUIZ}
        self.assertEqual(CheckedAnswers(html).answers,expected)
        self.assertEqual(HiddenFields(html).fields['submission_token'],data['submission_token'])
        self.assertIn('Was wählt SELECT',html)
        self.assertEqual(learning_snapshot(self.path),before)
        response=self.client.post('/sql/quiz',data={**HiddenFields(html).fields,**expected})
        self.assertIn('3 von 5',self.client.get(response.location).text)


    def test_english_results_can_be_read_in_german_without_rewriting_any_records(self):
        response=self.submit(4);location=response.location
        before=learning_snapshot(self.path)
        self.switch(path=location)
        html=self.client.get(location).text
        self.assertIn('Quiz bestanden',html)
        self.assertIn('Was wählt SELECT',html)
        self.switch('en',location)
        self.assertIn(sql_content.QUIZ[0]['prompt'],self.client.get(location).text)
        self.assertEqual(learning_snapshot(self.path),before)


    def test_unknown_legacy_snapshot_is_kept_in_original_language_without_guessing(self):
        response=self.submit(5);location=response.location
        with closing(db.open_database(self.path)) as connection:
            connection.execute("UPDATE learning_answers SET prompt='Earlier reviewed question', explanation='Earlier explanation' WHERE question_id='q1'")
            connection.commit()
        before=learning_snapshot(self.path);self.switch(path=location)
        html=self.client.get(location).text
        self.assertIn('Earlier reviewed question',html)
        self.assertIn('Earlier explanation',html)
        self.assertIn('frühere Formulierung',html)
        self.assertNotIn('Was wählt SELECT in einer Abfrage?',html)
        self.assertEqual(learning_snapshot(self.path),before)


    def test_unknown_title_and_changed_choices_preserve_saved_wording(self):
        with self.app.test_request_context('/'):
            session['language']='de'
            self.assertEqual(sql_display.title_text('sql','My earlier topic title'),'My earlier topic title')
            q=sql_content.QUIZ[0]
            row={'question_id':q['id'],'prompt':q['prompt'],'choices':{**q['choices'],'b':'Earlier correct choice'},'explanation':q['explanation']}
            shown=sql_display.saved_answers([row])[0]
            self.assertEqual(shown['choices']['b'],'Earlier correct choice')
            self.assertEqual(shown['language'],'en')
            self.assertTrue(shown['translation_fallback'])
            self.assertEqual(row['choices']['b'],'Earlier correct choice')

    def test_cross_language_duplicate_submissions_do_not_add_attempts(self):
        data=self.payload(5)
        first=self.client.post('/sql/quiz',data=data)
        self.switch(path=first.location)
        before=learning_snapshot(self.path)
        second=self.client.post('/sql/quiz',data=data)
        self.assertEqual(second.location,first.location)
        data['q1']='a'
        self.assertEqual(self.client.post('/sql/quiz',data=data).status_code,409)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM learning_attempts'),[(1,)])
        self.assertEqual(learning_snapshot(self.path),before)


    def test_two_same_name_visitors_keep_private_results_in_different_languages(self):
        other=self.app.test_client();self.start(other)
        self.switch();result=self.submit(5)
        self.assertIn('Herzlichen Glückwunsch, Francis!',self.client.get(result.location).text)
        self.assertEqual(other.get(result.location).status_code,404)
        self.assertIn('No practice or quiz activity yet',other.get('/progress/').text)
        self.assertIn('What does SELECT choose',other.get('/sql/quiz').text)
        self.assertIn('Was wählt SELECT',self.client.get('/sql/quiz').text)

    def test_html_in_saved_name_is_escaped_in_german_feedback(self):
        with closing(db.open_database(self.path)) as connection:
            connection.execute("UPDATE visits SET display_name=?",('<img src=x onerror=alert(1)>',));connection.commit()
        self.switch();result=self.submit(5)
        html=self.client.get(result.location).text
        self.assertNotIn('<img src=x',html)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;',html)
        self.assertIn('Herzlichen Glückwunsch',html)

    def test_invalid_answers_and_forged_scores_cannot_bypass_german_grading(self):
        self.switch();before=learning_snapshot(self.path);data=self.payload(0)
        self.assertEqual(self.client.post('/sql/quiz',data=MultiDict({**data,'q1':['a','b']})).status_code,400)
        self.assertEqual(learning_snapshot(self.path),before)
        data.update(score='5',total_questions='1',language='en',visit_id='foreign')
        self.assertEqual(self.client.post('/sql/quiz',data=data).status_code,303)
        self.assertEqual(self.rows('SELECT score,total_questions FROM learning_attempts'),[(0,5)])


    def test_results_survive_restart_and_read_only_language_changes(self):
        self.switch();response=self.submit(5)
        before=learning_snapshot(self.path)
        name=self.app.config['SESSION_COOKIE_NAME']
        client=create_app(self.config).test_client()
        client.set_cookie(name,self.client.get_cookie(name).value)
        self.assertIn('Volle Punktzahl',client.get(response.location).text)
        self.assertIn('5 / 5 richtig',client.get('/progress/').text)
        self.assertEqual(learning_snapshot(self.path),before)


    def test_other_subjects_are_localized_after_l4(self):
        self.switch()
        for slug in ('python','javascript','sap'):
            source=SUBJECTS[slug]['content']
            html=unescape(self.client.get(f'/{slug}/quiz').text)
            self.assertNotIn(source.QUIZ[0]['prompt'],html)
            self.assertIn('lang="de"',html)
            self.assertNotIn('interface-scope',html)
        self.assertEqual(sql_content.CONTENT_VERSION,'sql-select-where-v1')
        self.assertEqual(sql_content.PRACTICE_VERSION,'sql-select-where-practice-v2')


if __name__=='__main__':unittest.main()
