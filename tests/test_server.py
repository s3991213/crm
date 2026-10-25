"""frontend/server.py: sign-in, sessions, the password rules, and passing requests to the (mock) backend."""

import functools
import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

import api
import main
import server
import staff_auth
import state

POST_JSON = {"Content-Type": "application/json"}


@pytest.fixture
def backend_calls(monkeypatch):
    """Send the server's backend calls to the mock backend, and record them."""
    calls = []

    async def record(request):
        calls.append(request)

    monkeypatch.setattr(api.httpx, "AsyncClient", functools.partial(
        httpx.AsyncClient, transport=httpx.ASGITransport(app=main.app), event_hooks={"request": [record]}))
    return calls


@pytest.fixture
def client(staff_file, backend_calls, monkeypatch, tmp_path):
    monkeypatch.setattr(server, "SECRET", "x" * 40)
    monkeypatch.setattr(server, "UI_DIR", tmp_path / "dist")
    monkeypatch.setattr(server, "WRITES_LOG", tmp_path / "writes.log")  # never the real audit log
    server.write_log.handlers.clear()
    monkeypatch.setattr(state, "STATE_DB", tmp_path / "state.db")
    staff_auth.set_staff("priya", "Priya Shah", "temporary1")
    with TestClient(server.app) as c:
        yield c
    for h in server.write_log.handlers:
        h.close()
    server.write_log.handlers.clear()


def sign_in(client, password="temporary1", username="priya"):
    r = client.post("/api/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def ready(client):
    """Signed in, with the first-login password change done."""
    sign_in(client)
    assert client.post("/api/password", json={"new": "my-own-pass", "confirm": "my-own-pass"}).status_code == 200


def say(client, message, conversation="c1"):
    return client.post("/api/chat", json={"message": message, "conversation_id": conversation})


# --- signing in ----------------------------------------------------------------

def test_wrong_password_is_refused(client):
    r = client.post("/api/login", json={"username": "priya", "password": "nope"})
    assert r.status_code == 401
    assert client.get("/api/me").status_code == 401


def test_repeated_wrong_passwords_lock_the_username_for_a_minute(client, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(server.time, "time", lambda: clock[0])
    for _ in range(server.MAX_FAILS):
        assert client.post("/api/login", json={"username": "priya", "password": "nope"}).status_code == 401
    r = client.post("/api/login", json={"username": "Priya", "password": "temporary1"})
    assert r.status_code == 429 and "wait a minute" in r.json()["detail"]
    clock[0] += server.LOCK_SECONDS + 1
    sign_in(client)


def test_sign_in_sets_a_strict_http_only_cookie(client):
    r = client.post("/api/login", json={"username": " Priya ", "password": "temporary1"})
    assert r.json() == {"name": "Priya Shah", "must_change": True}
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "temporary1" not in cookie
    assert client.get("/api/me").json() == {"name": "Priya Shah", "must_change": True}


def test_tampered_cookie_is_refused(client):
    sign_in(client)
    value = client.cookies.get(server.COOKIE)
    client.cookies.clear()
    client.cookies.set(server.COOKIE, value[:-2] + ("00" if not value.endswith("00") else "11"))
    assert client.get("/api/me").status_code == 401


def test_expired_cookie_is_refused(client, monkeypatch):
    sign_in(client)
    monkeypatch.setattr(server.time, "time", lambda: 10**12)
    assert client.get("/api/me").status_code == 401


def test_logout_clears_the_session(client):
    sign_in(client)
    client.post("/api/logout")
    assert client.get("/api/me").status_code == 401


def test_logout_ends_the_session_on_the_server_too(client):
    sign_in(client)
    copied = client.cookies.get(server.COOKIE)
    client.post("/api/logout")
    client.cookies.set(server.COOKIE, copied)
    assert client.get("/api/me").status_code == 401


def test_logout_leaves_other_sessions_signed_in(client):
    sign_in(client)
    other = TestClient(server.app)
    sign_in(other)
    client.post("/api/logout")
    assert other.get("/api/me").status_code == 200


def test_cookie_from_before_session_ids_is_refused(client):
    body = json.dumps({"u": "priya", "v": staff_auth.session_version("priya"), "exp": 10**11}).encode()
    client.cookies.set(server.COOKIE, server.base64.urlsafe_b64encode(body).decode() + "." + server._sign(body))
    assert client.get("/api/me").status_code == 401


# --- passwords -------------------------------------------------------------------

def test_chat_waits_for_the_first_password_change(client, backend_calls):
    sign_in(client)
    r = say(client, "find Liam")
    assert r.status_code == 403 and "password first" in r.json()["detail"]
    assert client.get("/api/at-risk").status_code == 403
    assert backend_calls == []


def test_password_change_keeps_this_session_and_ends_others(client):
    sign_in(client)
    other = TestClient(server.app)
    sign_in(other)
    r = client.post("/api/password", json={"new": "my-own-pass", "confirm": "my-own-pass"})
    assert r.status_code == 200
    assert client.get("/api/me").json()["must_change"] is False
    assert other.get("/api/me").status_code == 401


def test_password_problems_are_explained(client):
    sign_in(client)
    r = client.post("/api/password", json={"new": "short", "confirm": "short"})
    assert r.status_code == 400 and "8 characters" in r.json()["detail"]


def test_later_password_change_needs_the_current_one(client):
    ready(client)
    r = client.post("/api/password", json={"current": "wrong", "new": "another-pass", "confirm": "another-pass"})
    assert r.status_code == 400
    r = client.post("/api/password", json={"current": "my-own-pass", "new": "another-pass", "confirm": "another-pass"})
    assert r.status_code == 200


def test_reset_by_a_manager_ends_the_session(client):
    ready(client)
    staff_auth.set_staff("priya", "Priya Shah", "temporary2")
    assert say(client, "find Liam").status_code == 401


def test_asking_to_change_password_never_reaches_the_backend(client, backend_calls):
    ready(client)
    r = say(client, "I want to change my password")
    assert r.json()["type"] == "change_password"
    assert backend_calls == []


# --- the backend -------------------------------------------------------------------

def test_chat_sends_the_signed_in_name_not_the_browsers(client, backend_calls):
    ready(client)
    r = client.post("/api/chat", json={"message": "find Liam", "conversation_id": "c1", "staff_name": "Someone Else"},
                    headers={"X-Staff-Name": "Someone Else"})
    assert r.json()["student"]["name"] == "Liam Nguyen"
    sent = backend_calls[-1]
    assert sent.headers["X-Staff-Name"] == "Priya Shah"
    assert json.loads(sent.content)["session_id"] == "priya:c1"


def test_confirm_writes_the_log_once(client, caplog):
    caplog.set_level(logging.INFO, logger="crm.writes")
    ready(client)
    update = say(client, "change Arjun's status to Withdrawn").json()["update"]
    r = client.post(f"/api/updates/{update['update_id']}/confirm")
    assert r.status_code == 200 and r.json()["ok"]
    assert "student='Arjun Patel'" in caplog.text and "staff='Priya Shah'" in caplog.text
    again = client.post(f"/api/updates/{update['update_id']}/confirm")
    assert again.status_code == 404 and "already been handled" in again.json()["detail"]


def test_waiting_change_and_session_survive_a_restart(client):
    ready(client)
    update = say(client, "change Arjun's status to Withdrawn").json()["update"]
    cookies = dict(client.cookies)
    client.__exit__(None, None, None)  # the server shuts down...
    with TestClient(server.app, cookies=cookies) as again:  # ...and starts again, from state.db alone
        assert again.get("/api/me").status_code == 200
        assert again.post(f"/api/updates/{update['update_id']}/confirm").status_code == 200


def test_cancel_does_not_log_a_write(client, caplog):
    caplog.set_level(logging.INFO, logger="crm.writes")
    ready(client)
    update = say(client, "change Arjun's status to Withdrawn").json()["update"]
    assert client.post(f"/api/updates/{update['update_id']}/cancel").json()["ok"]
    assert "student=" not in caplog.text


def test_only_the_person_who_asked_can_confirm(client):
    ready(client)
    update = say(client, "change Arjun's status to Withdrawn").json()["update"]
    staff_auth.set_staff("tom", "Tom Lee", "temporary1")
    other = TestClient(server.app)
    sign_in(other, username="tom")
    other.post("/api/password", json={"new": "toms-own-pass", "confirm": "toms-own-pass"})
    assert other.post(f"/api/updates/{update['update_id']}/confirm").status_code == 404


def test_refusal_reason_reaches_staff(client, monkeypatch):
    ready(client)
    update = say(client, "change Arjun's status to Withdrawn").json()["update"]

    async def refused(*args):
        raise api.BackendError("409", refused="The record changed.")
    monkeypatch.setattr(api, "confirm_update", refused)
    r = client.post(f"/api/updates/{update['update_id']}/confirm")
    assert r.status_code == 409 and r.json()["detail"] == "Not saved. The record changed."


def test_backend_down_gets_a_friendly_message(client, monkeypatch):
    ready(client)

    async def down(*args):
        raise api.BackendError("refused")
    monkeypatch.setattr(api, "chat", down)
    r = say(client, "find Liam")
    assert r.status_code == 502 and "couldn't reach" in r.json()["detail"]


# --- the UI files ------------------------------------------------------------------

def test_ui_is_served_with_a_fallback_to_index(client, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "assets" / "app.js").write_text("js")
    assert client.get("/").text == "<html>app</html>"
    assert client.get("/assets/app.js").text == "js"
    assert client.get("/some/page").text == "<html>app</html>"
    assert client.get("/../server.py").text == "<html>app</html>"
    assert client.get("/api/nothing").status_code == 404
