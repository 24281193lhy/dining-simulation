import random
import math
import json
import threading
from collections import defaultdict
from typing import Dict, List, Optional
from business.event_scheduler import EventScheduler
from monitor.web_monitor import push_user_activity

class AutomationCoordinator:
    """自动化仿真协调器，处理用户到达、决策、用餐流程（线程安全）"""

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

        # 用户临时状态存储
        self.user_target: Dict[str, dict] = {}

        # 线程安全锁
        self._lock = threading.Lock()

    def bind_scheduler(self, scheduler: EventScheduler):
        self.scheduler = scheduler
        scheduler.set_arrival_callback(self._arrival_callback)

    def _arrival_callback(self, current_time: float) -> List[dict]:
        """生成新到达用户（仿真线程内调用，需线程安全）"""
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

            # 记录目标和偏好
            with self._lock:
                self.user_target[user.user_id] = {
                    "canteen_id": canteen_id,
                    "window_id": global_win_id
                }
                # 记录 queue_join 事件（不依赖锁的存储可以放在锁内）
                self.storage.log_event("queue_join", user.user_id,
                                       f"加入窗口 {window_id}", timestamp=current_time)

            # 获取窗口名称用于推送，不涉及共享状态
            canteen = self.cm.canteens.get(canteen_id)
            window_obj = canteen.windows.get(window_id) if canteen else None
            if window_obj:
                push_user_activity(user.user_id, f"加入 {window_obj.name} 队列", current_time)

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
        """窗口选择（保留完整版）"""
        candidates = []
        weights = []

        for canteen in self.cm.canteens.values():
            for window in canteen.windows.values():
                if not window.is_accessible_by(user):
                    continue

                # 教师用户：只选教师专窗
                if user.is_teacher():
                    if window.window_type == 'teacher':
                        candidates.append((canteen.canteen_id, window.window_id))
                        weights.append(100.0)
                    continue  # 跳过所有非教师窗口

                # 学生用户
                score = self._calculate_window_score(canteen, window)
                if score <= 0:
                    continue

                if window.window_type == 'teacher':
                    continue

                candidates.append((canteen.canteen_id, window.window_id))
                weights.append(score)

        if not candidates:
            return None, None

        chosen = random.choices(candidates, weights=weights, k=1)[0]
        return chosen[0], chosen[1]

    def _calculate_window_score(self, canteen, window):
        """计算窗口吸引力得分（读取共享计数时加锁）"""
        max_queue = 30
        queue_len = min(window.queue_length(), max_queue)
        queue_score = 1.0 - (queue_len / max_queue)

        dist_map = {1: 1.0, 2: 0.7, 3: 0.5}
        dist_score = dist_map.get(canteen.canteen_id, 0.3)

        global_id = f"{canteen.canteen_id}_{window.window_id}"
        with self._lock:
            pref_count = self.window_service_count.get(global_id, 0)
        pref_score = min(pref_count / 30.0, 0.3)

        noise = random.uniform(-0.05, 0.05)

        score = (self.dist_weight * dist_score +
                 self.queue_weight * queue_score +
                 self.pref_weight * pref_score +
                 noise)
        return max(score, 0.01)

    def on_serve_finished(self, user_id: str):
        """打饭完成回调，由 EventScheduler 调用（仿真线程）"""
        if self.scheduler:
            self.current_time = self.scheduler.current_time

        user = self.um.get_user(user_id)
        if not user:
            return

        with self._lock:
            target = self.user_target.get(user_id)
        if not target:
            return

        canteen_id = target["canteen_id"]
        window_id = target["window_id"]

        # 更新偏好计数（加锁）
        with self._lock:
            self.window_service_count[window_id] += 1

        seat_mgr = self.sm.get(canteen_id)
        if not seat_mgr:
            return

        # 分配座位（SeatManager 内部加锁）
        seat = seat_mgr.assign_seat(user)
        if not seat:
            return

        meal_duration = random.uniform(*self.meal_time_range)
        end_time = self.current_time + meal_duration

        with self._lock:
            self.eating_users[user_id] = {
                "user": user,
                "canteen_id": canteen_id,
                "seat": seat,
                "end_time": end_time
            }
            self.storage.log_event("seat_occupy", user_id,
                                   f"占用座位 {seat.seat_id}", timestamp=self.current_time)

        window_name = self._get_window_name_by_global_id(window_id)
        push_user_activity(user_id, f"完成打饭，开始在 {window_name} 用餐", self.current_time)

    def tick_post_process(self, current_time: float):
        """
        处理用餐结束（由主线程定期调用，需线程安全）
        遍历 eating_users 时持有锁，防止并发修改
        """
        self.current_time = current_time
        finished = []

        with self._lock:
            # 先找出所有已到时间的用户
            for uid, info in self.eating_users.items():
                if current_time >= info["end_time"]:
                    finished.append(uid)

        # 释放座位等操作可在锁外进行，但需要先复制必要信息
        for uid in finished:
            with self._lock:
                info = self.eating_users.get(uid)
                if not info:
                    continue
                # 再次检查，因为可能被其他线程修改
                if current_time < info["end_time"]:
                    continue

                user = info["user"]
                canteen_id = info["canteen_id"]
                seat = info["seat"]
                # 删除记录
                del self.eating_users[uid]
                self.storage.log_event("seat_release", uid,
                                       f"释放座位 {seat.seat_id}", timestamp=current_time)

                # 清理用户状态
                self.um.clear_user_state(uid)
                if uid in self.user_target:
                    del self.user_target[uid]

            # 释放座位（在锁外调用，SeatManager 内部有锁）
            seat_mgr = self.sm.get(canteen_id)
            if seat_mgr:
                seat_mgr.release_seat(user)

            push_user_activity(uid, "用餐结束，离开食堂", current_time)

    def finalize_statistics(self, storage):
        from data.statistics import StatisticsAnalyzer
        analyzer = StatisticsAnalyzer(storage)
        stats = analyzer.compute_all()
        storage.export_statistics(stats, "final_stats.json")
        return stats

    def _get_window_name_by_global_id(self, global_win_id):
        try:
            c_id, w_id = map(int, global_win_id.split('_'))
            canteen = self.cm.canteens.get(c_id)
            if canteen:
                window = canteen.windows.get(w_id)
                return window.name if window else "未知窗口"
        except:
            pass
        return "未知窗口"
#A