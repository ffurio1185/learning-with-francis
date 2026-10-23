"""Semantic DB snapshot: successful page reads may renew only last_activity_at."""
from contextlib import closing
import sqlite3


def learning_snapshot(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        schema = connection.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        data = {}
        for (table,) in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            columns = [row[1] for row in connection.execute(f"PRAGMA table_info({quoted})")
                       if not (table == "visits" and row[1] == "last_activity_at")]
            fields = ','.join('"' + col.replace('"', '""') + '"' for col in columns)
            data[table] = connection.execute(f"SELECT {fields} FROM {quoted} ORDER BY rowid").fetchall()
        return schema, data
