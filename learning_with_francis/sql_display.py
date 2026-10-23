"""Subject translations are view copies, never replacements for canonical saved answers."""

from flask_babel import gettext, get_locale
from . import sql_content
from .sql_content import N_
from .subjects import SUBJECTS


SQL_TITLES = (N_("SELECT and WHERE"), N_("Reading tables with SELECT and WHERE"))
# Subject IDs disambiguate q1/practice1, which are reused by different subjects.
TITLES = {slug: (info["title"],) for slug, info in SUBJECTS.items()}
TITLES["sql"] = SQL_TITLES
QUESTIONS_BY_TOPIC = {
    info["content"].TOPIC_ID: {q["id"]: q for q in (*info["content"].PRACTICE, *info["content"].QUIZ)}
    for info in SUBJECTS.values()
}
QUESTIONS = QUESTIONS_BY_TOPIC[sql_content.TOPIC_ID]


def known_content(content):
    return any(content is info["content"] for info in SUBJECTS.values())


def content_language(subject):
    return str(get_locale() or "en") if subject in SUBJECTS else "en"


def title_text(subject, original):
    return gettext(original) if original in TITLES.get(subject, ()) else original


def title_language(subject, original):
    return content_language(subject) if original in TITLES.get(subject, ()) else "en"


def public_questions(content, kind, questions=None):
    source = content.public_questions(kind, questions)
    if not known_content(content):
        return source
    display = []
    for question in source:
        prompt = question["prompt"]
        display.append({"id": question["id"], "prompt": gettext(prompt),
                        "choices": {key: gettext(text) for key, text in question["choices"].items()}})
    return display


def saved_answers(answers, content=sql_content):
    """Translate only exact known snapshots; retain older wording without guessing."""
    questions = QUESTIONS_BY_TOPIC.get(content.TOPIC_ID, {}) if known_content(content) else {}
    language = str(get_locale() or "en")
    display = []
    for answer in answers:
        current = questions.get(answer["question_id"])
        known = current is not None and (answer["prompt"], answer["choices"], answer["explanation"]) == (
            current["prompt"], current["choices"], current["explanation"])
        item = {**answer, "language": language if known else "en",
                "translation_fallback": not known and language == "de"}
        if known:
            prompt, explanation = answer["prompt"], answer["explanation"]
            item.update(prompt=gettext(prompt), explanation=gettext(explanation),
                        choices={key: gettext(text) for key,text in answer["choices"].items()})
        display.append(item)
    return display


def feedback(kind, score, name):
    if kind == "practice":
        return (gettext("Well done, %(name)s! You solved the practice exercise.", name=name) if score else
                gettext("Keep practicing, %(name)s! Read the explanation and try again.", name=name))
    if score <= 2:
        return gettext("Keep practicing, %(name)s! Review the lesson and try again. You can do it!", name=name)
    if score <= 4:
        return gettext("Well done, %(name)s! You passed the quiz. Keep practicing to improve your score!", name=name)
    return gettext("Congratulations, %(name)s! Perfect score! You answered all five questions correctly!", name=name)
