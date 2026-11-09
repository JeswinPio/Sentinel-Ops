import json
import logging

from app.observability.logging import JsonFormatter, request_id_var


def _record(message: str, **extra) -> logging.LogRecord:
    record = logging.makeLogRecord({"name": "sentinel.test", "levelname": "INFO", "msg": message})
    record.__dict__.update(extra)
    return record


def test_json_formatter_emits_spec_fields_and_extras():
    entry = json.loads(JsonFormatter().format(_record("playbook.retrieved", incident_id="inc-1", confidence=0.94)))

    assert entry["service"] == "sentinel-ops"
    assert entry["level"] == "INFO"
    assert entry["event"] == "playbook.retrieved"
    assert entry["incident_id"] == "inc-1"
    assert entry["confidence"] == 0.94
    assert "timestamp" in entry


def test_json_formatter_includes_current_request_id():
    token = request_id_var.set("req-42")
    try:
        entry = json.loads(JsonFormatter().format(_record("incident.created")))
    finally:
        request_id_var.reset(token)

    assert entry["request_id"] == "req-42"
