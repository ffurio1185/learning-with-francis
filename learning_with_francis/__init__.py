"""Separate Phase 2 application; Version 1 remains in the root app.py."""

from pathlib import Path

from datetime import timedelta

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

from flask_babel import gettext
from werkzeug.exceptions import HTTPException

from . import db, i18n
from .security import csrf_token, load_signing_key, valid_csrf
from . import visitors
from .learning import bp as learning_blueprint
from .progress import bp as progress_blueprint
from .display_time import berlin_datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_app(test_config=None):
    """Build the application without creating or resetting a database."""
    app = Flask(
        __name__,
        instance_path=str(PROJECT_ROOT / "instance"),
        static_folder=str(PROJECT_ROOT / "static"),
    )
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "learning_with_francis.db"),
        SECRET_KEY_FILE=str(Path(app.instance_path) / "session-signing-key"),
        SESSION_COOKIE_NAME="learning_with_francis_visit",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Local preview uses HTTP on loopback. Enable Secure when serving HTTPS.
        SESSION_COOKIE_SECURE=False,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=64 * 1024,
        BABEL_DEFAULT_LOCALE="en",
        BABEL_TRANSLATION_DIRECTORIES="translations",
    )
    if test_config is not None:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = load_signing_key(app.config["SECRET_KEY_FILE"])

    db.init_app(app)
    i18n.init_app(app)
    app.register_blueprint(learning_blueprint)
    app.register_blueprint(progress_blueprint)
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.add_template_filter(berlin_datetime)

    @app.after_request
    def private_pages(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    def render_home(error=None, status=200, entered_name=""):
        if not error:
            entered_name = getattr(g, "language_draft", {}).get("visitor_name", entered_name)
        subjects = db.get_db().execute("SELECT name FROM subjects ORDER BY display_order").fetchall()
        visit = visitors.active_visit(session.get("visit_id"))
        if visit is None:
            session.pop("visit_id", None)
        progress = visitors.current_progress(visit["visit_id"]) if visit else []
        return render_template("foundation.html", setup_ready=True, subjects=subjects,
                               visit=visit, progress=progress, error=error,
                               entered_name=entered_name), status

    @app.errorhandler(db.DatabaseSetupError)
    def unavailable(error):
        return render_template("foundation.html", setup_ready=False, subjects=[]), 503

    @app.errorhandler(HTTPException)
    def interface_error(error):
        messages = {403: gettext("You do not have access to this page."),
                    404: gettext("This page or result is not available for your visit."),
                    405: gettext("This action is not available with that request method."),
                    409: gettext("This form was already submitted with different answers. Use Try Again."),
                    413: gettext("This submission is too large. Please submit a smaller form.")}
        response = error.get_response()
        response.set_data(render_template("interface_error.html", code=error.code,
                          message=messages.get(error.code, gettext("The request could not be processed. Please try again."))))
        response.content_type = "text/html; charset=utf-8"
        return response

    @app.get("/")
    def cover():
        return render_template("cover.html")

    @app.get("/learn/")
    def index():
        return render_home()

    @app.post("/visits/start")
    def start_visit():
        if not valid_csrf(request.form.get("csrf_token")):
            return render_home(gettext("This form has expired. Please try again."), 400)
        names = request.form.getlist("visitor_name")
        try:
            name = visitors.validate_name(names[0] if len(names) == 1 else None)
        except ValueError as error:
            return render_home(str(error), 400, entered_name=names[0] if names else "")
        visit_id = visitors.start_visit(name, session.get("visit_id"))
        i18n.clear_visit_session()
        session["visit_id"] = visit_id
        return redirect(url_for("index"), code=303)

    def finish_visit(new_visit=False):
        if not valid_csrf(request.form.get("csrf_token")):
            return render_home(gettext("This form has expired. Please try again."), 400)
        visit = visitors.active_visit(session.get("visit_id"))
        if visit:
            visitors.end_visit(visit["visit_id"])
        i18n.clear_visit_session()
        flash(gettext("Start a fresh visit below.") if new_visit else gettext("Your visit has ended. Your saved history is retained."))
        return redirect(url_for("index"), code=303)

    @app.post("/visits/end")
    def end_visit():
        return finish_visit()

    @app.post("/visits/new")
    def new_visit():
        return finish_visit(new_visit=True)

    return app
