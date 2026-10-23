"""Explicit, non-destructive database setup for the Phase 2 foundation."""

from contextlib import closing
from pathlib import Path
import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


APPLICATION_ID = 0x4C574631  # LWF1: distinguishes this database from Version 1.
SCHEMA_VERSION = 4
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
MIGRATION_PATH = Path(__file__).with_name("migrations") / "002_visitors.sql"
ACTIVITY_MIGRATION_PATH = Path(__file__).with_name("migrations") / "003_sql_activity.sql"


RETENTION_MIGRATION_PATH = Path(__file__).with_name("migrations") / "004_temporary_visits.sql"


class DatabaseSetupError(RuntimeError):
    """The selected file is missing or is not a supported Phase 2 database."""


def open_database(db_path):
    """Open and validate an existing Phase 2 database; never create one here."""
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise DatabaseSetupError("Phase 2 database is missing. Run the init-db command first.")

    connection = None
    try:
        connection = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA secure_delete = ON")
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if application_id == APPLICATION_ID and version in (1, 2, 3):
            raise DatabaseSetupError("Phase 2 needs the explicit upgrade-db command; left unchanged.")
        if application_id != APPLICATION_ID or version != SCHEMA_VERSION:
            raise DatabaseSetupError("This is not a supported Phase 2 database; left unchanged.")
        connection.execute("SELECT subject_id, name, display_order FROM subjects LIMIT 0")
        connection.execute("SELECT topic_id, subject_id, title FROM topics LIMIT 0")
        connection.execute("SELECT visit_id, display_name, started_at, ended_at, last_activity_at FROM visits LIMIT 0")
        connection.execute("SELECT visit_id, topic_id, learning_status, understanding_confirmed_at FROM topic_progress LIMIT 0")
        connection.execute("SELECT history_id, visit_id, topic_id, changed_at FROM topic_status_history LIMIT 0")
        connection.execute("SELECT attempt_id, visit_id, score FROM learning_attempts LIMIT 0")
        connection.execute("SELECT attempt_id, question_id, selected_option FROM learning_answers LIMIT 0")
        return connection
    except (sqlite3.Error, DatabaseSetupError) as error:
        if connection is not None:
            connection.close()
        if isinstance(error, DatabaseSetupError):
            raise
        raise DatabaseSetupError("Phase 2 database validation failed; left unchanged.") from error


def initialize_database(db_path):
    """Create curriculum metadata once, or validate an existing file unchanged.

    Return True for a new database and False for an existing valid database.
    Existing files are never overwritten, reset, or migrated by this command.
    """
    path = Path(db_path).expanduser().resolve()
    if path.exists():
        with closing(open_database(path)):
            return False

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb"):
            pass
    except FileExistsError as error:
        raise DatabaseSetupError("Database file already exists; left unchanged.") from error
    reserved = path.stat()

    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(schema)
            connection.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))
            connection.executescript(ACTIVITY_MIGRATION_PATH.read_text(encoding="utf-8"))
            connection.executescript(RETENTION_MIGRATION_PATH.read_text(encoding="utf-8"))
        with closing(open_database(path)):
            pass
        return True
    except (sqlite3.Error, DatabaseSetupError) as error:
        # Remove only the new file reserved by this invocation on setup failure.
        if path.exists():
            current = path.stat()
            if (current.st_dev, current.st_ino) == (reserved.st_dev, reserved.st_ino):
                path.unlink()
        raise DatabaseSetupError("Phase 2 initialization failed; no partial database retained.") from error


def upgrade_database(db_path):
    """Explicitly upgrade Phase 2, retaining all records and making a backup first.

    No upgrade is performed on requests or by init-db. Existing backups are
    never overwritten. The migration commits completely or rolls back.
    """
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise DatabaseSetupError("Database is missing; left unchanged.")
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            marker = connection.execute("PRAGMA application_id").fetchone()[0]
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if marker != APPLICATION_ID or version not in (1, 2, 3, SCHEMA_VERSION):
                raise DatabaseSetupError("Not a supported Phase 2 database; left unchanged.")
            if version == SCHEMA_VERSION:
                with closing(open_database(path)):
                    return None
            tables = [row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
            # Compare the original columns, even when a migration adds metadata.
            columns = {table: [row[1] for row in connection.execute(
                'PRAGMA table_info("' + table.replace('"', '""') + '")')] for table in tables}
            def existing_records():
                return {table: connection.execute('SELECT ' + ','.join(
                    '"' + column.replace('"', '""') + '"' for column in columns[table])
                    + ' FROM "' + table.replace('"', '""') + '" ORDER BY 1').fetchall() for table in tables}
            records = existing_records()
            backup_suffix = {1: ".before-p2.2.db", 2: ".before-p2.3.db", 3: ".before-temporary-visits.db"}[version]
            backup_path = path.with_name(path.stem + backup_suffix)
            with backup_path.open("xb"):
                pass
            with closing(sqlite3.connect(backup_path)) as backup:
                connection.backup(backup)
            try:
                bodies = []
                for target, filename in ((2, MIGRATION_PATH), (3, ACTIVITY_MIGRATION_PATH), (4, RETENTION_MIGRATION_PATH)):
                    if version < target:
                        migration = filename.read_text(encoding="utf-8").strip()
                        if not migration.startswith("BEGIN IMMEDIATE;") or not migration.endswith("COMMIT;"):
                            raise DatabaseSetupError("Migration needs BEGIN IMMEDIATE and COMMIT.")
                        bodies.append(migration[len("BEGIN IMMEDIATE;"):-len("COMMIT;")])
                # All needed migrations and record comparisons share one transaction.
                connection.executescript("BEGIN IMMEDIATE;\n" + "\n".join(bodies))
                if existing_records() != records:
                    raise DatabaseSetupError("Migration changed existing records; rolled back.")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            return backup_path
    except (sqlite3.Error, OSError) as error:
        raise DatabaseSetupError("Upgrade failed; original data retained. Check the backup before retrying.") from error


def get_db():
    """Keep one validated connection per Flask request or command."""
    if "phase2_db" not in g:
        g.phase2_db = open_database(current_app.config["DATABASE"])
    return g.phase2_db


def close_db(error=None):
    connection = g.pop("phase2_db", None)
    if connection is not None:
        connection.close()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create the separate database, with no reset or overwrite option."""
    try:
        created = initialize_database(current_app.config["DATABASE"])
    except DatabaseSetupError as error:
        raise click.ClickException(str(error)) from error
    outcome = "Initialized" if created else "Already initialized; left unchanged"
    click.echo(f"{outcome}: {current_app.config['DATABASE']}")


@click.command("check-db")
@with_appcontext
def check_db_command():
    """Check database identity, schema version, and curriculum row counts."""
    try:
        connection = get_db()
        subjects = connection.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        topics = connection.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
    except DatabaseSetupError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Phase 2 database ready (schema {SCHEMA_VERSION}): {subjects} subjects, {topics} topics.")


@click.command("upgrade-db")
@with_appcontext
def upgrade_db_command():
    """Back up and upgrade an existing Phase 2 database; never touch Version 1."""
    try:
        backup = upgrade_database(current_app.config["DATABASE"])
    except DatabaseSetupError as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Upgraded to schema {SCHEMA_VERSION}; backup: {backup}" if backup
               else "Already current; left unchanged.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(check_db_command)
    app.cli.add_command(upgrade_db_command)
