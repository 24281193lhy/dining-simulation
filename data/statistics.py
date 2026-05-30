from typing import Dict, List
from collections import defaultdict
from data.storage import SimulationStorage

class StatisticsAnalyzer:
    """基于存储的事件和快照进行统计分析（防御性编程）"""

    def __init__(self, storage: SimulationStorage):
        self.storage = storage
        self.events = storage.load_events()
        self.snapshots = storage.load_snapshots()

    def compute_all(self) -> Dict:
        return {
            "avg_wait_time": self.average_wait_time(),
            "window_busy_rate": self.window_busy_rate(),
            "peak_hours": self.peak_hours(),
            "total_served": self.total_served(),
            "avg_seat_occupancy": self.average_seat_occupancy()
        }

    def average_wait_time(self) -> float:
        """计算平均排队等待时间（分钟）"""
        wait_times = []
        join_times: Dict[str, float] = {}

        for event in self.events:
            # 防御：确保必要字段存在
            etype = event.get("event_type")
            uid = event.get("user_id")
            ts = event.get("timestamp")
            if etype is None or uid is None or ts is None:
                continue

            if etype == "queue_join":
                join_times[uid] = ts
            elif etype == "serve_finished":
                if uid in join_times:
                    wait = ts - join_times[uid]
                    wait_times.append(wait)
        return sum(wait_times) / len(wait_times) if wait_times else 0.0

    def window_busy_rate(self) -> Dict[str, float]:
        """各窗口繁忙度 = 服务总人数 / 仿真总时长（人次/分钟）"""
        if not self.snapshots:
            return {}
        total_time = self.snapshots[-1]["time"] - self.snapshots[0]["time"]
        if total_time <= 0:
            return {}

        last_snapshot = self.snapshots[-1]
        windows = last_snapshot.get("windows", {})
        rates = {}
        for win_id, win_data in windows.items():
            served = win_data.get("total_served", 0)
            rates[win_id] = served / total_time if total_time > 0 else 0.0
        return rates

    def peak_hours(self, interval_minutes: int = 30) -> List[Dict]:
        """识别排队高峰时段"""
        if not self.snapshots:
            return []
        bins = defaultdict(int)
        for snap in self.snapshots:
            time = snap.get("time")
            if time is None:
                continue
            bin_key = int(time // interval_minutes) * interval_minutes
            total_queue = sum(snap.get("queues", {}).values())
            bins[bin_key] = max(bins[bin_key], total_queue)

        sorted_peaks = sorted(bins.items(), key=lambda x: x[1], reverse=True)
        return [{"start_time": t, "end_time": t + interval_minutes, "queue_length": q}
                for t, q in sorted_peaks[:3]]

    def total_served(self) -> int:
        """总服务人数（基于 serve_finished 事件）"""
        return sum(1 for e in self.events if e.get("event_type") == "serve_finished")

    def average_seat_occupancy(self) -> Dict[int, float]:
        """各食堂平均座位占用率（%）"""
        if not self.snapshots:
            return {}
        canteen_occ = defaultdict(list)
        for snap in self.snapshots:
            seats = snap.get("seats", {})
            for cid, seat_data in seats.items():
                total = seat_data.get("total", 0)
                occupied = seat_data.get("occupied", 0)
                if total == 0:
                    continue   # 避免除零
                rate = occupied / total * 100
                canteen_occ[int(cid)].append(rate)
        return {cid: sum(rates)/len(rates) for cid, rates in canteen_occ.items()}

#A