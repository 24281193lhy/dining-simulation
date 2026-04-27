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
        """准备包含特定场景数据的存储实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SimulationStorage(log_dir=tmpdir)

            # 场景：学生 S001 等待了 5 分钟，S002 等待了 6 分钟
            # 注意：使用更新后的事件名 "serve_finished"
            storage.log_event("queue_join", "S001", "window1", timestamp=0.0)
            storage.log_event("serve_finished", "S001", "window1", timestamp=5.0)

            storage.log_event("queue_join", "S002", "window1", timestamp=2.0)
            storage.log_event("serve_finished", "S002", "window1", timestamp=8.0)

            # 构造跨度为 10 分钟的快照
            storage.save_snapshot(0.0, {"1_1": {"serving": None, "total_served": 0}},
                                  {1: {"total": 100, "occupied": 10}}, {"1_1": 1})
            storage.save_snapshot(10.0, {"1_1": {"serving": None, "total_served": 2}},
                                  {1: {"total": 100, "occupied": 20}}, {"1_1": 0})
            yield storage

    def test_average_wait_time(self, sample_storage):
        """测试平均等待时间计算：(5 + 6) / 2 = 5.5"""
        analyzer = StatisticsAnalyzer(sample_storage)
        avg = analyzer.average_wait_time()
        assert abs(avg - 5.5) < 0.01

    def test_total_served_with_new_event_name(self, sample_storage):
        """测试总服务人数统计是否识别新的 serve_finished 事件名"""
        analyzer = StatisticsAnalyzer(sample_storage)
        served = analyzer.total_served()
        assert served == 2

    def test_window_busy_rate(self, sample_storage):
        """测试窗口繁忙度：2人 / 10分钟 = 0.2"""
        analyzer = StatisticsAnalyzer(sample_storage)
        rates = analyzer.window_busy_rate()
        assert abs(rates.get("1_1", 0) - 0.2) < 0.01

    def test_peak_hours_identification(self, sample_storage):
        """测试高峰时段识别"""
        analyzer = StatisticsAnalyzer(sample_storage)
        peaks = analyzer.peak_hours(interval_minutes=30)
        # 由于我们只有 0-10 分钟的数据，它应该落在第一个时间段
        assert len(peaks) > 0
        assert peaks[0]["start_time"] == 0

    def test_average_seat_occupancy(self, sample_storage):
        """测试座位占用率：(10% + 20%) / 2 = 15%"""
        analyzer = StatisticsAnalyzer(sample_storage)
        occupancy = analyzer.average_seat_occupancy()
        assert abs(occupancy.get(1, 0) - 15.0) < 0.01

    def test_compute_all_integration(self, sample_storage):
        """测试 compute_all 是否返回所有必需的键"""
        analyzer = StatisticsAnalyzer(sample_storage)
        all_stats = analyzer.compute_all()
        required_keys = ["avg_wait_time", "window_busy_rate", "peak_hours", "total_served", "avg_seat_occupancy"]
        for key in required_keys:
            assert key in all_stats, f"统计结果中缺少关键指标: {key}"
