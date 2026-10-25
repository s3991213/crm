"""What the staff server remembers across restarts, in one small SQLite file:
open sessions, changes waiting for a Confirm click, and recent wrong passwords.

A connection per call keeps it safe from FastAPI's worker threads; traffic is a
few staff, so the cost doesn't matter.
"""

import json
import os
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path

STATE_DB = Path(os.getenv("CRM_STATE_DB", Path(__file__).parent / "data" / "state.db"))
PENDING_KEEP = 2 * 3600  # the backend refuses a change after 60 minutes, so older ones are only clutter

SCHEMA = """
create table if not exists sessions (id text primary key, username text not null, expires real not null);
create table if not exists pending (update_id text primary key, username text not null, update_json text not null,
                                    at real not null);
create table if not exists failed_logins (username text not null, at real not null);
"""


def _run(sql: str, args: tuple = ()) -> list[tuple]:
    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(STATE_DB, timeout=10)) as db:
        db.executescript(SCHEMA)
        with db:  # one transaction, committed on success
            return db.execute(sql, args).fetchall()


# --- sessions: signing out ends one here, so a copied cookie stops working too ---

def new_session(username: str, expires: float) -> str:
    _run("delete from sessions where expires < ?", (time.time(),))
    sid = secrets.token_urlsafe(24)
    _run("insert into sessions values (?, ?, ?)", (sid, username, expires))
    return sid


def session_open(sid: str, username: str) -> bool:
    return bool(_run("select 1 from sessions where id = ? and username = ? and expires >= ?",
                     (sid, username, time.time())))


def end_session(sid: str) -> None:
    _run("delete from sessions where id = ?", (sid,))


# --- changes this server showed, by update id: who may confirm them, and what to log ---

def add_pending(update_id: str, username: str, update: dict) -> None:
    now = time.time()
    _run("delete from pending where at < ?", (now - PENDING_KEEP,))
    _run("insert or replace into pending values (?, ?, ?, ?)", (update_id, username, json.dumps(update), now))


def take_pending(update_id: str, username: str) -> dict | None:
    """Remove and return the change, only for the person who asked for it. A second click gets None."""
    rows = _run("delete from pending where update_id = ? and username = ? returning update_json",
                (update_id, username))
    return json.loads(rows[0][0]) if rows else None


# --- wrong passwords, per username ---

def recent_failures(username: str, since: float) -> int:
    _run("delete from failed_logins where at < ?", (since,))
    return _run("select count(*) from failed_logins where username = ?", (username,))[0][0]


def add_failure(username: str, at: float) -> None:
    _run("insert into failed_logins values (?, ?)", (username, at))


def clear_failures(username: str) -> None:
    _run("delete from failed_logins where username = ?", (username,))
