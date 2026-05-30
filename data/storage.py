import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional


class SimulationStorage:
    """仿真数据存储：事件日志、状态快照、统计结果输出（线程安全）"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        self.event_log_path = os.path.join(log_dir, "events.jsonl")
        self.snapshot_log_path = os.path.join(log_dir, "snapshots.jsonl")

        self._events: List[Dict] = []
        self._snapshots: List[Dict] = []
        self._lock = threading.Lock()

        # 每次创建新存储时清空旧日志，确保仿真从零开始
        self._clear_file(self.event_log_path)
        self._clear_file(self.snapshot_log_path)

    def _clear_file(self, path: str):
        """清空文件内容（修复 2）"""
        if os.path.exists(path):
            open(path, 'w').close()

    # ---------- 事件记录 ----------
    def log_event(self, event_type: str, user_id: str, detail: str,
                  timestamp: Optional[float] = None):
        ts = timestamp if timestamp is not None else datetime.now().timestamp()
        event = {
            "timestamp": ts,
            "event_type": event_type,
            "user_id": user_id,
            "detail": detail
        }
        with self._lock:                          # 修复 1：加锁
            self._events.append(event)
            self._append_jsonl(self.event_log_path, event)

    def _append_jsonl(self, path: str, data: Dict):
        """调用方已持有 self._lock"""
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    # ---------- 状态快照 ----------
    def save_snapshot(self, time: float, windows_status: Dict,
                      seats_status: Dict, queues_length: Dict):
        snapshot = {
            "time": time,
            "windows": windows_status,
            "seats": seats_status,
            "queues": queues_length
        }
        with self._lock:                          # 修复 1：加锁
            self._snapshots.append(snapshot)
            self._append_jsonl(self.snapshot_log_path, snapshot)

    # ---------- 数据加载 ----------
    def load_events(self) -> List[Dict]:
        with self._lock:                          # 修复 1：读前加锁
            if not self._events and os.path.exists(self.event_log_path):
                with open(self.event_log_path, 'r', encoding='utf-8') as f:
                    self._events = [json.loads(line) for line in f if line.strip()]
            return list(self._events)             # 返回副本，防止外部意外修改

    def load_snapshots(self) -> List[Dict]:
        with self._lock:
            if not self._snapshots and os.path.exists(self.snapshot_log_path):
                with open(self.snapshot_log_path, 'r', encoding='utf-8') as f:
                    self._snapshots = [json.loads(line) for line in f if line.strip()]
            return list(self._snapshots)

    # ---------- 统计输出 ----------
    def export_statistics(self, stats: Dict, output_file: str = "stats.json"):
        path = os.path.join(self.log_dir, output_file)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        # print 已注释，避免 Web 服务刷屏

    def get_statistics(self) -> Dict:
        """供 UI 实时调用的简易统计（实际由 StatisticsAnalyzer 提供）"""
        return {
            "avg_wait_time": 0,
            "window_busy_rate": "0%",
            "peak_hours": "暂无",
            "total_served": 0
        }

#A