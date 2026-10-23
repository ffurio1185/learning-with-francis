"""Visit-scoped storage. Browser requests never choose an owner's visit ID."""

from datetime import datetime, timedelta, timezone

import secrets
import unicodedata

from flask import current_app
from flask_babel import gettext

from .db import get_db


def validate_name(value):
    if not isinstance(value, str):
        raise ValueError(gettext("Please enter your name."))
    name = value.strip()
    if not 1 <= len(name) <= 50:
        raise ValueError(gettext("Please enter a name between 1 and 50 characters."))
    # Support international names, spaces, apostrophes and hyphens, not markup/control characters.
    if not any(unicodedata.category(char).startswith("L") for char in name) or any(
        not (unicodedata.category(char)[0] in "LM" or char in " '-’") for char in name
    ):
        raise ValueError(gettext("Use letters, spaces, apostrophes or hyphens for your name."))
    return name


def utc_now():
    """UTC storage clock; browser-supplied dates never determine expiration."""
    return datetime.now(timezone.utc)


def activity_times():
    now = utc_now()
    cutoff = now - timedelta(seconds=current_app.config["VISIT_IDLE_SECONDS"])
    return now.strftime("%Y-%m-%d %H:%M:%S"), cutoff.strftime("%Y-%m-%d %H:%M:%S")


def active_visit(visit_id):
    """Check expiry without renewing it, including inside write transactions."""
    if not isinstance(visit_id, str):
        return None
    _, cutoff = activity_times()
    return get_db().execute(
        """SELECT visit_id, display_name, started_at FROM visits
           WHERE visit_id = ? AND ended_at IS NULL
             AND COALESCE(last_activity_at, started_at) > ?""",
        (visit_id, cutoff),
    ).fetchone()


def delete_visit_records(connection, visit_id):
    """Delete only this owner, children first. Caller owns the transaction."""
    connection.execute(
        "DELETE FROM learning_answers WHERE attempt_id IN "
        "(SELECT attempt_id FROM learning_attempts WHERE visit_id = ?)", (visit_id,))
    for table in ("learning_attempts", "topic_status_history", "topic_progress", "visits"):
        connection.execute(f"DELETE FROM {table} WHERE visit_id = ?", (visit_id,))


def cleanup_expired_visits():
    """Lazy cleanup, including ended legacy visits; never create/upgrade storage."""
    connection = get_db()
    _, cutoff = activity_times()
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        expired = connection.execute(
            "SELECT visit_id FROM visits WHERE ended_at IS NOT NULL "
            "OR COALESCE(last_activity_at, started_at) <= ?", (cutoff,)).fetchall()
        for row in expired:
            delete_visit_records(connection, row["visit_id"])
    return len(expired)


def record_activity(visit_id):
    """Renew only an unexpired visit after a successful learning request."""
    connection = get_db()
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        now, cutoff = activity_times()
        row = connection.execute(
            "SELECT last_activity_at FROM visits WHERE visit_id = ? AND ended_at IS NULL "
            "AND COALESCE(last_activity_at, started_at) > ?", (visit_id, cutoff)).fetchone()
        if row is None:
            # It may have expired or been ended in another tab during the request.
            delete_visit_records(connection, visit_id)
            return False
        if row["last_activity_at"] is None or row["last_activity_at"] < now:
            connection.execute("UPDATE visits SET last_activity_at = ? WHERE visit_id = ?", (now, visit_id))
    return True


def start_visit(name, previous_visit_id=None):
    """Save a new visitor, fresh progress and initial history atomically."""
    name = validate_name(name)
    visit_id = secrets.token_urlsafe(32)
    connection = get_db()
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        if previous_visit_id is not None:
            delete_visit_records(connection, previous_visit_id)
        now, _ = activity_times()
        connection.execute(
            "INSERT INTO visits (visit_id, display_name, started_at, last_activity_at) VALUES (?, ?, ?, ?)",
            (visit_id, name, now, now))
        connection.execute(
            "INSERT INTO topic_progress (visit_id, topic_id) SELECT ?, topic_id FROM topics", (visit_id,)
        )
        connection.execute(
            """INSERT INTO topic_status_history
                   (visit_id, topic_id, previous_status, new_status, user_confirmed)
               SELECT visit_id, topic_id, NULL, 'Still Learning', 0
               FROM topic_progress WHERE visit_id = ?""", (visit_id,)
        )
    return visit_id


def end_visit(visit_id):
    """Remove the entire visit atomically; shared curriculum is never deleted."""
    with get_db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        delete_visit_records(connection, visit_id)


def current_progress(visit_id):
    """Only return progress for the active owner resolved from the signed session."""
    return get_db().execute(
        """SELECT subjects.subject_id, subjects.name, topics.title, progress.learning_status
           FROM topic_progress AS progress
           JOIN visits ON visits.visit_id = progress.visit_id AND visits.ended_at IS NULL
           JOIN topics ON topics.topic_id = progress.topic_id
           JOIN subjects ON subjects.subject_id = topics.subject_id
           WHERE progress.visit_id = ? ORDER BY subjects.display_order""", (visit_id,)
    ).fetchall()
