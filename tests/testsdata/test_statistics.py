import tempfile

import pytest

from data import SimulationStorage, StatisticsAnalyzer


class TestStatisticsAnalyzer:
    @pytest.fixture
    def sample_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SimulationStorage(log_dir=tmpdir)
            storage.log_event("queue_join", "S001", "window1", timestamp=0.0)
            storage.log_event("serve_finished", "S001", "window1", timestamp=5.0)
            storage.log_event("queue_join", "S002", "window1", timestamp=2.0)
            storage.log_event("serve_finished", "S002", "window1", timestamp=8.0)
            storage.save_snapshot(
                0.0,
                {"1_1": {"serving": None, "total_served": 0}},
                {1: {"total": 100, "occupied": 10}},
                {"1_1": 1},
            )
            storage.save_snapshot(
                10.0,
                {"1_1": {"serving": None, "total_served": 2}},
                {1: {"total": 100, "occupied": 20}},
                {"1_1": 0},
            )
            yield storage
            storage.close()

    def test_average_wait_time(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        assert abs(analyzer.average_wait_time() - 5.5) < 0.01

    def test_total_served_with_new_event_name(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        assert analyzer.total_served() == 2

    def test_window_busy_rate(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        rates = analyzer.window_busy_rate()
        assert abs(rates.get("1_1", 0) - 0.2) < 0.01

    def test_peak_hours_identification(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        peaks = analyzer.peak_hours(interval_minutes=30)
        assert len(peaks) > 0
        assert peaks[0]["start_time"] == 0

    def test_average_seat_occupancy(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        occupancy = analyzer.average_seat_occupancy()
        assert abs(occupancy.get(1, 0) - 15.0) < 0.01

    def test_compute_all_integration(self, sample_storage):
        analyzer = StatisticsAnalyzer(sample_storage)
        all_stats = analyzer.compute_all()
        required_keys = [
            "avg_wait_time",
            "window_busy_rate",
            "peak_hours",
            "total_served",
            "avg_seat_occupancy",
            "window_summary",
            "queue_summary",
            "seat_summary",
            "event_count_by_type",
            "latest_snapshot_time",
        ]
        for key in required_keys:
            assert key in all_stats, f"统计结果中缺少关键指标: {key}"
