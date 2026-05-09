"""仿真数据存储模块。

负责将仿真过程中的事件日志、状态快照和统计结果保存到本地文件，
同时保留内存缓存，供实时统计和 Web/UI 层快速读取。
"""

from __future__ import annotations

import atexit
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class SimulationStorage:
    """仿真数据存储：事件日志、状态快照、统计结果输出。

    设计目标：
    1. 内存中立即可查，满足仿真过程中的实时统计；
    2. 文件写入使用小批量缓冲，降低频繁 I/O；
    3. 提供 close/flush/reset，便于测试、退出和重新仿真；
    4. 不引入新依赖，保持和现有项目兼容。
    """

    DEFAULT_BATCH_SIZE = 50

    def __init__(self, log_dir: str = "logs", batch_size: int = DEFAULT_BATCH_SIZE):
        self.log_dir = str(log_dir)
        self.batch_size = max(1, int(batch_size))

        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        self.event_log_path = os.path.join(self.log_dir, "events.jsonl")
        self.snapshot_log_path = os.path.join(self.log_dir, "snapshots.jsonl")
        self.statistics_path = os.path.join(self.log_dir, "stats.json")

        self._touch(self.event_log_path)
        self._touch(self.snapshot_log_path)

        self._events: List[Dict[str, Any]] = []
        self._snapshots: List[Dict[str, Any]] = []
        self._event_buffer: List[Dict[str, Any]] = []
        self._snapshot_buffer: List[Dict[str, Any]] = []
        self._latest_stats: Dict[str, Any] = {}
        self._closed = False

        # 主程序目前没有显式调用 close，这里保证正常解释器退出时仍会落盘。
        atexit.register(self.close)

    # ---------- 基础文件工具 ----------
    @staticmethod
    def _touch(path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).touch(exist_ok=True)

    @staticmethod
    def _json_default(obj: Any) -> str:
        """兜底序列化，避免 datetime、Path 等对象导致日志写入中断。"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    def _write_jsonl_many(self, path: str, rows: Iterable[Dict[str, Any]]) -> None:
        self._touch(path)
        with open(path, "a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, default=self._json_default) + "\n")

    def _read_jsonl(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []

        rows: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # 单行日志损坏时跳过，避免整个统计功能崩溃。
                    continue
        return rows

    # ---------- 事件记录 ----------
    def log_event(
        self,
        event_type: str,
        user_id: str,
        detail: Any,
        timestamp: Optional[float] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """记录单个事件，自动附加时间戳并写入缓冲区。

        :param event_type: 事件类型，如 queue_join、serve_finished、seat_occupy。
        :param user_id: 用户编号。
        :param detail: 事件详情，可以是字符串或可 JSON 序列化对象。
        :param timestamp: 仿真时间。若为空，则使用当前真实时间戳。
        :param extra: 额外字段，便于后续扩展。
        :return: 本次生成的事件字典。
        """
        ts = timestamp if timestamp is not None else datetime.now().timestamp()
        event: Dict[str, Any] = {
            "timestamp": ts,
            "event_type": str(event_type),
            "user_id": str(user_id),
            "detail": detail,
        }
        event.update(extra)

        self._events.append(event)
        self._event_buffer.append(event)
        if len(self._event_buffer) >= self.batch_size:
            self.flush_events()
        return event

    def flush_events(self) -> None:
        """将事件缓冲区刷入 events.jsonl。"""
        if not self._event_buffer:
            return
        self._write_jsonl_many(self.event_log_path, self._event_buffer)
        self._event_buffer.clear()

    # ---------- 状态快照 ----------
    def save_snapshot(
        self,
        time: float,
        windows_status: Dict[Any, Any],
        seats_status: Dict[Any, Any],
        queues_length: Dict[Any, Any],
        **extra: Any,
    ) -> Dict[str, Any]:
        """保存仿真时刻的状态快照。

        :param time: 当前仿真时间（分钟）。
        :param windows_status: {window_global_id: {serving, total_served, ...}}
        :param seats_status: {canteen_id: {total, occupied}}
        :param queues_length: {window_global_id: queue_length}
        :return: 本次生成的快照字典。
        """
        snapshot: Dict[str, Any] = {
            "time": time,
            "windows": windows_status or {},
            "seats": seats_status or {},
            "queues": queues_length or {},
        }
        snapshot.update(extra)

        self._snapshots.append(snapshot)
        self._snapshot_buffer.append(snapshot)
        if len(self._snapshot_buffer) >= self.batch_size:
            self.flush_snapshots()
        return snapshot

    def flush_snapshots(self) -> None:
        """将快照缓冲区刷入 snapshots.jsonl。"""
        if not self._snapshot_buffer:
            return
        self._write_jsonl_many(self.snapshot_log_path, self._snapshot_buffer)
        self._snapshot_buffer.clear()

    # ---------- 数据加载 ----------
    def load_events(self, force_reload: bool = False) -> List[Dict[str, Any]]:
        """加载事件。

        默认优先返回内存缓存，避免仿真运行中因为缓冲未落盘而读不到最新数据。
        force_reload=True 时从文件重新读取，适合独立离线分析。
        """
        if force_reload:
            self.flush_events()
            self._events = self._read_jsonl(self.event_log_path)
        elif not self._events:
            self._events = self._read_jsonl(self.event_log_path)
        return list(self._events)

    def load_snapshots(self, force_reload: bool = False) -> List[Dict[str, Any]]:
        """加载状态快照。"""
        if force_reload:
            self.flush_snapshots()
            self._snapshots = self._read_jsonl(self.snapshot_log_path)
        elif not self._snapshots:
            self._snapshots = self._read_jsonl(self.snapshot_log_path)
        return list(self._snapshots)

    # ---------- 统计结果 ----------
    def update_statistics(self, stats: Dict[str, Any]) -> None:
        """更新内存中的最新统计结果，供 UI/API 快速读取。"""
        self._latest_stats = dict(stats or {})

    def export_statistics(self, stats: Dict[str, Any], output_file: str = "stats.json") -> str:
        """导出统计结果为 JSON 文件，并缓存为最新统计结果。

        :return: 导出的文件路径。
        """
        self.update_statistics(stats)
        path = os.path.join(self.log_dir, output_file)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=self._json_default)
        self.statistics_path = path
        return path

    def get_statistics(self) -> Dict[str, Any]:
        """获取当前统计结果。

        若已经通过 export_statistics/update_statistics 写入，则直接返回；
        否则尝试基于当前事件和快照即时计算。
        """
        if self._latest_stats:
            return dict(self._latest_stats)

        try:
            from data.statistics import StatisticsAnalyzer

            stats = StatisticsAnalyzer(self).compute_all()
            self.update_statistics(stats)
            return stats
        except Exception:
            return {
                "avg_wait_time": 0.0,
                "window_busy_rate": {},
                "peak_hours": [],
                "total_served": 0,
                "avg_seat_occupancy": {},
            }

    # ---------- 生命周期管理 ----------
    def flush(self) -> None:
        """将所有缓冲区写入硬盘。"""
        self.flush_events()
        self.flush_snapshots()

    def close(self) -> None:
        """关闭存储对象前强制落盘。可重复调用。"""
        if self._closed:
            return
        self.flush()
        self._closed = True

    def reset(self) -> None:
        """清空内存缓存、缓冲区和当前日志文件。"""
        self._events.clear()
        self._snapshots.clear()
        self._event_buffer.clear()
        self._snapshot_buffer.clear()
        self._latest_stats.clear()
        self._closed = False

        for path in (self.event_log_path, self.snapshot_log_path):
            self._touch(path)
            with open(path, "w", encoding="utf-8"):
                pass

        # 不删除用户自定义统计文件，仅清空默认统计文件路径对应内容。
        if os.path.exists(self.statistics_path):
            try:
                with open(self.statistics_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, ensure_ascii=False)
            except OSError:
                pass
