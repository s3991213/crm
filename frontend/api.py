"""Thin HTTP client for the CRM Assistant FastAPI backend.

All business logic lives in the backend. This module only sends requests
and returns the JSON it gets back. See README.md for the API contract.
"""

import os

import httpx

API_BASE_URL = os.getenv("CRM_API_BASE_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT = float(os.getenv("CRM_API_TIMEOUT", "60"))


class BackendError(Exception):
    """The backend could not be reached or returned an error."""

    def __init__(self, message: str, timed_out: bool = False):
        super().__init__(message)
        self.timed_out = timed_out


async def _request(method: str, path: str, staff_name: str, json: dict | None = None) -> dict:
    headers = {"X-Staff-Name": staff_name}
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=API_TIMEOUT) as client:
            response = await client.request(method, path, json=json, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as exc:
        raise BackendError(str(exc), timed_out=True) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise BackendError(str(exc)) from exc


async def chat(message: str, staff_name: str, session_id: str) -> dict:
    return await _request(
        "POST", "/chat", staff_name, {"message": message, "staff_name": staff_name, "session_id": session_id}
    )


async def at_risk(staff_name: str) -> dict:
    return await _request("GET", "/at-risk", staff_name)


async def confirm_update(update_id: str, staff_name: str) -> dict:
    return await _request("POST", f"/updates/{update_id}/confirm", staff_name, {"staff_name": staff_name})


async def cancel_update(update_id: str, staff_name: str) -> dict:
    return await _request("POST", f"/updates/{update_id}/cancel", staff_name, {"staff_name": staff_name})
