"""Staff logins, stored as salted PBKDF2 hashes in staff.json.

Each record has a random `version` that is replaced whenever the login is
added, reset or its password changed. Sessions remember the version they
signed in with, so a removed or reset login stops working straight away
instead of when the session expires.
"""

import hashlib
import hmac
import json
import os
import secrets
import tempfile
from pathlib import Path

STAFF_FILE = Path(os.getenv("STAFF_FILE", Path(__file__).parent / "staff.json"))
ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def _check(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)


def load_staff() -> dict:
    if not STAFF_FILE.exists():
        return {}
    return json.loads(STAFF_FILE.read_text())


def save_staff(staff: dict) -> None:
    """Write staff.json readable by this user only, and atomically: a crash mid-write
    must never leave a half-written file, because that would block every login."""
    fd, tmp = tempfile.mkstemp(dir=STAFF_FILE.parent, prefix=".staff-", suffix=".tmp")  # created 0600
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(staff, indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STAFF_FILE)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def set_staff(username: str, name: str, password: str) -> None:
    """Add a login, or reset an existing one to a new temporary password."""
    staff = load_staff()
    username = username.strip().lower()
    staff[username] = {
        "name": name.strip(),
        "password_hash": hash_password(password),
        "must_change": True,
        "version": secrets.token_hex(8),
    }
    save_staff(staff)


def remove_staff(username: str) -> bool:
    staff = load_staff()
    if staff.pop(username.strip().lower(), None) is None:
        return False
    save_staff(staff)
    return True


def verify(username: str, password: str) -> str | None:
    """Return the staff member's display name if the login is valid."""
    record = load_staff().get(username.strip().lower())
    if record and _check(password, record["password_hash"]):
        return record["name"]
    return None


def session_version(username: str) -> str | int | None:
    """The login's current version, or None if the login doesn't exist."""
    record = load_staff().get(username.strip().lower())
    return record.get("version", 0) if record else None


def is_current(username: str, version) -> bool:
    """True if a session signed in at `version` is still allowed: the login exists
    and its password hasn't been reset or changed since."""
    current = session_version(username)
    return current is not None and version == current


def must_change(username: str) -> bool:
    """True while the staff member is still on the temporary password they were given."""
    record = load_staff().get(username.strip().lower())
    return bool(record and record.get("must_change"))


def change_password(username: str, current: str | None, new: str, confirm: str) -> str | None:
    """Set a new password. Returns a plain-English problem, or None on success.

    `current` may be None only for the forced first-login change, where the
    staff member has just signed in with their temporary password.
    """
    staff = load_staff()
    record = staff.get(username.strip().lower())
    if not record:
        return "We couldn't find your login. Please ask your manager for help."
    if current is not None and not _check(current, record["password_hash"]):
        return "Your current password isn't right. Please try again."
    if len(new) < 8:
        return "Please use at least 8 characters."
    if new != confirm:
        return "The two new passwords don't match."
    if _check(new, record["password_hash"]):
        return "Please choose a password different from the one you have now."
    record["password_hash"] = hash_password(new)
    record["must_change"] = False
    record["version"] = secrets.token_hex(8)
    save_staff(staff)
    return None
