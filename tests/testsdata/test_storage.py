import json
import os
import tempfile

import pytest

from data import SimulationStorage


class TestSimulationStorage:
    @pytest.fixture
    def temp_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SimulationStorage(log_dir=tmpdir)
            yield storage
            storage.close()

    def test_log_event_basic(self, temp_storage):
        temp_storage.log_event("queue_join", "S2024001", "在窗口1排队")
        events = temp_storage.load_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "queue_join"
        assert events[0]["user_id"] == "S2024001"
        assert "timestamp" in events[0]

    def test_batch_writing(self, temp_storage):
        for i in range(10):
            temp_storage.log_event("test_event", f"user_{i}", "detail")
        with open(temp_storage.event_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 0
        assert len(temp_storage._events) == 10

    def test_save_and_load_snapshot(self, temp_storage):
        temp_storage.save_snapshot(
            time=10.0,
            windows_status={"1_1": {"serving": None, "total_served": 5}},
            seats_status={1: {"total": 100, "occupied": 20}},
            queues_length={"1_1": 3},
        )
        snaps = temp_storage.load_snapshots()
        assert len(snaps) == 1
        assert snaps[0]["time"] == 10.0
        assert snaps[0]["queues"]["1_1"] == 3

    def test_close_persists_data(self, temp_storage):
        temp_storage.log_event("serve_finished", "S001", "完成服务")
        temp_storage.close()
        new_storage = SimulationStorage(log_dir=temp_storage.log_dir)
        events = new_storage.load_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "serve_finished"

    def test_export_statistics(self, temp_storage):
        stats = {"avg_wait_time": 2.5, "total_served": 100}
        temp_storage.export_statistics(stats, output_file="out.json")
        file_path = os.path.join(temp_storage.log_dir, "out.json")
        assert os.path.exists(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["avg_wait_time"] == 2.5
        assert temp_storage.get_statistics()["total_served"] == 100

    def test_reset_clears_all(self, temp_storage):
        temp_storage.log_event("test", "u1", "d1")
        temp_storage.reset()
        assert len(temp_storage._events) == 0
        assert len(temp_storage._event_buffer) == 0
        assert temp_storage._latest_stats == {}
