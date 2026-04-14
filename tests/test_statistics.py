import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
import pytest
from data.storage import SimulationStorage
from data.statistics import StatisticsAnalyzer

class TestStatisticsAnalyzer:
    @pytest.fixture
    def sample_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SimulationStorage(log_dir=tmpdir)
            # 构造测试数据
            storage.log_event("queue_join", "S001", "window1", timestamp=0.0)
            storage.log_event("queue_serve_done", "S001", "window1", timestamp=5.0)
            storage.log_event("queue_join", "S002", "window1", timestamp=2.0)
            storage.log_event("queue_serve_done", "S002", "window1", timestamp=8.0)
            storage.save_snapshot(0.0, {"1_1": {"serving": None, "total_served": 0}},
                                  {1: {"total": 100, "occupied": 10}}, {"1_1": 1})
            storage.save_snapshot(10.0, {"1_1": {"serving": None, "total_served": 2}},
                                  {1: {"total": 100, "occupied": 20}}, {"1_1": 0})
            yield storage

    def test_average_wait_time(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        avg = analyzer.average_wait_time()
        assert abs(avg - 5.5) < 0.01

    def test_total_served(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        served = analyzer.total_served()
        assert served == 2

    def test_window_busy_rate(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        rates = analyzer.window_busy_rate()
        assert abs(rates.get("1_1", 0) - 0.2) < 0.01

    def test_compute_all(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        all_stats = analyzer.compute_all()
        assert "avg_wait_time" in all_stats
        assert "total_served" in all_stats
        assert all_stats["total_served"] == 2