from flask import Flask, render_template, request, redirect, url_for
from pathlib import Path
from database import list_topics, change_topic_status, get_learning_overview
app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "milestone3_test.db"
@app.route("/")
def show_topics():
    """Display learning topics and their current statuses."""
    return render_topics_page()


def render_topics_page(error=None):
    """Include the same summaries and history on normal and error pages."""
    return render_template(
        "topics.html",
        topics=list_topics(DB_PATH),
        overview=get_learning_overview(DB_PATH),
        error=error
    )


@app.route("/topics/<int:category_id>/status", methods=["POST"])
def update_topic_status(category_id):
    """Save a topic's selected status using explicit form confirmation."""
    new_status = request.form.get("new_status", "")
    user_confirmed = request.form.get("user_confirmed") == "yes"

    try:
        change_topic_status(
            DB_PATH,
            category_id,
            new_status,
            user_confirmed=user_confirmed
        )
    except ValueError as error:
        return render_topics_page(error=str(error)), 400

    return redirect(url_for("show_topics"), code=303)
