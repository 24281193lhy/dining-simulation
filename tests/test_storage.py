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
        """提供一个临时的存储实例，测试结束后自动清理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SimulationStorage(log_dir=tmpdir)
            yield storage

    def test_log_event_basic(self, temp_storage):
        """测试基本的事件记录功能"""
        temp_storage.log_event("queue_join", "S2024001", "在窗口1排队")
        events = temp_storage.load_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "queue_join"
        assert events[0]["user_id"] == "S2024001"
        assert "timestamp" in events[0]

    def test_batch_writing(self, temp_storage):
        """测试批量写入机制：未满50条时不应立即写入文件"""
        # 记录 10 条事件
        for i in range(10):
            temp_storage.log_event("test_event", f"user_{i}", "detail")

        # 此时内存中应该有，但文件中可能还没有（取决于是否触发 flush）
        # 我们手动检查文件内容来验证批量逻辑
        with open(temp_storage.event_log_path, 'r') as f:
            lines = f.readlines()
        # 因为 BATCH_SIZE 是 50，这里应该还是 0 行
        assert len(lines) == 0
        assert len(temp_storage._events) == 10

    def test_save_and_load_snapshot(self, temp_storage):
        """测试快照的保存与加载"""
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

    def test_close_persists_data(self, temp_storage):
        """测试 close 方法是否能将缓冲区剩余数据刷入硬盘"""
        temp_storage.log_event("serve_finished", "S001", "完成服务")
        # 调用 close 强制刷新
        temp_storage.close()

        # 重新创建一个实例读取文件，验证持久化
        new_storage = SimulationStorage(log_dir=temp_storage.log_dir)
        events = new_storage.load_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "serve_finished"

    def test_export_statistics(self, temp_storage):
        """测试统计结果导出为 JSON 文件"""
        stats = {"avg_wait_time": 2.5, "total_served": 100}
        temp_storage.export_statistics(stats, output_file="out.json")
        file_path = os.path.join(temp_storage.log_dir, "out.json")
        assert os.path.exists(file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data["avg_wait_time"] == 2.5

    def test_reset_clears_all(self, temp_storage):
        """测试重置功能"""
        temp_storage.log_event("test", "u1", "d1")
        temp_storage.reset()
        assert len(temp_storage._events) == 0
        assert len(temp_storage._event_buffer) == 0
        assert temp_storage._latest_stats == {}
