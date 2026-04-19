import sys
import os
import threading

import time
import json


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business.canteen_manager import CanteenManager
from business.queue_engine import QueueEngine
from business.seat_manager import SeatManager
from business.user_manager import UserManager
from business.event_scheduler import EventScheduler
from data.storage import SimulationStorage
from data.statistics import StatisticsAnalyzer
from ui.student_ui import StudentUI
from ui.admin_ui import AdminUI
from ui.common import show_main_menu
from utils.display import print_info, print_error


# ========== 初始化业务层 ==========
def init_business(storage):
    canteen_manager = CanteenManager()
    from business.canteen_manager import Dish

    # ========== 1. 学苑餐厅 ==========
    canteen1 = canteen_manager.add_canteen("学苑餐厅", total_seats=200)
    # 普通窗口1
    w1 = canteen1.add_window("米粉窗口", speed=1.2, window_type='normal')
    w1.add_dish(Dish("米粉", 15))
    w1.add_dish(Dish("吊龙米线", 17))
    # 普通窗口2
    w2 = canteen1.add_window("麻辣香锅窗口", speed=1.5, window_type='normal')
    w2.add_dish(Dish("麻辣香锅", 20))
    # 普通窗口3
    w3 = canteen1.add_window("石锅拌饭窗口", speed=1.3, window_type='normal')
    w3.add_dish(Dish("石锅拌饭", 15))
    w3.add_dish(Dish("广式烧腊饭", 17))
    # 普通窗口4
    w4 = canteen1.add_window("自选菜窗口", speed=0.9, window_type='normal')
    w4.add_dish(Dish("自选菜", 12))
    # 普通窗口5
    w5 = canteen1.add_window("早餐窗口", speed=0.8, window_type='normal')
    w5.add_dish(Dish("早餐", 8))

    # ========== 2. 明湖餐厅 ==========
    canteen2 = canteen_manager.add_canteen("明湖餐厅", total_seats=200)
    w6 = canteen2.add_window("烤鸭窗口", speed=1.4, window_type='normal')
    w6.add_dish(Dish("烤鸭", 20))
    w7 = canteen2.add_window("黄焖鸡窗口", speed=1.2, window_type='normal')
    w7.add_dish(Dish("黄焖鸡", 15))
    w7.add_dish(Dish("小炒肉", 17))
    w8 = canteen2.add_window("风味炒饭窗口", speed=1.0, window_type='normal')
    w8.add_dish(Dish("风味炒饭", 12))
    w9 = canteen2.add_window("面食窗口", speed=1.3, window_type='normal')
    w9.add_dish(Dish("刀削面", 16))
    w9.add_dish(Dish("重庆小面", 12))
    w10 = canteen2.add_window("自选菜窗口", speed=0.9, window_type='normal')
    w10.add_dish(Dish("自选菜", 12))
    w11 = canteen2.add_window("擂椒拌饭窗口", speed=1.1, window_type='normal')
    w11.add_dish(Dish("擂椒拌饭", 15))
    w12 = canteen2.add_window("早餐窗口", speed=0.8, window_type='normal')
    w12.add_dish(Dish("早餐", 8))

    # ========== 3. 学活餐厅 ==========
    canteen3 = canteen_manager.add_canteen("学活餐厅", total_seats=250)
    w13 = canteen3.add_window("油泼面窗口", speed=1.2, window_type='normal')
    w13.add_dish(Dish("油泼面", 12))
    w13.add_dish(Dish("刀削面", 15))
    w14 = canteen3.add_window("渔粉窗口", speed=1.3, window_type='normal')
    w14.add_dish(Dish("渔粉", 16))
    w14.add_dish(Dish("过桥米线", 17))
    w15 = canteen3.add_window("烤盘饭窗口", speed=1.5, window_type='normal')
    w15.add_dish(Dish("烤盘饭", 20))
    w16 = canteen3.add_window("拌饭窗口", speed=1.2, window_type='normal')
    w16.add_dish(Dish("炙烤五花肉拌饭", 17))
    w16.add_dish(Dish("法式烤排饭", 15.6))
    w17 = canteen3.add_window("韩式烤肉拌饭窗口", speed=1.1, window_type='normal')
    w17.add_dish(Dish("韩式烤肉拌饭", 16))
    w18 = canteen3.add_window("自选菜窗口", speed=0.9, window_type='normal')
    w18.add_dish(Dish("自选菜", 12))
    w19 = canteen3.add_window("早餐窗口", speed=0.8, window_type='normal')
    w19.add_dish(Dish("早餐", 8))

    # ========== 4. 学四食堂 ==========
    canteen4 = canteen_manager.add_canteen("学四食堂", total_seats=150)
    w20 = canteen4.add_window("米线抄手窗口", speed=1.2, window_type='normal')
    w20.add_dish(Dish("吊龙米线", 17))
    w20.add_dish(Dish("重庆抄手", 9))
    w21 = canteen4.add_window("烧鸭饭窗口", speed=1.3, window_type='normal')
    w21.add_dish(Dish("广式烧鸭饭", 15))
    w21.add_dish(Dish("隆江猪脚饭", 17))
    w22 = canteen4.add_window("馄饨窗口", speed=1.0, window_type='normal')
    w22.add_dish(Dish("三鲜馄饨", 9))
    w22.add_dish(Dish("福鼎肉片", 15))
    w23 = canteen4.add_window("减脂餐窗口", speed=0.9, window_type='normal')
    w23.add_dish(Dish("减脂餐", 10))
    w24 = canteen4.add_window("自选菜窗口", speed=0.9, window_type='normal')
    w24.add_dish(Dish("自选菜", 12))
    w25 = canteen4.add_window("早餐窗口", speed=0.8, window_type='normal')
    w25.add_dish(Dish("早餐", 8))

    # ========== 5. 留园餐厅（教师餐厅） ==========
    canteen5 = canteen_manager.add_canteen("留园餐厅", total_seats=100)
    # 教师窗口1
    w26 = canteen5.add_window("烤鱼窗口", speed=0.8, window_type='teacher')
    w26.add_dish(Dish("烤鱼", 50))
    # 教师窗口2
    w27 = canteen5.add_window("教师自选菜窗口", speed=0.7, window_type='teacher')
    w27.add_dish(Dish("教师自选菜", 15))
    # 教师窗口3
    w28 = canteen5.add_window("早餐窗口", speed=0.6, window_type='teacher')
    w28.add_dish(Dish("早餐", 10))

    # ========== 用户管理器 ==========
    user_manager = UserManager()
    user_manager.add_user("S2024001", role='student')
    user_manager.add_user("T001", role='teacher')

    # ========== 创建队列引擎和座位管理器 ==========
    queue_engines = {}
    for canteen in canteen_manager.canteens.values():
        for window in canteen.windows.values():
            global_id = f"{canteen.canteen_id}_{window.window_id}"
            engine = QueueEngine(window)
            queue_engines[global_id] = engine

    seat_managers = {}
    for canteen in canteen_manager.canteens.values():
        seat_managers[canteen.canteen_id] = SeatManager(canteen)

    # ========== 事件调度器 ==========
    scheduler = EventScheduler(canteen_manager, storage=storage)
    scheduler.register_all_windows(queue_engines)

    return {
        'canteen_manager': canteen_manager,
        'user_manager': user_manager,
        'queue_engines': queue_engines,
        'seat_managers': seat_managers,
        'scheduler': scheduler
    }


def start_simulation_thread(scheduler, duration=10000, interval=1.0):
    def run():
        scheduler.run(duration, real_time_interval=interval)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


class AdminManager:
    def __init__(self, config_dir="config"):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "admin.json")
        self._ensure_config()

    def _ensure_config(self):
        """确保配置文件存在，默认账号 admin 密码 admin123"""
        os.makedirs(self.config_dir, exist_ok=True)
        if not os.path.exists(self.config_file):
            default = {"username": "admin", "password": "admin123"}
            with open(self.config_file, "w") as f:
                json.dump(default, f, indent=2)

    def authenticate(self, username, password):
        """验证管理员账号密码"""
        with open(self.config_file, "r") as f:
            data = json.load(f)
        return data.get("username") == username and data.get("password") == password

    def change_password(self, username, old_password, new_password):
        """修改密码，需验证旧密码"""
        if not self.authenticate(username, old_password):
            return False
        with open(self.config_file, "r") as f:
            data = json.load(f)
        data["password"] = new_password
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)
        return True

# ========== UI适配器 ==========
class UIAdapter:
    def __init__(self, canteen_manager, user_manager, queue_engines, seat_managers,scheduler):
        self.cm = canteen_manager
        self.um = user_manager
        self.qe = queue_engines
        self.sm = seat_managers
        self.scheduler = scheduler

    def list_canteens(self):
        return [{"id": cid, "name": c.name} for cid, c in self.cm.canteens.items()]

    def add_canteen(self, name, total_seats):
        canteen = self.cm.add_canteen(name, total_seats=total_seats)
        if canteen.canteen_id not in self.sm:
            self.sm[canteen.canteen_id] = SeatManager(canteen)
        return canteen.canteen_id

    def add_window(self, canteen_id, name, speed, window_type):
        canteen = self.cm.get_canteen(canteen_id)
        if not canteen:
            return None
        window = canteen.add_window(name, speed=speed, window_type=window_type)
        global_id = f"{canteen_id}_{window.window_id}"
        engine = QueueEngine(window)
        self.qe[global_id] = engine
        self.scheduler.register_queue_engine(global_id, engine)  # 关键：注册到时钟
        return global_id

    def add_dish(self, window_global_id, dish_name, price):
        from business.canteen_manager import Dish
        parts = window_global_id.split('_')
        if len(parts) != 2:
            return False
        cid, wid = int(parts[0]), int(parts[1])
        canteen = self.cm.get_canteen(cid)
        if not canteen:
            return False
        window = canteen.get_window(wid)
        if not window:
            return False
        dish = Dish(dish_name, price)
        window.add_dish(dish)
        return True

    def get_user_object(self, user_id):
        return self.um.get_user(user_id)

    def authenticate(self, user_id, user_type):
        user = self.um.get_user(user_id)
        if user is None:
            role = 'student' if user_type == 'student' else 'teacher'
            user = self.um.add_user(user_id, role)
        return {"id": user.user_id, "name": user.user_id, "type": user.role}

    def get_all_canteens_status(self, user=None):
        """user 参数为 User 对象，用于过滤窗口"""
        result = []
        for cid, canteen in self.cm.canteens.items():
            total_queue = 0
            windows_info = []
            # 根据用户身份过滤窗口
            if user:
                visible_windows = canteen.get_accessible_windows(user)
            else:
                visible_windows = list(canteen.windows.values())
            for window in visible_windows:
                global_id = f"{cid}_{window.window_id}"
                engine = self.qe.get(global_id)
                queue_len = engine.queue_length() if engine else 0
                wait_time = engine.estimate_wait_time() if engine else 0
                total_queue += queue_len
                windows_info.append({
                    "id": global_id,
                    "name": window.name,
                    "type": "教工专窗" if window.window_type == 'teacher' else "普通",
                    "queue_len": queue_len,
                    "wait_time": int(wait_time * 60)
                })
            if not windows_info:
                continue  # 无可见窗口则不显示该食堂
            free_seats = len(canteen.available_seats())
            result.append({
                "id": cid,
                "name": canteen.name,
                "free_seats": free_seats,
                "total_queue": total_queue,
                "windows": windows_info
            })
        return result

    def get_window_dishes(self, window_global_id):
        parts = window_global_id.split('_')
        if len(parts) != 2:
            return []
        cid, wid = int(parts[0]), int(parts[1])
        canteen = self.cm.get_canteen(cid)
        if not canteen:
            return []
        window = canteen.get_window(wid)
        if not window:
            return []
        return [{"name": d.name, "price": d.price} for d in window.dishes]

    def join_queue(self, user_id, window_global_id):
        user = self.um.get_user(user_id)
        if not user:
            return {"success": False, "message": "用户不存在"}
        engine = self.qe.get(window_global_id)
        if not engine:
            return {"success": False, "message": "窗口不存在"}
        success = engine.join_queue(user)
        if success:
            wait_min = engine.estimate_wait_time(user)
            return {"success": True, "wait_time": int(wait_min * 60)}
        else:
            return {"success": False, "message": "加入队列失败，可能已在队列中或权限不足"}

    def get_user_queue_status(self, user_id):
        user = self.um.get_user(user_id)
        if not user:
            return None
        for global_id, engine in self.qe.items():
            pos = engine.get_position(user)
            if pos > 0:
                return {
                    "window_name": engine.window.name,
                    "ahead": pos - 1,
                    "wait_time": int(engine.estimate_wait_time(user) * 60)
                }
        return None

    def assign_seat(self, user_id, canteen_id):
        user = self.um.get_user(user_id)
        if not user:
            return None
        seat_mgr = self.sm.get(canteen_id)
        if not seat_mgr:
            return None
        seat = seat_mgr.assign_seat(user, strategy='nearest')
        if seat:
            return {"id": seat.seat_id, "location": f"座位{seat.seat_id}"}
        return None

    def get_free_seats(self, canteen_id):
        seat_mgr = self.sm.get(canteen_id)
        if not seat_mgr:
            return []
        available = seat_mgr.canteen.available_seats()
        return [{"id": s.seat_id, "location": f"座位{s.seat_id}"} for s in available[:10]]

    def occupy_seat(self, user_id, seat_id):
        user = self.um.get_user(user_id)
        if not user:
            return False
        for canteen in self.cm.canteens.values():
            seat_mgr = self.sm.get(canteen.canteen_id)
            seat = seat_mgr._get_seat(seat_id)
            if seat:
                if seat.is_occupied:
                    return False
                seat.occupy(user)
                user.current_seat = seat
                return True
        return False

    def release_seat(self, user_id):
        user = self.um.get_user(user_id)
        if not user or not user.current_seat:
            return False
        for canteen in self.cm.canteens.values():
            if user.current_seat in canteen.seats:
                seat_mgr = self.sm.get(canteen.canteen_id)
                return seat_mgr.release_seat(user)
        return False

    def get_all_canteens_config(self):
        result = []
        for cid, canteen in self.cm.canteens.items():
            windows_info = []
            for window in canteen.windows.values():
                windows_info.append({
                    "id": f"{cid}_{window.window_id}",
                    "name": window.name,
                    "type": "教工专窗" if window.window_type == 'teacher' else "普通",
                    "speed": window.speed,
                    "dishes": [d.name for d in window.dishes]
                })
            result.append({
                "id": cid,
                "name": canteen.name,
                "total_seats": len(canteen.seats),
                "windows": windows_info
            })
        return result


# ========== 主程序 ==========
def main():
    # 初始化真实存储
    storage = SimulationStorage(log_dir="logs")

    # 初始化业务组件
    biz = init_business(storage)
    canteen_manager = biz['canteen_manager']
    user_manager = biz['user_manager']
    queue_engines = biz['queue_engines']
    seat_managers = biz['seat_managers']
    scheduler = biz['scheduler']

    # 启动仿真时钟线程
    sim_thread = start_simulation_thread(scheduler)

    # 创建适配器
    adapter = UIAdapter(canteen_manager, user_manager, queue_engines, seat_managers, scheduler)

    # 包装存储以提供统计
    class StorageWithStats:
        def __init__(self, storage):
            self.storage = storage
        def log_event(self, *args, **kwargs):
            self.storage.log_event(*args, **kwargs)
        def get_statistics(self):
            analyzer = StatisticsAnalyzer(self.storage)
            stats = analyzer.compute_all()
            return {
                "avg_wait_time": round(stats['avg_wait_time'] * 60),
                "window_busy_rate": str(round(stats.get('window_busy_rate', {}).get('overall', 0) * 100)) + "%",
                "peak_hours": str(stats.get('peak_hours', [])),
                "total_served": stats['total_served']
            }

    real_storage = StorageWithStats(storage)

    # 创建管理员管理器（放在主循环之前）
    admin_manager = AdminManager()

    # 主循环（只保留一个）
    while True:
        choice = show_main_menu()
        if choice == "1":
            student_ui = StudentUI(adapter, adapter, adapter, real_storage)
            student_ui.run()
        elif choice == "2":
            admin_ui = AdminUI(adapter, real_storage, admin_manager)   # 传入三个参数
            admin_ui.run()
        elif choice == "0":
            print_info("感谢使用，再见！")
            sys.exit(0)

if __name__ == "__main__":
    main()