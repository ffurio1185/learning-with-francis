"""Connected tracker: every read and write belongs to the signed-in browser visit."""

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .db import get_db
from .learning import visit_required
from .security import valid_csrf
from . import visitors


bp = Blueprint("progress", __name__, url_prefix="/progress")
STATUSES = ("Still Learning", "Needs Review", "Completed")


def learning_overview(visit_id):
    """Read one consistent snapshot; count attempts, never individual quiz answers."""
    connection = get_db()
    with connection:
        connection.execute("BEGIN")
        if visitors.active_visit(visit_id) is None:
            abort(403)
        topics = connection.execute(
            """SELECT p.topic_id, s.subject_id, s.name, t.title, p.learning_status,
                      p.understanding_confirmed_at,
                      COUNT(CASE WHEN a.activity_kind = 'practice' THEN 1 END) AS practice_attempts,
                      COUNT(CASE WHEN a.activity_kind = 'practice' AND a.score = 1 THEN 1 END) AS exercises_completed,
                      COUNT(CASE WHEN a.activity_kind = 'quiz' THEN 1 END) AS quiz_attempts
               FROM topic_progress AS p
               JOIN topics AS t ON t.topic_id = p.topic_id
               JOIN subjects AS s ON s.subject_id = t.subject_id
               LEFT JOIN learning_attempts AS a
                   ON a.visit_id = p.visit_id AND a.topic_id = p.topic_id
               WHERE p.visit_id = ?
               GROUP BY p.topic_id, s.subject_id, s.name, s.display_order, t.title,
                        p.learning_status, p.understanding_confirmed_at
               ORDER BY s.display_order""", (visit_id,)
        ).fetchall()
        activity = connection.execute(
            """SELECT a.attempt_id, a.activity_kind, a.score, a.total_questions,
                      a.submitted_at, s.name, s.subject_id
               FROM learning_attempts AS a
               JOIN topics AS t ON t.topic_id = a.topic_id
               JOIN subjects AS s ON s.subject_id = t.subject_id
               WHERE a.visit_id = ? ORDER BY a.submitted_at DESC, a.rowid DESC""", (visit_id,)
        ).fetchall()
        history = connection.execute(
            """SELECT h.history_id, h.previous_status, h.new_status, h.changed_at,
                      h.user_confirmed, s.name
               FROM topic_status_history AS h
               JOIN topics AS t ON t.topic_id = h.topic_id
               JOIN subjects AS s ON s.subject_id = t.subject_id
               WHERE h.visit_id = ? ORDER BY h.changed_at DESC, h.history_id DESC""", (visit_id,)
        ).fetchall()
    return {
        "topics": topics,
        "status_counts": [{"learning_status": status,
                           "topic_count": sum(row["learning_status"] == status for row in topics)}
                          for status in STATUSES],
        "totals": {key: sum(row[key] for row in topics)
                   for key in ("practice_attempts", "exercises_completed", "quiz_attempts")},
        "activity": activity,
        "history": history,
    }


def change_status(visit_id, topic_id, new_status, user_confirmed=False):
    """Save an owned status change and history atomically; never infer understanding."""
    if new_status not in STATUSES:
        raise ValueError("Choose Still Learning, Needs Review, or Completed.")
    if type(user_confirmed) is not bool:
        raise ValueError("Confirmation must come from your confirmation checkbox.")
    if new_status == "Completed" and not user_confirmed:
        raise ValueError("Please confirm that you understand this topic before selecting Completed.")
    connection = get_db()
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        if visitors.active_visit(visit_id) is None:
            abort(403)
        previous = connection.execute(
            """SELECT learning_status FROM topic_progress
               WHERE visit_id = ? AND topic_id = ?""", (visit_id, topic_id)
        ).fetchone()
        if previous is None:
            abort(404)
        # Refreshes or repeated Save clicks must not invent extra status changes.
        if previous["learning_status"] == new_status:
            return
        changed_at = connection.execute("SELECT datetime('now')").fetchone()[0]
        connection.execute(
            """UPDATE topic_progress SET learning_status = ?, understanding_confirmed_at = ?
               WHERE visit_id = ? AND topic_id = ?""",
            (new_status, changed_at if new_status == "Completed" else None, visit_id, topic_id),
        )
        connection.execute(
            """INSERT INTO topic_status_history
                   (visit_id, topic_id, previous_status, new_status, changed_at, user_confirmed)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (visit_id, topic_id, previous["learning_status"], new_status, changed_at,
             int(new_status == "Completed")),
        )


def render_progress(error=None, status=200):
    return render_template("progress.html", visit=g.learning_visit,
                           overview=learning_overview(g.learning_visit["visit_id"]),
                           statuses=STATUSES, error=error), status


@bp.get("/")
@visit_required
def index():
    return render_progress()


@bp.post("/<topic_id>/status")
@visit_required
def update_status(topic_id):
    if not valid_csrf(request.form.get("csrf_token")):
        return render_progress("This form has expired. Please reload My Progress and try again.", 400)
    try:
        statuses = request.form.getlist("new_status")
        if len(statuses) != 1:
            raise ValueError("Please choose one learning status.")
        change_status(g.learning_visit["visit_id"], topic_id, statuses[0],
                      user_confirmed=request.form.getlist("user_confirmed") == ["yes"])
    except ValueError as error:
        return render_progress(str(error), 400)
    flash("Your learning status is saved. Practice and quiz results stay separate from understanding.")
    return redirect(url_for("progress.index"), code=303)
