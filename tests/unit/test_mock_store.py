from app.rag.mock_store import MockVectorDB


def test_connection_pool_alert_matches_pool_playbook():
    result = MockVectorDB().search("Help! Database-Cluster reports connection pool exhausted!")

    assert result is not None
    assert result["id"] == "playbook-01"


def test_disk_alert_matches_database_disk_playbook():
    result = MockVectorDB().search("disk_utilization_percent > 95%")

    assert result is not None
    assert result["id"] == "playbook-05"


def test_unrelated_message_returns_no_playbook():
    assert MockVectorDB().search("Transaction completed successfully") is None
