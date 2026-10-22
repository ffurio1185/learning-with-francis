import sqlite3
from pathlib import Path


def connect_database(db_path):
    """
    Connect to an existing SQLite database.
    Raise an error if the file does not exist.
    Enable foreign keys.
    Return the database connection.
    """
    if not Path(db_path).is_file():
        raise FileNotFoundError(
            f"Database file not found: {db_path}"
        )

    database_uri = Path(db_path).resolve().as_uri() + "?mode=rw"
    connection = sqlite3.connect(database_uri, uri=True)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def list_topics(db_path):
    """
    Read learning topics from the existing SQLite database.

    Input: Path to the database file.
    Return: A list of tuples containing the topic ID,
    topic name, and learning status.
    Return an empty list if no topics exist.
    """
    connection = connect_database(db_path)

    try:
        cursor = connection.execute(
            "SELECT category_id, category_name, learning_status FROM Categories"
        )
        return cursor.fetchall()
    finally:
        connection.close()


def record_exercise(db_path, category_id, title):
    """
    Record a new learning exercise.

    Parameters:
        db_path: Path to the existing SQLite database.
        category_id: ID of the learning topic.
        title: Name of the exercise, which cannot be blank.

    Returns:
        The new task_id as an integer after saving successfully.

    The exercise starts incomplete (status = 0).
    The topic's learning status remains unchanged.
    """
    title = title.strip()

    if not title:
        raise ValueError("Exercise title cannot be empty.")

    connection = connect_database(db_path)

    try:
        cursor = connection.execute(
            "INSERT INTO Tasks (title, category_id) VALUES (?, ?)",
            (title, category_id)
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def record_quiz_attempt(db_path, category_id, quiz_name, correct_answers, total_questions):
    """
    Record a new quiz attempt for a learning topic.

    Parameters:
        db_path: Path to the existing SQLite database.
        category_id: ID of the learning topic.
        quiz_name: Nonblank name of the quiz.
        correct_answers: Whole number from 0 to total_questions.
        total_questions: Positive whole number of questions.

    Returns:
        The new attempt_id as an integer after saving successfully.

    Each call records a separate quiz attempt.
    The topic's learning status remains unchanged, even with a perfect score.
    Only the user can confirm when a topic is Completed.
    """

    quiz_name = quiz_name.strip()

    if not quiz_name:
        raise ValueError("Quiz name cannot be empty.")

    if type(correct_answers) is not int:
        raise TypeError("Correct answers must be an integer.")

    if type(total_questions) is not int:
        raise TypeError("Total questions must be an integer.")

    if total_questions <= 0:
        raise ValueError("Total questions must be greater than zero.")

    if correct_answers < 0 or correct_answers > total_questions:
        raise ValueError("Correct answers must be between 0 and total questions.")

    connection = connect_database(db_path)

    try:
        cursor = connection.execute(
            """
            INSERT INTO QuizAttempts
                (category_id, quiz_name, correct_answers, total_questions)
            VALUES (?, ?, ?, ?)
            """,
            (category_id, quiz_name, correct_answers, total_questions)
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def change_topic_status(db_path, category_id, new_status, user_confirmed=False):
    """
    Change a topic's learning status and record its history.

    Parameters:
        db_path: Path to the existing SQLite database.
        category_id: ID of the existing learning topic.
        new_status: Still Learning, Needs Review, or Completed.
        user_confirmed: Boolean indicating explicit user confirmation.
                        Defaults to False.

    Returns:
        The new history_id as an integer after both database
        changes have been saved successfully.

    Setting a topic to Completed requires user_confirmed to be True.
    Quiz scores and exercise results never confirm completion.

    Changing to Still Learning or Needs Review clears the
    current confirmation timestamp.

    The topic update and history entry must be saved together
    in one transaction. Both changes are rolled back on failure.
    """

    if new_status not in ("Still Learning", "Needs Review", "Completed"):
        raise ValueError(
            "Status must be Still Learning, Needs Review, or Completed."
        )

    if type(user_confirmed) is not bool:
        raise TypeError("User confirmation must be a boolean.")

    if new_status == "Completed" and user_confirmed is not True:
        raise ValueError(
            "Explicit user confirmation is required to mark a topic as Completed."
        )

    connection = connect_database(db_path)

    try:
        connection.execute("BEGIN IMMEDIATE")

        cursor = connection.execute(
            "SELECT learning_status FROM Categories WHERE category_id = ?",
            (category_id,)
        )

        row = cursor.fetchone()

        if row is None:
            raise ValueError("The specified topic ID does not exist.")

        previous_status = row[0]

        changed_at = connection.execute(
            "SELECT datetime('now')"
        ).fetchone()[0]

        if new_status == "Completed":
            confirmed_at = changed_at
        else:
            confirmed_at = None

        connection.execute(
            """
            UPDATE Categories
            SET learning_status = ?,
                understanding_confirmed_at = ?
            WHERE category_id = ?
            """,
            (new_status, confirmed_at, category_id)
        )

        history_cursor = connection.execute(
            """
            INSERT INTO TopicStatusHistory
                (category_id, previous_status, new_status, changed_at, user_confirmed)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                category_id,
                previous_status,
                new_status,
                changed_at,
                1 if new_status == "Completed" else 0
            )
        )

        connection.commit()
        return history_cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def create_topic(db_path, category_name):
    """
    Create a learning topic and its initial history entry.

    Parameters:
        db_path: Path to the existing SQLite database.
        category_name: Topic name, which cannot be blank.

    Returns:
        The new category_id as an integer after saving successfully.

    The topic starts as Still Learning with no confirmation timestamp.
    Its initial history has previous_status = NULL and user_confirmed = 0.

    Save the topic and history together in one transaction.
    Roll back both inserts if either fails.
    Existing topics and their history remain unchanged.
    """
    category_name = category_name.strip()

    if not category_name:
        raise ValueError("Topic name cannot be empty.")

    connection = connect_database(db_path)

    try:
        connection.execute("BEGIN IMMEDIATE")

        topic_cursor = connection.execute(
            "INSERT INTO Categories (category_name) VALUES (?)",
            (category_name,)
        )

        category_id = topic_cursor.lastrowid

        connection.execute(
            """
            INSERT INTO TopicStatusHistory
                (category_id, previous_status, new_status, user_confirmed)
            VALUES (?, ?, ?, ?)
            """,
            (category_id, None, "Still Learning", 0)
        )

        connection.commit()
        return category_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_learning_overview(db_path):
    """Read topic counts and dated practice/status history without changing data.

    Return lists of dictionaries under status_counts, topic_counts,
    practice_history, and status_history. Counts cover all saved topics.
    Topics without practice are included with zero counts.
    """
    connection = connect_database(db_path)
    connection.row_factory = sqlite3.Row

    try:
        # All four queries read the same database snapshot.
        connection.execute("BEGIN")
        status_counts = connection.execute(
            """
            WITH statuses(learning_status, display_order) AS (
                VALUES ('Still Learning', 1), ('Needs Review', 2), ('Completed', 3)
            )
            SELECT statuses.learning_status, COUNT(Categories.category_id) AS topic_count
            FROM statuses
            LEFT JOIN Categories
                ON Categories.learning_status = statuses.learning_status
            GROUP BY statuses.learning_status, statuses.display_order
            ORDER BY statuses.display_order
            """
        ).fetchall()

        # Count each practice table first so multiple quizzes cannot multiply
        # the number of exercises when the results are joined to a topic.
        topic_counts = connection.execute(
            """
            WITH exercise_counts AS (
                SELECT category_id, COUNT(task_id) AS exercise_count,
                       COUNT(CASE WHEN status = 1 THEN task_id END) AS completed_exercises
                FROM Tasks
                GROUP BY category_id
            ), quiz_counts AS (
                SELECT category_id, COUNT(attempt_id) AS quiz_attempt_count
                FROM QuizAttempts
                GROUP BY category_id
            )
            SELECT Categories.category_id, Categories.category_name,
                   Categories.learning_status,
                   COALESCE(exercise_counts.exercise_count, 0) AS exercise_count,
                   COALESCE(exercise_counts.completed_exercises, 0) AS completed_exercises,
                   COALESCE(quiz_counts.quiz_attempt_count, 0) AS quiz_attempt_count
            FROM Categories
            LEFT JOIN exercise_counts ON exercise_counts.category_id = Categories.category_id
            LEFT JOIN quiz_counts ON quiz_counts.category_id = Categories.category_id
            ORDER BY Categories.category_id
            """
        ).fetchall()

        practice_history = connection.execute(
            """
            SELECT practice.*, Categories.category_name
            FROM (
                SELECT task_id AS entry_id, category_id, 'Exercise' AS practice_type,
                       title, created_at AS recorded_at, completed_at,
                       status AS exercise_status, NULL AS correct_answers,
                       NULL AS total_questions
                FROM Tasks
                UNION ALL
                SELECT attempt_id, category_id, 'Quiz', quiz_name, attempted_at,
                       NULL, NULL, correct_answers, total_questions
                FROM QuizAttempts
            ) AS practice
            JOIN Categories ON Categories.category_id = practice.category_id
            ORDER BY practice.recorded_at DESC, practice.practice_type, practice.entry_id DESC
            """
        ).fetchall()

        status_history = connection.execute(
            """
            SELECT TopicStatusHistory.history_id, TopicStatusHistory.category_id,
                   Categories.category_name, TopicStatusHistory.previous_status,
                   TopicStatusHistory.new_status, TopicStatusHistory.changed_at,
                   TopicStatusHistory.user_confirmed
            FROM TopicStatusHistory
            JOIN Categories ON Categories.category_id = TopicStatusHistory.category_id
            ORDER BY TopicStatusHistory.changed_at DESC, TopicStatusHistory.history_id DESC
            """
        ).fetchall()

        return {
            "status_counts": [dict(row) for row in status_counts],
            "topic_counts": [dict(row) for row in topic_counts],
            "practice_history": [dict(row) for row in practice_history],
            "status_history": [dict(row) for row in status_history],
        }
    finally:
        connection.close()
