"""frontend/api.py against the mock backend, plus how it reports failures."""

import functools
import logging

import httpx
import pytest

import api
import main

pytestmark = pytest.mark.anyio


@pytest.fixture
def use_transport(monkeypatch):
    def install(transport):
        monkeypatch.setattr(api.httpx, "AsyncClient", functools.partial(httpx.AsyncClient, transport=transport))
    return install


@pytest.fixture
def mock_backend(use_transport):
    use_transport(httpx.ASGITransport(app=main.app))


async def test_chat_round_trip(mock_backend):
    data = await api.chat("find Liam", "Test Staff", "session-1")
    assert data["type"] == "answer"
    assert data["student"]["name"] == "Liam Nguyen"


async def test_at_risk(mock_backend):
    data = await api.at_risk("Test Staff")
    assert data["students"]


async def test_confirm_flow_sends_staff_name(mock_backend, caplog):
    caplog.set_level(logging.INFO, logger="audit")
    data = await api.chat("change Arjun's status to Withdrawn", "Test Staff", "session-1")
    result = await api.confirm_update(data["update"]["update_id"], "Test Staff")
    assert result["ok"] is True
    assert "staff='Test Staff'" in caplog.text


async def test_cancel(mock_backend):
    data = await api.chat("change Arjun's status to Withdrawn", "Test Staff", "session-1")
    assert (await api.cancel_update(data["update"]["update_id"], "Test Staff"))["ok"] is True
    assert main.STUDENTS[4]["status"] == "Active"


async def test_unknown_update_is_an_error(mock_backend):
    with pytest.raises(api.BackendError) as exc:
        await api.confirm_update("no-such-id", "Test Staff")
    assert not exc.value.timed_out


async def test_timeout_is_flagged(use_transport):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)
    use_transport(httpx.MockTransport(handler))
    with pytest.raises(api.BackendError) as exc:
        await api.chat("hi", "Test Staff", "s")
    assert exc.value.timed_out


async def test_server_error(use_transport):
    use_transport(httpx.MockTransport(lambda request: httpx.Response(500)))
    with pytest.raises(api.BackendError) as exc:
        await api.at_risk("Test Staff")
    assert not exc.value.timed_out


async def test_non_json_reply(use_transport):
    use_transport(httpx.MockTransport(lambda request: httpx.Response(200, text="<html>oops</html>")))
    with pytest.raises(api.BackendError):
        await api.at_risk("Test Staff")


async def test_connection_refused(use_transport):
    def handler(request):
        raise httpx.ConnectError("refused", request=request)
    use_transport(httpx.MockTransport(handler))
    with pytest.raises(api.BackendError):
        await api.chat("hi", "Test Staff", "s")
