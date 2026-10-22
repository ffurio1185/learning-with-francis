"""Visit-scoped storage. Browser requests never choose an owner's visit ID."""

import secrets
import unicodedata

from .db import get_db


def validate_name(value):
    if not isinstance(value, str):
        raise ValueError("Please enter your name.")
    name = value.strip()
    if not 1 <= len(name) <= 50:
        raise ValueError("Please enter a name between 1 and 50 characters.")
    # Support international names, spaces, apostrophes and hyphens, not markup/control characters.
    if not any(unicodedata.category(char).startswith("L") for char in name) or any(
        not (unicodedata.category(char)[0] in "LM" or char in " '-’") for char in name
    ):
        raise ValueError("Use letters, spaces, apostrophes or hyphens for your name.")
    return name


def active_visit(visit_id):
    if not isinstance(visit_id, str):
        return None
    return get_db().execute(
        "SELECT visit_id, display_name, started_at FROM visits WHERE visit_id = ? AND ended_at IS NULL",
        (visit_id,),
    ).fetchone()


def start_visit(name, previous_visit_id=None):
    """Save a new visitor, fresh progress and initial history atomically."""
    name = validate_name(name)
    visit_id = secrets.token_urlsafe(32)
    connection = get_db()
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        if previous_visit_id is not None:
            connection.execute(
                "UPDATE visits SET ended_at = datetime('now') WHERE visit_id = ? AND ended_at IS NULL",
                (previous_visit_id,),
            )
        connection.execute("INSERT INTO visits (visit_id, display_name) VALUES (?, ?)", (visit_id, name))
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
    with get_db() as connection:
        connection.execute(
            "UPDATE visits SET ended_at = datetime('now') WHERE visit_id = ? AND ended_at IS NULL",
            (visit_id,),
        )


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
