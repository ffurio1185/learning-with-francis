"""Local signing-key storage and form protection; no accounts or passwords."""

import hmac
import os
from pathlib import Path
import secrets
import tempfile

from flask import session


def load_signing_key(filename):
    """Keep one private signing key across restarts, outside source control."""
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # Publish a complete file atomically, without replacing another process's key.
        descriptor, temporary = tempfile.mkstemp(prefix=".session-key-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w") as handle:
                handle.write(secrets.token_hex(32))
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
        finally:
            Path(temporary).unlink()
    if path.stat().st_mode & 0o077:
        raise RuntimeError("Session signing key must be private (file permissions 600).")
    key = path.read_text().strip()
    if len(key) != 64 or any(character not in "0123456789abcdef" for character in key):
        raise RuntimeError("Invalid session signing key; restore the existing private key.")
    return key


def csrf_token():
    """Bind forms to this browser session, independently of the visitor name."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def valid_csrf(value):
    expected = session.get("csrf_token")
    return (isinstance(value, str) and isinstance(expected, str)
            and hmac.compare_digest(value.encode("utf-8"), expected.encode("utf-8")))
