import json

import pytest
from fastapi.testclient import TestClient

import backend.main as main


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Use isolated temporary storage for every test."""
    test_history_file = tmp_path / "audit_history.json"
    monkeypatch.setattr(main, "AUDIT_HISTORY_FILE", test_history_file)

    with TestClient(main.app) as test_client:
        yield test_client


def test_get_empty_audit_history(client):
    response = client.get("/audit-history")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["total_records"] == 0
    assert response.json()["records"] == []


def test_create_inspection_record(client):
    payload = {
        "event_type": "inspection",
        "url": "https://example.com",
        "viewport": "1366x768",
        "approval_state": "not_applicable",
        "detected_issues": [],
    }

    response = client.post("/audit-history", json=payload)

    assert response.status_code == 200

    record = response.json()["record"]

    assert response.json()["status"] == "success"
    assert record["event_type"] == "inspection"
    assert record["url"] == "https://example.com/"
    assert record["id"]
    assert record["timestamp"]


def test_reject_invalid_event_type(client):
    payload = {
        "event_type": "unknown",
        "url": "https://example.com",
    }

    response = client.post("/audit-history", json=payload)

    assert response.status_code == 400


def test_reject_invalid_viewport(client):
    payload = {
        "event_type": "inspection",
        "url": "https://example.com",
        "viewport": "123x456",
    }

    response = client.post("/audit-history", json=payload)

    assert response.status_code == 400


def test_records_are_persisted_and_newest_first(client):
    first_payload = {
        "event_type": "inspection",
        "url": "https://example.com",
        "viewport": "1366x768",
    }

    second_payload = {
        "event_type": "repair",
        "url": "https://example.org",
        "viewport": "375x812",
        "approval_state": "approved",
        "repair_result": {"status": "success"},
    }

    first_response = client.post("/audit-history", json=first_payload)
    second_response = client.post("/audit-history", json=second_payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_id = first_response.json()["record"]["id"]
    second_id = second_response.json()["record"]["id"]

    history_response = client.get("/audit-history")
    history = history_response.json()

    assert history_response.status_code == 200
    assert history["total_records"] == 2
    assert history["records"][0]["id"] == second_id
    assert history["records"][1]["id"] == first_id

    saved_records = json.loads(
        main.AUDIT_HISTORY_FILE.read_text(encoding="utf-8")
    )

    assert len(saved_records) == 2
    assert saved_records[0]["id"] == second_id
