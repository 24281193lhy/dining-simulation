import random
import math
import json
from collections import defaultdict
from typing import Dict, List, Optional
from business.event_scheduler import EventScheduler

class AutomationCoordinator:
    """自动化仿真协调器，处理用户到达、决策、用餐流程"""

    def __init__(self, canteen_manager, user_manager, queue_engines, seat_managers, storage, config_path="config.json"):
        self.cm = canteen_manager
        self.um = user_manager
        self.qe = queue_engines
        self.sm = seat_managers
        self.storage = storage

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.base_rate = self.config["arrival"]["avg_rate"]
        self.peak_mult = self.config["arrival"]["peak_multiplier"]
        self.peak_start = self.config["arrival"]["peak_hours"][0] * 60
        self.peak_end = self.config["arrival"]["peak_hours"][1] * 60

        self.dist_weight = self.config["decision"]["distance_weight"]
        self.queue_weight = self.config["decision"]["queue_weight"]
        self.pref_weight = self.config["decision"]["preference_weight"]
        self.meal_time_range = self.config["decision"]["meal_time_range"]

        self.current_time = 0
        self.eating_users: Dict[str, dict] = {}
        self.window_service_count = defaultdict(int)
        self.scheduler: Optional[EventScheduler] = None

        # 用户临时状态存储（因为 User 类没有 target_canteen 属性）
        self.user_target: Dict[str, dict] = {}

    def bind_scheduler(self, scheduler: EventScheduler):
        self.scheduler = scheduler
        scheduler.set_arrival_callback(self._arrival_callback)

    def _arrival_callback(self, current_time: float) -> List[dict]:
        self.current_time = current_time

        hour_in_day = current_time % (24 * 60)
        if self.peak_start <= hour_in_day <= self.peak_end:
            rate = self.base_rate * self.peak_mult
        else:
            rate = self.base_rate

        L = math.exp(-rate)
        k = 0
        p = 1.0
        while p > L:
            p *= random.random()
            k += 1
        arrival_count = max(0, k - 1)

        arrivals = []
        for _ in range(arrival_count):
            user = self._select_random_user()
            if not user:
                continue

            canteen_id, window_id = self._decide_canteen_and_window(user)
            if window_id is None:
                continue

            global_win_id = f"{canteen_id}_{window_id}"
            engine = self.qe.get(global_win_id)
            if not engine:
                continue

            if not engine.join_queue(user):
                continue

            # 记录目标食堂窗口
            self.user_target[user.user_id] = {
                "canteen_id": canteen_id,
                "window_id": global_win_id
            }

            # 记录 queue_join 事件供统计使用
            self.storage.log_event("queue_join", user.user_id,
                                   f"加入窗口 {window_id}", timestamp=current_time)

            arrivals.append({
                "user_id": user.user_id,
                "window_id": global_win_id,
                "detail": f"{user.user_id} 到达并加入窗口 {window_id}"
            })

        return arrivals

    def _select_random_user(self):
        all_users = self.um.get_all_users()
        return random.choice(all_users) if all_users else None

    def _decide_canteen_and_window(self, user):
        best_score = -1
        best_canteen = None
        best_window = None

        for canteen in self.cm.canteens.values():
            for window in canteen.windows.values():
                if not window.is_accessible_by(user):
                    continue
                score = self._calculate_window_score(canteen, window)
                if score > best_score:
                    best_score = score
                    best_canteen = canteen.canteen_id
                    best_window = window.window_id
        return best_canteen, best_window

    def _calculate_window_score(self, canteen, window):
        max_queue = 30
        queue_len = min(window.queue_length(), max_queue)
        queue_score = 1.0 - (queue_len / max_queue)

        dist_score = 1.0 / canteen.canteen_id

        global_id = f"{canteen.canteen_id}_{window.window_id}"
        pref_count = self.window_service_count.get(global_id, 0)
        pref_score = min(pref_count / 10.0, 1.0)

        return (self.dist_weight * dist_score +
                self.queue_weight * queue_score +
                self.pref_weight * pref_score)

    def on_serve_finished(self, user_id: str):
        """打饭完成回调，由 EventScheduler 调用"""
        user = self.um.get_user(user_id)
        if not user:
            return

        target = self.user_target.get(user_id)
        if not target:
            return

        canteen_id = target["canteen_id"]
        window_id = target["window_id"]
        self.window_service_count[window_id] += 1

        seat_mgr = self.sm.get(canteen_id)
        if not seat_mgr:
            return

        seat = seat_mgr.assign_seat(user)
        if not seat:
            return

        meal_duration = random.uniform(*self.meal_time_range)
        end_time = self.current_time + meal_duration

        self.eating_users[user_id] = {
            "user": user,
            "canteen_id": canteen_id,
            "seat": seat,
            "end_time": end_time
        }
        self.storage.log_event("seat_occupy", user_id,
                               f"占用座位 {seat.seat_id}", timestamp=self.current_time)

    def tick_post_process(self, current_time: float):
        self.current_time = current_time
        finished = []
        for uid, info in list(self.eating_users.items()):
            if current_time >= info["end_time"]:
                seat_mgr = self.sm.get(info["canteen_id"])
                if seat_mgr:
                    seat_mgr.release_seat(info["user"])
                self.storage.log_event("seat_release", uid,
                                       f"释放座位 {info['seat'].seat_id}", timestamp=current_time)
                finished.append(uid)
                # 清理用户状态
                self.um.clear_user_state(uid)
                if uid in self.user_target:
                    del self.user_target[uid]

        for uid in finished:
            del self.eating_users[uid]

    def finalize_statistics(self, storage):
        from data.statistics import StatisticsAnalyzer
        analyzer = StatisticsAnalyzer(storage)
        stats = analyzer.compute_all()
        storage.export_statistics(stats, "final_stats.json")
        return stats