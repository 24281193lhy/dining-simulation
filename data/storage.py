import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

class SimulationStorage:
    """仿真数据存储：事件日志、状态快照、统计结果输出"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        self.event_log_path = os.path.join(log_dir, "events.jsonl")
        self.snapshot_log_path = os.path.join(log_dir, "snapshots.jsonl")

        self._events: List[Dict] = []      # 内存缓存
        self._snapshots: List[Dict] = []

    # ---------- 事件记录 ----------
    def log_event(self, event_type: str, user_id: str, detail: str, timestamp: Optional[float] = None):
        """记录单个事件，自动附加时间戳"""
        ts = timestamp if timestamp is not None else datetime.now().timestamp()
        event = {
            "timestamp": ts,
            "event_type": event_type,
            "user_id": user_id,
            "detail": detail
        }
        self._events.append(event)
        self._append_jsonl(self.event_log_path, event)

    def _append_jsonl(self, path: str, data: Dict):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    # ---------- 状态快照 ----------
    def save_snapshot(self, time: float, windows_status: Dict, seats_status: Dict, queues_length: Dict):
        """
        保存仿真时刻的快照
        :param time: 当前仿真时间（分钟）
        :param windows_status: {window_global_id: {"serving": user_id或None, "total_served": int}}
        :param seats_status: {canteen_id: {"total": int, "occupied": int}}
        :param queues_length: {window_global_id: queue_length}
        """
        snapshot = {
            "time": time,
            "windows": windows_status,
            "seats": seats_status,
            "queues": queues_length
        }
        self._snapshots.append(snapshot)
        self._append_jsonl(self.snapshot_log_path, snapshot)

    # ---------- 数据加载 ----------
    def load_events(self) -> List[Dict]:
        """从文件加载所有事件（若内存为空则读取文件）"""
        if not self._events and os.path.exists(self.event_log_path):
            with open(self.event_log_path, 'r', encoding='utf-8') as f:
                self._events = [json.loads(line) for line in f if line.strip()]
        return self._events

    def load_snapshots(self) -> List[Dict]:
        if not self._snapshots and os.path.exists(self.snapshot_log_path):
            with open(self.snapshot_log_path, 'r', encoding='utf-8') as f:
                self._snapshots = [json.loads(line) for line in f if line.strip()]
        return self._snapshots

    # ---------- 统计输出 ----------
    def export_statistics(self, stats: Dict, output_file: str = "stats.json"):
        path = os.path.join(self.log_dir, output_file)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"📊 统计结果已导出至 {path}")

    def get_statistics(self) -> Dict:
        """供 UI 实时调用的简易统计（实际由 StatisticsAnalyzer 计算后更新）"""
        return {
            "avg_wait_time": 0,
            "window_busy_rate": "0%",
            "peak_hours": "暂无",
            "total_served": 0
        }