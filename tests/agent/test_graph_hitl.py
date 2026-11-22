from app.agents.graph import approve_incident, deny_incident, graph, start_incident

CRITICAL_INCIDENT = {
    "timestamp": "2026-08-24T12:00:00",
    "service_name": "postgresql-db-01",
    "severity": "CRITICAL",
    "message": "disk_utilization_percent > 95%",
    "infrastructure_id": "postgresql-db-01",
    "playbook_topic": "Database Disk Capacity Exhaustion",
    "solution": (
        "1. Check database disk usage and identify the largest log files.\n"
        "2. Verify that the identified logs are safe to remove before deletion.\n"
        "3. Remove only eligible old log files to recover disk space.\n"
        "4. Recheck disk utilization and confirm the database has returned to a safe level."
    )
}


def _incident(severity: str) -> dict:
    return {**CRITICAL_INCIDENT, "severity": severity}


def test_critical_incident_pauses_before_hitl():
    result, config = start_incident(CRITICAL_INCIDENT, thread_id="test-critical-pause")

    assert result["status"] == "ANALYZED"
    assert graph.get_state(config).next == ("HITL_CHECKPOINT",)


def test_approval_resumes_to_simulated_execution():
    start_incident(CRITICAL_INCIDENT, thread_id="test-critical-approve")

    result = approve_incident(thread_id="test-critical-approve")

    assert result["status"] == "EXECUTED_SIMULATION"
    assert result["current_node"] == "SIMULATED_EXECUTION_NODE"


def test_denial_escalates_without_execution():
    start_incident(CRITICAL_INCIDENT, thread_id="test-critical-deny")

    result = deny_incident(thread_id="test-critical-deny")

    assert result["status"] == "ESCALATED"
    assert result["current_node"] == "ESCALATION_NODE"


def test_warning_runs_low_risk_path_without_pausing():
    result, config = start_incident(_incident("WARNING"), thread_id="test-warning")

    assert result["status"] == "EXECUTED_SIMULATION"
    assert result["current_node"] == "AUTONOMOUS_LOW_RISK_NODE"
    assert graph.get_state(config).next == ()


def test_info_resolves_without_mutation():
    result, _ = start_incident(_incident("INFO"), thread_id="test-info")

    assert result["status"] == "RESOLVED"
    assert result["current_node"] == "SAFE_RESOLUTION_NODE"
