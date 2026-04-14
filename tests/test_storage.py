import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import tempfile
import pytest
from data.storage import SimulationStorage

class TestSimulationStorage:
    @pytest.fixture
    def temp_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SimulationStorage(log_dir=tmpdir)
            yield storage

    def test_log_event(self, temp_storage):
        temp_storage.log_event("queue_join", "S2024001", "window_1_1")
        events = temp_storage.load_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "queue_join"
        assert events[0]["user_id"] == "S2024001"

    def test_save_and_load_snapshot(self, temp_storage):
        temp_storage.save_snapshot(
            time=10.0,
            windows_status={"1_1": {"serving": None, "total_served": 5}},
            seats_status={1: {"total": 100, "occupied": 20}},
            queues_length={"1_1": 3}
        )
        snaps = temp_storage.load_snapshots()
        assert len(snaps) == 1
        assert snaps[0]["time"] == 10.0
        assert snaps[0]["queues"]["1_1"] == 3

    def test_export_statistics(self, temp_storage):
        stats = {"avg_wait_time": 2.5, "total_served": 100}
        temp_storage.export_statistics(stats, output_file="out.json")
        file_path = os.path.join(temp_storage.log_dir, "out.json")
        assert os.path.exists(file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data["avg_wait_time"] == 2.5