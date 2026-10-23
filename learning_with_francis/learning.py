"""Shared subject flow: grade on the server and save visit-owned, topic-owned activity."""

from functools import wraps
import json
import secrets

from flask import Blueprint, abort, current_app, g, redirect, render_template, request, session, url_for
from itsdangerous import BadData, URLSafeTimedSerializer

from flask_babel import gettext

from .db import get_db
from .security import valid_csrf
from . import sql_content, sql_display, visitors
from .subjects import SUBJECTS

bp = Blueprint("learning", __name__)


@bp.url_value_preprocessor
def select_subject(endpoint, values):
    slug = values.pop("subject")
    if slug not in SUBJECTS:
        abort(404)
    g.learning_subject = {"slug": slug, **SUBJECTS[slug]}
    g.learning_content = SUBJECTS[slug]["content"]


@bp.url_defaults
def subject_urls(endpoint, values):
    if endpoint.startswith("learning."):
        values.setdefault("subject", getattr(g, "learning_subject", {}).get("slug", "sql"))


@bp.context_processor
def subject_template_context():
    info = getattr(g, "learning_subject", {"slug": "sql", **SUBJECTS["sql"]})
    return {"subject": {"slug": info["slug"], "name": info["name"], "title": sql_display.title_text(info["slug"], info["title"])},
            "learning_content_language": sql_display.content_language(info["slug"])}


def visit_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        g.learning_visit = visitors.active_visit(session.get("visit_id"))
        if g.learning_visit is None:
            session.pop("visit_id", None)
            return redirect(url_for("index"), code=303)
        return function(*args, **kwargs)
    return wrapped


def signer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="sql-activity-submission")


def submission_token(kind):
    content = getattr(g, "learning_content", sql_content)
    return signer().dumps({"visit": g.learning_visit["visit_id"], "kind": kind,
                           "version": content.CONTENT_VERSION, "topic": content.TOPIC_ID, "nonce": secrets.token_urlsafe(32)})


def validate_submission(token, kind):
    content = getattr(g, "learning_content", sql_content)
    try:
        data = signer().loads(token, max_age=12 * 60 * 60)
    except (BadData, TypeError):
        raise ValueError(gettext("This activity form has expired or is invalid. Please open it again.")) from None
    if (not isinstance(data, dict) or data.get("visit") != g.learning_visit["visit_id"]
        or data.get("kind") != kind or data.get("version") != content.CONTENT_VERSION
        or data.get("topic", sql_content.TOPIC_ID) != content.TOPIC_ID
        or not isinstance(data.get("nonce"), str) or len(data["nonce"]) != 43):
        raise ValueError(gettext("This activity form belongs to a different visit or activity. Please open it again."))
    return data["nonce"]


def grade_answers(form, kind, questions=None):
    """Validate exactly one known answer for every question; ignore browser scores."""
    content = getattr(g, "learning_content", sql_content)
    answers = []
    source = content.questions_for(kind) if questions is None else questions
    expected = {q["id"] for q in source}
    if any(key.startswith(("q", "practice")) and key not in expected for key in form):
        raise ValueError(gettext("Please submit answers only for this activity's questions."))
    for question in source:
        selected = form.getlist(question["id"])
        if len(selected) != 1 or selected[0] not in question["choices"]:
            raise ValueError(gettext("Please choose one listed answer for every question."))
        answers.append({**question, "selected": selected[0],
                        "is_correct": int(selected[0] == question["correct"])})
    return answers


def save_attempt(kind, nonce, answers):
    """Serialize duplicate submissions; answers and score commit together."""
    content = getattr(g, "learning_content", sql_content)
    connection = get_db()
    visit_id = g.learning_visit["visit_id"]
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        # Recheck inside the write transaction in case another tab just ended the visit.
        if visitors.active_visit(visit_id) is None:
            abort(403)
        previous = connection.execute(
            "SELECT attempt_id, visit_id, activity_kind, topic_id FROM learning_attempts WHERE submission_id = ?", (nonce,)
        ).fetchone()
        if previous is not None:
            saved = connection.execute(
                "SELECT question_id, selected_option FROM learning_answers WHERE attempt_id = ? ORDER BY position",
                (previous["attempt_id"],),
            ).fetchall()
            if (previous["visit_id"] != visit_id or previous["activity_kind"] != kind or previous["topic_id"] != content.TOPIC_ID
                or [(row["question_id"], row["selected_option"]) for row in saved]
                    != [(row["id"], row["selected"]) for row in answers]):
                abort(409, description=gettext("This form was already submitted with different answers. Use Try Again."))
            return previous["attempt_id"]
        attempt_id = secrets.token_urlsafe(24)
        score = sum(answer["is_correct"] for answer in answers)
        connection.execute(
            """INSERT INTO learning_attempts
                (attempt_id, submission_id, visit_id, topic_id, activity_kind, content_version, score, total_questions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (attempt_id, nonce, visit_id, content.TOPIC_ID, kind,
             content.PRACTICE_VERSION if kind == "practice" else content.CONTENT_VERSION, score, len(answers)),
        )
        connection.executemany(
            """INSERT INTO learning_answers
                (attempt_id, position, question_id, prompt, choices_json, selected_option,
                 correct_option, is_correct, explanation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(attempt_id, position, answer["id"], answer["prompt"], json.dumps(answer["choices"]),
              answer["selected"], answer["correct"], answer["is_correct"], answer["explanation"])
             for position, answer in enumerate(answers, 1)],
        )
    # Activity never updates topic_progress or topic_status_history.
    return attempt_id


def activity_overview(visit_id):
    content = getattr(g, "learning_content", sql_content)
    connection = get_db()
    counts = connection.execute(
        """SELECT COUNT(CASE WHEN activity_kind = 'practice' THEN 1 END) AS practice_attempts,
                  COUNT(CASE WHEN activity_kind = 'practice' AND score = 1 THEN 1 END) AS exercises_completed,
                  COUNT(CASE WHEN activity_kind = 'quiz' THEN 1 END) AS quiz_attempts
           FROM learning_attempts WHERE visit_id = ? AND topic_id = ?""", (visit_id, content.TOPIC_ID)
    ).fetchone()
    history = connection.execute(
        """SELECT attempt_id, activity_kind, score, total_questions, submitted_at
           FROM learning_attempts WHERE visit_id = ? AND topic_id = ?
           ORDER BY submitted_at DESC, rowid DESC""", (visit_id, content.TOPIC_ID)
    ).fetchall()
    return counts, history


@bp.get("/<subject>/")
@visit_required
def lesson():
    counts, history = activity_overview(g.learning_visit["visit_id"])
    template = "sql_lesson.html" if g.learning_subject["slug"] == "sql" else "subject_lesson.html"
    return render_template(template, visit=g.learning_visit, counts=counts, history=history)


def activity(kind):
    content = getattr(g, "learning_content", sql_content)
    error = None
    status = 200
    if request.method == "POST":
        try:
            if not valid_csrf(request.form.get("csrf_token")):
                raise ValueError(gettext("This form has expired. Please try again."))
            nonce = validate_submission(request.form.get("submission_token"), kind)
            answers = grade_answers(request.form, kind)
        except ValueError as failure:
            error, status = str(failure), 400
        else:
            attempt_id = save_attempt(kind, nonce, answers)
            return redirect(url_for("learning.results", attempt_id=attempt_id), code=303)
    # Keep a valid form token on validation errors; a corrected resubmission is still one attempt.
    token = request.form.get("submission_token") if error else getattr(g, "language_draft", {}).get("submission_token")
    if token:
        try:
            validate_submission(token, kind)
        except ValueError:
            token = None
    return render_template("sql_activity.html", visit=g.learning_visit, kind=kind,
                           questions=sql_display.public_questions(content, kind), error=error,
                           selected=request.form, submission_token=token or submission_token(kind)), status


@bp.route("/<subject>/practice", methods=["GET", "POST"])
@visit_required
def practice():
    content = getattr(g, "learning_content", sql_content)
    error, status, selected = None, 200, request.form
    run_id = secrets.token_urlsafe(32)
    position = 0
    try:
        if request.method == "POST":
            if not valid_csrf(request.form.get("csrf_token")):
                raise ValueError(gettext("This form has expired. Please try again."))
            data = practice_token_data(request.form.get("submission_token"), "practice-question")
            run_id, position = data["run"], data.get("position")
            if type(position) is not int or not 0 <= position < len(content.PRACTICE):
                raise ValueError(gettext("This practice question is invalid. Please start again."))
            if request.form.get("position") != str(position):
                raise ValueError(gettext("This form does not match the displayed question. Please try again."))
            question = content.PRACTICE[position]
            answers = grade_answers(request.form, "practice", (question,))
            # A token is issued only for the next unanswered question. Check again
            # on submission, allowing a repeated POST for an already-saved answer.
            if position > practice_position(run_id):
                raise ValueError(gettext("Please answer the earlier practice questions first."))
            attempt_id = save_attempt("practice", f"{run_id}:{position}", answers)
            return redirect(url_for("learning.results", attempt_id=attempt_id), code=303)
        if request.args.get("run"):
            run_id = practice_token_data(request.args["run"], "practice-round")["run"]
        position = practice_position(run_id)
    except ValueError as failure:
        error, status = str(failure), 400
        # Recover only an in-range question index. Never render a forged index.
        if type(position) is not int or not 0 <= position < len(content.PRACTICE):
            position = 0
    g.language_return_path = url_for("learning.practice", run=practice_token(run_id, "practice-round"))
    if position == len(content.PRACTICE) and not error:
        return render_template("practice_complete.html", visit=g.learning_visit, total=len(content.PRACTICE))
    question = content.PRACTICE[position]
    return render_template("sql_activity.html", visit=g.learning_visit, kind="practice",
                           questions=sql_display.public_questions(content, "practice", (question,)),
                           error=error, selected=selected, practice_position=position,
                           practice_total=len(content.PRACTICE),
                           submission_token=practice_token(run_id, "practice-question", position)), status


def practice_token(run_id, purpose, position=None):
    content = getattr(g, "learning_content", sql_content)
    data = {"visit": g.learning_visit["visit_id"], "kind": purpose,
            "version": content.PRACTICE_VERSION, "topic": content.TOPIC_ID, "run": run_id}
    if position is not None:
        data["position"] = position
    return signer().dumps(data)


def practice_token_data(token, purpose):
    content = getattr(g, "learning_content", sql_content)
    try:
        data = signer().loads(token, max_age=12 * 60 * 60)
    except (BadData, TypeError):
        raise ValueError(gettext("This practice form has expired or is invalid. Please start again.")) from None
    if (not isinstance(data, dict) or data.get("visit") != g.learning_visit["visit_id"]
        or data.get("kind") != purpose or data.get("version") != content.PRACTICE_VERSION
        or data.get("topic", sql_content.TOPIC_ID) != content.TOPIC_ID
        or not isinstance(data.get("run"), str) or len(data["run"]) != 43
        or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-" for char in data["run"])):
        raise ValueError(gettext("This practice form belongs to a different visit or round. Please start again."))
    return data


def practice_position(run_id):
    """Find the first unsaved question using this visit's round-specific records."""
    content = getattr(g, "learning_content", sql_content)
    saved = get_db().execute(
        """SELECT submission_id FROM learning_attempts
           WHERE visit_id = ? AND topic_id = ? AND activity_kind = 'practice' AND content_version = ?
             AND submission_id IN (""" + ",".join("?" for _ in content.PRACTICE) + ")",
        (g.learning_visit["visit_id"], content.TOPIC_ID, content.PRACTICE_VERSION,
         *(f"{run_id}:{position}" for position in range(len(content.PRACTICE)))),
    ).fetchall()
    ids = {row["submission_id"] for row in saved}
    return next((position for position in range(len(content.PRACTICE))
                 if f"{run_id}:{position}" not in ids), len(content.PRACTICE))


def practice_navigation(attempt):
    """Retain old single-question results; add continuation only to new rounds."""
    content = getattr(g, "learning_content", sql_content)
    if attempt["activity_kind"] != "practice" or attempt["content_version"] != content.PRACTICE_VERSION:
        return None
    run_id, separator, number = attempt["submission_id"].partition(":")
    if not separator or not number.isdigit() or not 0 <= int(number) < len(content.PRACTICE):
        return None
    return {"position": int(number) + 1, "total": len(content.PRACTICE),
            "next_url": url_for("learning.practice", run=practice_token(run_id, "practice-round"))}


@bp.route("/<subject>/quiz", methods=["GET", "POST"])
@visit_required
def quiz():
    return activity("quiz")


@bp.get("/<subject>/results/<attempt_id>")
@visit_required
def results(attempt_id):
    content = getattr(g, "learning_content", sql_content)
    attempt = get_db().execute(
        "SELECT * FROM learning_attempts WHERE attempt_id = ? AND visit_id = ? AND topic_id = ?",
        (attempt_id, g.learning_visit["visit_id"], content.TOPIC_ID),
    ).fetchone()
    if attempt is None:
        abort(404)
    answers = []
    for row in get_db().execute("SELECT * FROM learning_answers WHERE attempt_id = ? ORDER BY position", (attempt_id,)):
        answers.append({**dict(row), "choices": json.loads(row["choices_json"])})
    name = g.learning_visit["display_name"]
    feedback = sql_display.feedback(attempt["activity_kind"], attempt["score"], name)
    answers = sql_display.saved_answers(answers, content)
    return render_template("sql_results.html", visit=g.learning_visit, attempt=attempt,
                           answers=answers, feedback=feedback, practice_navigation=practice_navigation(attempt))
