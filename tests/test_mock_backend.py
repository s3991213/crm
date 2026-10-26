"""The mock backend must follow the API contract in README.md."""

import logging

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)
STAFF = {"X-Staff-Name": "Test Staff"}
CARD_KEYS = {"name", "status", "course", "last_contact", "payment_status"}


def chat(message: str) -> dict:
    response = client.post("/chat", json={"message": message, "staff_name": "Test Staff"}, headers=STAFF)
    assert response.status_code == 200
    return response.json()


def stage(message: str = "change Arjun's status to Withdrawn") -> dict:
    data = chat(message)
    assert data["type"] == "confirm_update"
    return data["update"]


def test_find_student_returns_card():
    data = chat("find Liam")
    assert data["type"] == "answer"
    assert data["student"]["name"] == "Liam Nguyen"
    assert set(data["student"]) == CARD_KEYS


def test_policy_answer_names_its_source():
    data = chat("what's the refund policy?")
    assert data["type"] == "answer" and "70%" in data["text"]
    assert data["sources"] == [{"policy": "Fees, Payment Plans and Refunds Policy",
                                "section": "Refunds when a student withdraws"}]


def test_summary_returns_history():
    data = chat("summarise Sofia's history")
    assert data["type"] == "answer"
    assert data["student"]["name"] == "Sofia Martinez"
    assert "Visa" in data["text"]


def test_draft_email_is_signed_by_staff():
    data = chat("draft a follow-up email for Priya")
    assert data["type"] == "draft_email"
    assert data["draft"]["to"] == "priya.sharma@example.com"
    assert data["draft"]["body"].rstrip().endswith("Test Staff")


@pytest.mark.parametrize(
    "message",
    ["find a student", "summarise a student's history", "draft a follow-up email", "change status to Active", "hello"],
)
def test_unclear_requests_ask_a_question(message):
    data = chat(message)
    assert data["type"] == "clarify"
    assert data["text"]


def test_at_risk_is_sorted_and_filtered():
    data = client.get("/at-risk", headers=STAFF).json()
    scores = [s["risk_score"] for s in data["students"]]
    assert scores == sorted(scores, reverse=True)
    assert all(score >= 0.4 for score in scores)
    assert "Priya Sharma" not in [s["name"] for s in data["students"]]
    assert all(s["reasons"] for s in data["students"])


def test_at_risk_via_chat():
    assert chat("who is at risk?")["type"] == "at_risk"


def test_cooling_leads_endpoint_and_chat():
    data = client.get("/cooling-leads", headers=STAFF).json()
    assert data["type"] == "cooling_leads" and {"name", "status", "course", "days_quiet", "reason"} <= set(data["leads"][0])
    assert chat("which leads are going cold?")["type"] == "cooling_leads"


def test_staging_a_change_saves_nothing():
    update = stage()
    assert update["old_value"] == "Active"
    assert update["new_value"] == "Withdrawn"
    assert main.STUDENTS[4]["status"] == "Active"


def test_new_value_keeps_original_case():
    assert stage("update Liam's course to Diploma of IT")["new_value"] == "Diploma of IT"


def test_confirm_writes_and_audits(caplog):
    update = stage()
    with caplog.at_level(logging.INFO, logger="audit"):
        response = client.post(f"/updates/{update['update_id']}/confirm", json={"staff_name": "Test Staff"}, headers=STAFF)
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert main.STUDENTS[4]["status"] == "Withdrawn"
    assert "staff='Test Staff'" in caplog.text
    assert "old='Active'" in caplog.text


def test_confirm_twice_fails_second_time():
    update = stage()
    url = f"/updates/{update['update_id']}/confirm"
    assert client.post(url, json={}, headers=STAFF).status_code == 200
    assert client.post(url, json={}, headers=STAFF).status_code == 404


def test_cancel_discards_the_change():
    update = stage()
    response = client.post(f"/updates/{update['update_id']}/cancel", json={}, headers=STAFF)
    assert response.json()["ok"] is True
    assert main.STUDENTS[4]["status"] == "Active"
    assert client.post(f"/updates/{update['update_id']}/confirm", json={}, headers=STAFF).status_code == 404
