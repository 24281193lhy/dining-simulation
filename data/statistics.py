"""仿真统计分析模块。

基于 SimulationStorage 中保存的事件日志和状态快照，计算等待时间、服务人数、
窗口繁忙度、排队高峰、座位占用率等指标。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple


class StatisticsAnalyzer:
    """基于存储的事件和快照进行统计分析。"""

    SERVE_FINISHED_EVENTS = {"serve_finished", "serve_done", "service_finished", "service_complete"}
    QUEUE_JOIN_EVENTS = {"queue_join", "join_queue"}

    def __init__(self, storage):
        self.storage = storage
        self.events = storage.load_events()
        self.snapshots = storage.load_snapshots()

    # ---------- 对外总入口 ----------
    def compute_all(self) -> Dict[str, Any]:
        """计算 Web/UI/报告常用的完整统计指标。"""
        stats = {
            "avg_wait_time": self.average_wait_time(),
            "window_busy_rate": self.window_busy_rate(),
            "peak_hours": self.peak_hours(),
            "total_served": self.total_served(),
            "avg_seat_occupancy": self.average_seat_occupancy(),
            "window_summary": self.window_summary(),
            "queue_summary": self.queue_summary(),
            "seat_summary": self.seat_summary(),
            "event_count_by_type": self.event_count_by_type(),
            "latest_snapshot_time": self.latest_snapshot_time(),
        }

        if hasattr(self.storage, "update_statistics"):
            self.storage.update_statistics(stats)
        return stats

    # ---------- 基础辅助方法 ----------
    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_int_key(value: Any) -> Any:
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    @classmethod
    def _is_queue_join(cls, event: Dict[str, Any]) -> bool:
        return event.get("event_type") in cls.QUEUE_JOIN_EVENTS

    @classmethod
    def _is_serve_finished(cls, event: Dict[str, Any]) -> bool:
        return event.get("event_type") in cls.SERVE_FINISHED_EVENTS

    @staticmethod
    def _event_time(event: Dict[str, Any]) -> Optional[float]:
        if "timestamp" in event:
            return StatisticsAnalyzer._to_float(event.get("timestamp"))
        if "time" in event:
            return StatisticsAnalyzer._to_float(event.get("time"))
        return None

    @staticmethod
    def _queue_values(snapshot: Dict[str, Any]) -> List[float]:
        queues = snapshot.get("queues") or {}
        if not isinstance(queues, dict):
            return []
        return [StatisticsAnalyzer._to_float(v) for v in queues.values()]

    @staticmethod
    def _snapshot_time_range(snapshots: List[Dict[str, Any]]) -> float:
        if len(snapshots) < 2:
            return 0.0
        start = StatisticsAnalyzer._to_float(snapshots[0].get("time"))
        end = StatisticsAnalyzer._to_float(snapshots[-1].get("time"))
        return max(0.0, end - start)

    # ---------- 核心指标 ----------
    def average_wait_time(self) -> float:
        """计算平均排队等待时间（分钟）。

        采用 user_id 维度的先进先出匹配：queue_join -> serve_finished。
        """
        wait_times: List[float] = []
        join_times: Dict[str, List[float]] = defaultdict(list)

        for event in self.events:
            user_id = str(event.get("user_id", ""))
            event_time = self._event_time(event)
            if not user_id or event_time is None:
                continue

            if self._is_queue_join(event):
                join_times[user_id].append(event_time)
            elif self._is_serve_finished(event) and join_times[user_id]:
                start_time = join_times[user_id].pop(0)
                wait = event_time - start_time
                if wait >= 0:
                    wait_times.append(wait)

        return round(sum(wait_times) / len(wait_times), 2) if wait_times else 0.0

    def window_busy_rate(self) -> Dict[str, float]:
        """各窗口繁忙度 = 服务人数增量 / 仿真时间跨度。"""
        if len(self.snapshots) < 2:
            return {}

        total_time = self._snapshot_time_range(self.snapshots)
        if total_time <= 0:
            return {}

        first_windows = self.snapshots[0].get("windows") or {}
        last_windows = self.snapshots[-1].get("windows") or {}
        rates: Dict[str, float] = {}

        for win_id, last_data in last_windows.items():
            first_data = first_windows.get(win_id, {}) if isinstance(first_windows, dict) else {}
            first_served = self._to_float(first_data.get("total_served", 0)) if isinstance(first_data, dict) else 0.0
            last_served = self._to_float(last_data.get("total_served", 0)) if isinstance(last_data, dict) else 0.0
            served_delta = max(0.0, last_served - first_served)
            rates[str(win_id)] = round(served_delta / total_time, 4)

        return rates

    def peak_hours(self, interval_minutes: int = 30, top_n: int = 3) -> List[Dict[str, Any]]:
        """识别排队高峰时段，按时间段聚合最大排队人数。"""
        if not self.snapshots:
            return []

        interval = max(1, int(interval_minutes))
        bins: Dict[int, int] = defaultdict(int)

        for snap in self.snapshots:
            current_time = self._to_float(snap.get("time"))
            bin_key = int(current_time // interval) * interval
            total_queue = int(sum(self._queue_values(snap)))
            bins[bin_key] = max(bins[bin_key], total_queue)

        sorted_peaks = sorted(bins.items(), key=lambda item: item[1], reverse=True)
        return [
            {"start_time": t, "end_time": t + interval, "queue_length": q}
            for t, q in sorted_peaks[:top_n]
        ]

    def total_served(self) -> int:
        """总服务人数。"""
        return sum(1 for event in self.events if self._is_serve_finished(event))

    def average_seat_occupancy(self) -> Dict[Any, float]:
        """各食堂平均座位占用率，单位为百分比。"""
        canteen_rates: Dict[Any, List[float]] = defaultdict(list)

        for snap in self.snapshots:
            seats = snap.get("seats") or {}
            if not isinstance(seats, dict):
                continue

            for canteen_id, seat_data in seats.items():
                if not isinstance(seat_data, dict):
                    continue
                total = self._to_float(seat_data.get("total"))
                occupied = self._to_float(seat_data.get("occupied"))
                if total <= 0:
                    continue
                rate = occupied / total * 100
                canteen_rates[self._to_int_key(canteen_id)].append(rate)

        return {
            canteen_id: round(sum(rates) / len(rates), 2)
            for canteen_id, rates in canteen_rates.items()
            if rates
        }

    # ---------- 扩展指标：用于报告和仪表盘 ----------
    def window_summary(self) -> Dict[str, Dict[str, Any]]:
        """按窗口汇总服务数、平均队长、最大队长和繁忙度。"""
        if not self.snapshots:
            return {}

        queue_records: Dict[str, List[float]] = defaultdict(list)
        for snap in self.snapshots:
            queues = snap.get("queues") or {}
            if isinstance(queues, dict):
                for win_id, queue_len in queues.items():
                    queue_records[str(win_id)].append(self._to_float(queue_len))

        latest_windows = self.snapshots[-1].get("windows") or {}
        busy_rates = self.window_busy_rate()
        summary: Dict[str, Dict[str, Any]] = {}

        for win_id, win_data in latest_windows.items():
            win_key = str(win_id)
            queues = queue_records.get(win_key, [])
            total_served = 0
            if isinstance(win_data, dict):
                total_served = int(self._to_float(win_data.get("total_served", 0)))

            summary[win_key] = {
                "total_served": total_served,
                "avg_queue_length": round(sum(queues) / len(queues), 2) if queues else 0.0,
                "max_queue_length": int(max(queues)) if queues else 0,
                "busy_rate": busy_rates.get(win_key, 0.0),
            }

        return summary

    def queue_summary(self) -> Dict[str, Any]:
        """整体队列统计。"""
        total_queue_by_snapshot = [sum(self._queue_values(snap)) for snap in self.snapshots]
        if not total_queue_by_snapshot:
            return {"avg_total_queue": 0.0, "max_total_queue": 0, "snapshots_count": 0}

        return {
            "avg_total_queue": round(sum(total_queue_by_snapshot) / len(total_queue_by_snapshot), 2),
            "max_total_queue": int(max(total_queue_by_snapshot)),
            "snapshots_count": len(self.snapshots),
        }

    def seat_summary(self) -> Dict[Any, Dict[str, Any]]:
        """按食堂汇总平均、最高和最新座位占用率。"""
        records: Dict[Any, List[float]] = defaultdict(list)
        latest: Dict[Any, float] = {}

        for snap in self.snapshots:
            seats = snap.get("seats") or {}
            if not isinstance(seats, dict):
                continue
            for canteen_id, seat_data in seats.items():
                if not isinstance(seat_data, dict):
                    continue
                total = self._to_float(seat_data.get("total"))
                occupied = self._to_float(seat_data.get("occupied"))
                if total <= 0:
                    continue
                key = self._to_int_key(canteen_id)
                rate = occupied / total * 100
                records[key].append(rate)
                latest[key] = rate

        return {
            canteen_id: {
                "avg_occupancy": round(sum(rates) / len(rates), 2),
                "max_occupancy": round(max(rates), 2),
                "latest_occupancy": round(latest.get(canteen_id, 0.0), 2),
            }
            for canteen_id, rates in records.items()
            if rates
        }

    def event_count_by_type(self) -> Dict[str, int]:
        """统计各类事件数量。"""
        counter = Counter(str(event.get("event_type", "unknown")) for event in self.events)
        return dict(counter)

    def latest_snapshot_time(self) -> Optional[float]:
        """返回最新快照时间。"""
        if not self.snapshots:
            return None
        return self._to_float(self.snapshots[-1].get("time"))
