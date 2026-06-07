# -*- coding: utf-8 -*-
from unittest.mock import patch
from api.services.status_aggregator import get_combined_status


def test_combined_status_merges_running_tasks():
    classic = {
        "status": "running",
        "running_count": 1,
        "queue_length": 2,
        "max_concurrent": 3,
        "running_tasks": [{"task_id": 1, "platform": "xhs", "crawler_type": "search", "started_at": "t", "status": "running"}],
        "platform": "xhs", "crawler_type": "search", "started_at": "t", "error_message": None, "task_id": 1,
    }
    pro = {"running_count": 1, "waiting_count": 1, "running": [{"task_id": 9, "platform": "dy"}], "waiting": []}
    with patch("api.services.status_aggregator.crawler_manager") as mgr:
        mgr.get_status.return_value = classic
        with patch("api.services.status_aggregator._get_pro_status", return_value=pro):
            result = get_combined_status()
    assert result["running_count"] == 2
    assert result["queue_length"] == 3
    assert result["running_tasks"][1]["source"] == "pro"
