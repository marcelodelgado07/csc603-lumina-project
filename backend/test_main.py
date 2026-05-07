"""
Tests for the Lumina FastAPI backend.

The HuggingFace call is mocked so these run fast and don't burn API quota.

Run from backend/:
    pip install -r requirements-dev.txt
    pytest -v
"""

import json
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ─────────────────────────────────────────────
# Sample payloads (Schemas 1 & 2)
# ─────────────────────────────────────────────

SAMPLE_USER = {
    "user_id": 1,
    "earliest_study_time": "08:00:00",
    "latest_study_time": "21:00:00",
    "total_weekly_hours_goal": 5,
    "break_frequency": 50,
    "break_duration": 10,
}

SAMPLE_CLASSES = [
    {
        "class_id": 101,
        "class_name": "CSC 603 - Generative AI",
        "class_start_time": "14:00:00",
        "class_end_time": "15:15:00",
        "class_days": ["Tuesday", "Thursday"],
        "priority_level": 5,
        "syllabus_url": "https://example.com/syllabi/csc603.pdf",
        "is_completed": False,
    }
]

SAMPLE_REQUEST = {"user": SAMPLE_USER, "classes": SAMPLE_CLASSES}


# A complete, valid AI response (Schema 3) used by the happy-path test
FAKE_AI_RESPONSE = json.dumps(
    [
        {
            "id": 1,
            "type": "study",
            "class_name": "CSC 603 - Generative AI",
            "start_time": "2025-07-07T08:00:00",
            "end_time": "2025-07-07T08:50:00",
        },
        {
            "id": 2,
            "type": "break",
            "class_name": "Rest",
            "start_time": "2025-07-07T08:50:00",
            "end_time": "2025-07-07T09:00:00",
        },
    ]
)


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────


def test_health_check_returns_ok():
    response = client.get("/")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Lumina API"
    assert "hf_token_configured" in body


# ─────────────────────────────────────────────
# Pydantic validation (Schema 1 & 2 enforcement)
# ─────────────────────────────────────────────


def test_missing_user_fields_returns_422():
    """
    Empty user object should fail because total_weekly_hours_goal is the
    only field without a server-side default.
    """
    response = client.post(
        "/generate-schedule", json={"user": {}, "classes": []}
    )
    assert response.status_code == 422

    error_locs = {tuple(e["loc"]) for e in response.json()["detail"]}
    assert ("body", "user", "total_weekly_hours_goal") in error_locs


def test_invalid_priority_level_returns_422():
    """priority_level outside 1-5 should fail validation."""
    bad_classes = [{**SAMPLE_CLASSES[0], "priority_level": 99}]
    response = client.post(
        "/generate-schedule", json={"user": SAMPLE_USER, "classes": bad_classes}
    )
    assert response.status_code == 422


def test_completely_empty_body_returns_422():
    response = client.post("/generate-schedule", json={})
    assert response.status_code == 422


# ─────────────────────────────────────────────
# Token / config errors
# ─────────────────────────────────────────────


def test_missing_token_returns_helpful_500(monkeypatch):
    """Without HF_API_TOKEN we should get a clear 500 with guidance."""
    monkeypatch.delenv("HF_API_TOKEN", raising=False)

    response = client.post("/generate-schedule", json=SAMPLE_REQUEST)
    assert response.status_code == 500
    assert "HF_API_TOKEN" in response.json()["detail"]
    assert ".env" in response.json()["detail"]


# ─────────────────────────────────────────────
# Happy path — AI call mocked
# ─────────────────────────────────────────────


def test_happy_path_returns_schedule_and_warnings(monkeypatch):
    """A successful AI call should return a parsed schedule + warnings list."""
    monkeypatch.setenv("HF_API_TOKEN", "fake-token-for-testing")

    with patch("main.lumina_ai.call_huggingface", return_value=FAKE_AI_RESPONSE):
        response = client.post("/generate-schedule", json=SAMPLE_REQUEST)

    assert response.status_code == 200

    body = response.json()
    assert "schedule" in body
    assert "warnings" in body
    assert isinstance(body["schedule"], list)
    assert isinstance(body["warnings"], list)
    assert len(body["schedule"]) == 2

    # Block shape matches Schema 3
    block = body["schedule"][0]
    assert block["type"] == "study"
    assert block["class_name"] == "CSC 603 - Generative AI"
    assert "T" in block["start_time"]  # ISO 8601


def test_happy_path_break_block_has_rest_class_name(monkeypatch):
    monkeypatch.setenv("HF_API_TOKEN", "fake-token-for-testing")

    with patch("main.lumina_ai.call_huggingface", return_value=FAKE_AI_RESPONSE):
        response = client.post("/generate-schedule", json=SAMPLE_REQUEST)

    body = response.json()
    break_blocks = [b for b in body["schedule"] if b["type"] == "break"]
    assert len(break_blocks) == 1
    assert break_blocks[0]["class_name"] == "Rest"


# ─────────────────────────────────────────────
# Failure modes
# ─────────────────────────────────────────────


def test_ai_call_failure_returns_502(monkeypatch):
    """If the underlying HF call raises, we surface it as a 502."""
    monkeypatch.setenv("HF_API_TOKEN", "fake-token-for-testing")

    with patch(
        "main.lumina_ai.call_huggingface",
        side_effect=RuntimeError("HuggingFace API down"),
    ):
        response = client.post("/generate-schedule", json=SAMPLE_REQUEST)

    assert response.status_code == 502
    assert "AI generation failed" in response.json()["detail"]


def test_truncated_json_recovers(monkeypatch):
    """
    The AI script's extract_json has truncation recovery for cases where
    max_tokens cuts the array off mid-stream. Verify we still get a usable
    schedule when that happens.
    """
    monkeypatch.setenv("HF_API_TOKEN", "fake-token-for-testing")

    truncated = (
        '[\n'
        '  {"id": 1, "type": "study", "class_name": "CSC 603", '
        '"start_time": "2025-07-07T08:00:00", '
        '"end_time": "2025-07-07T08:50:00"},\n'
        '  {"id": 2, "type": "break", "class_name": "Rest", '
        '"start_time": "2025-07-07T08:50:00", '
        '"end_time": "2025-07-07T09:00:00"'  # missing closing }, ], etc
    )

    with patch("main.lumina_ai.call_huggingface", return_value=truncated):
        response = client.post("/generate-schedule", json=SAMPLE_REQUEST)

    assert response.status_code == 200
    assert len(response.json()["schedule"]) >= 1


def test_non_array_response_returns_502(monkeypatch):
    """If the model returns a JSON object instead of array, we 502."""
    monkeypatch.setenv("HF_API_TOKEN", "fake-token-for-testing")

    with patch(
        "main.lumina_ai.call_huggingface",
        return_value='{"error": "I cannot do that"}',
    ):
        response = client.post("/generate-schedule", json=SAMPLE_REQUEST)

    assert response.status_code == 502


# ─────────────────────────────────────────────
# Server-side defaults (for the frontend's minimal payload)
# ─────────────────────────────────────────────


def test_minimal_payload_succeeds(monkeypatch):
    """
    Frontend should be able to send just total_weekly_hours_goal +
    class_name and have the server fill in the rest.
    """
    monkeypatch.setenv("HF_API_TOKEN", "fake-token-for-testing")

    payload = {
        "user": {"total_weekly_hours_goal": 5},
        "classes": [{"class_name": "CSC 603"}],
    }

    with patch("main.lumina_ai.call_huggingface", return_value=FAKE_AI_RESPONSE):
        response = client.post("/generate-schedule", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["schedule"], list)
    assert len(body["schedule"]) == 2


def test_missing_total_weekly_hours_returns_422():
    """total_weekly_hours_goal has no default — omitting it must fail."""
    response = client.post(
        "/generate-schedule",
        json={"user": {}, "classes": [{"class_name": "CSC 603"}]},
    )
    assert response.status_code == 422

    error_locs = {tuple(e["loc"]) for e in response.json()["detail"]}
    assert ("body", "user", "total_weekly_hours_goal") in error_locs


def test_class_ids_auto_assigned(monkeypatch):
    """
    Classes submitted without class_id should get sequential 1, 2, 3...
    by the time they reach the AI helpers.
    """
    monkeypatch.setenv("HF_API_TOKEN", "fake-token-for-testing")

    payload = {
        "user": {"total_weekly_hours_goal": 5},
        "classes": [
            {"class_name": "CSC 603"},
            {"class_name": "CSC 510"},
        ],
    }

    captured = {}

    def fake_build_messages(_user, classes, week_start=None):
        captured["classes"] = classes
        return []  # call_huggingface is mocked, so this return value is unused

    with patch(
        "main.lumina_ai.build_messages", side_effect=fake_build_messages
    ), patch("main.lumina_ai.call_huggingface", return_value=FAKE_AI_RESPONSE):
        response = client.post("/generate-schedule", json=payload)

    assert response.status_code == 200
    assert len(captured["classes"]) == 2
    assert captured["classes"][0]["class_id"] == 1
    assert captured["classes"][1]["class_id"] == 2


# ─────────────────────────────────────────────
# Date handling — week start is computed from today, not hardcoded
# ─────────────────────────────────────────────


def test_uses_current_week_dates(monkeypatch):
    """
    The system prompt's date range should reflect the current calendar
    week, not the hardcoded 2025-07-07 week from the original AI script.
    """
    monkeypatch.setenv("HF_API_TOKEN", "fake-token-for-testing")

    captured_messages = []

    def capture_then_respond(messages):
        captured_messages.append(messages)
        return FAKE_AI_RESPONSE

    fixed_today = date(2026, 5, 11)  # a Monday

    with patch("main.date") as mock_date:
        mock_date.today.return_value = fixed_today
        with patch(
            "main.lumina_ai.call_huggingface",
            side_effect=capture_then_respond,
        ):
            response = client.post("/generate-schedule", json=SAMPLE_REQUEST)

    assert response.status_code == 200
    assert len(captured_messages) == 1

    system_prompt = captured_messages[0][0]["content"]
    assert "2026-05-11" in system_prompt
    assert "2026-05-15" in system_prompt
    # And, for the avoidance of doubt, the old hardcoded date is gone.
    assert "2025-07-07" not in system_prompt


def test_different_today_produces_different_dates(monkeypatch):
    """
    Two requests on different 'todays' should produce two different
    system prompts — proving the week range is computed, not hardcoded.
    """
    monkeypatch.setenv("HF_API_TOKEN", "fake-token-for-testing")

    captured_prompts = []

    def capture(messages):
        captured_prompts.append(messages[0]["content"])
        return FAKE_AI_RESPONSE

    for fixed_today in [date(2026, 5, 11), date(2026, 5, 18)]:
        with patch("main.date") as mock_date:
            mock_date.today.return_value = fixed_today
            with patch(
                "main.lumina_ai.call_huggingface", side_effect=capture
            ):
                response = client.post(
                    "/generate-schedule", json=SAMPLE_REQUEST
                )
            assert response.status_code == 200

    assert len(captured_prompts) == 2
    assert captured_prompts[0] != captured_prompts[1]
    assert "2026-05-11" in captured_prompts[0]
    assert "2026-05-18" in captured_prompts[1]
