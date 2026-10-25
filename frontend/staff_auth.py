"""Staff logins, stored as salted PBKDF2 hashes in staff.json."""

import hashlib
import hmac
import json
import os
import secrets
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
    STAFF_FILE.write_text(json.dumps(staff, indent=2))


def verify(username: str, password: str) -> str | None:
    """Return the staff member's display name if the login is valid."""
    record = load_staff().get(username.strip().lower())
    if record and _check(password, record["password_hash"]):
        return record["name"]
    return None


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
    save_staff(staff)
    return None
