"""Explicit production setup; the approved local application stays unchanged."""

from contextlib import closing
import os
from pathlib import Path
import re
import sqlite3
import sys

from werkzeug.exceptions import SecurityError

from . import create_app, db


def production_config(environ=None):
    """Fail closed on missing secrets, unsafe data locations or unknown hosts."""
    env = os.environ if environ is None else environ
    secret = env.get("LWF_SECRET_KEY", "")
    if len(secret) < 32 or secret != secret.strip():
        raise RuntimeError("Set LWF_SECRET_KEY to a stable, randomly generated secret of at least 32 characters.")
    directory = Path(env.get("LWF_DATA_DIR", ""))
    source = Path(__file__).resolve().parents[1]
    if not directory.is_absolute() or directory == Path("/"):
        raise RuntimeError("Set LWF_DATA_DIR to an absolute private persistent directory.")
    directory = directory.resolve()
    if directory == source or directory.is_relative_to(source):
        raise RuntimeError("Production data must be outside the source and public static directories.")
    host_text = env.get("LWF_ALLOWED_HOSTS") or env.get("RENDER_EXTERNAL_HOSTNAME", "")
    hosts = [host.strip().lower() for host in host_text.split(",")]
    hostname = re.compile(r"(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
    if not hosts or any(not hostname.fullmatch(host) or ".." in host for host in hosts):
        raise RuntimeError("Set LWF_ALLOWED_HOSTS to exact hostnames without schemes, ports or wildcards.")
    return {
        "DATABASE": str(directory / "learning_with_francis.db"),
        "SECRET_KEY": secret,
        "TRUSTED_HOSTS": hosts,
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "DEBUG": False,
        "TESTING": False,
        "PREFERRED_URL_SCHEME": "https",
    }


def prepare_database(environ=None):
    """Initialise a new private schema-3 database, or validate without resetting."""
    config = production_config(environ)
    directory = Path(config["DATABASE"]).parent
    old_mask = os.umask(0o077)
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        return db.initialize_database(config["DATABASE"])
    finally:
        os.umask(old_mask)


def create_production_app(environ=None):
    """Use the Version 2 factory, an existing database and HTTPS-safe settings."""
    config = production_config(environ)
    with closing(db.open_database(config["DATABASE"])):
        pass
    app = create_app(config)

    @app.errorhandler(SecurityError)
    def invalid_host(error):
        # Host rejection happens before a URL adapter exists. Rendering the normal
        # error template would try to build links and turn a safe 400 into a 500.
        return "Invalid request host.", 400, {"Content-Type": "text/plain; charset=utf-8"}

    @app.get("/healthz")
    def health():
        try:
            db.get_db().execute("SELECT 1").fetchone()
        except (db.DatabaseSetupError, OSError, sqlite3.Error):
            return {"status": "unavailable"}, 503
        return {"status": "ok"}

    @app.after_request
    def production_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'"
        )
        return response

    return app


if __name__ == "__main__":
    if sys.argv[1:] != ["prepare"]:
        raise SystemExit("Usage: python -m learning_with_francis.production prepare")
    try:
        created = prepare_database()
    except (RuntimeError, OSError, db.DatabaseSetupError) as error:
        raise SystemExit(str(error)) from None
    print("Initialised fresh production schema 3." if created else "Existing production database validated; records unchanged.")
