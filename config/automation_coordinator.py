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

            self.user_target[user.user_id] = {
                "canteen_id": canteen_id,
                "window_id": global_win_id
            }

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
        """改进后的窗口选择：教师必选教师窗口，学生按距离+随机权重选窗口"""
        candidates = []
        weights = []

        for canteen in self.cm.canteens.values():
            for window in canteen.windows.values():
                if not window.is_accessible_by(user):
                    continue

                # 教师用户强制只选教师窗口
                if user.is_teacher():
                    if window.window_type == 'teacher':
                        # 教师专窗权重极高
                        candidates.append((canteen.canteen_id, window.window_id))
                        weights.append(100.0)
                    # 忽略非教师窗口
                    continue

                # 学生用户：计算得分
                score = self._calculate_window_score(canteen, window)
                if score <= 0:
                    continue

                # 学生不能选教师专窗（已在 is_accessible_by 处理，但双重保险）
                if window.window_type == 'teacher':
                    continue

                candidates.append((canteen.canteen_id, window.window_id))
                weights.append(score)

        if not candidates:
            return None, None

        # 调试输出（可观察分布）
        chosen = random.choices(candidates, weights=weights, k=1)[0]
        # 取消注释以查看选择日志
        # print(f"[{self.current_time}] 用户 {user.user_id} 选择窗口 {chosen[0]}_{chosen[1]}")
        return chosen[0], chosen[1]

    def _calculate_window_score(self, canteen, window):
        max_queue = 30
        queue_len = min(window.queue_length(), max_queue)
        queue_score = 1.0 - (queue_len / max_queue)

        # 拉大距离差异：食堂1=1.0，食堂2=0.7，食堂3=0.5
        dist_map = {1: 1.0, 2: 0.7, 3: 0.5}
        dist_score = dist_map.get(canteen.canteen_id, 0.3)

        global_id = f"{canteen.canteen_id}_{window.window_id}"
        pref_count = self.window_service_count.get(global_id, 0)
        # 降低偏好得分的增长速率，避免垄断
        pref_score = min(pref_count / 30.0, 0.3)  # 最多贡献0.3

        noise = random.uniform(-0.05, 0.05)

        # 权重配置可在 config.json 中调整
        return (self.dist_weight * dist_score +
                self.queue_weight * queue_score +
                self.pref_weight * pref_score +
                noise)

    def on_serve_finished(self, user_id: str):
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
            # 无空座，用户离开（静默）
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