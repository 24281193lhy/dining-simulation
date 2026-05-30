import sys
import os
import threading
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business.canteen_manager import CanteenManager, Dish
from business.queue_engine import QueueEngine
from business.seat_manager import SeatManager
from business.user_manager import UserManager
from business.event_scheduler import EventScheduler
from data.storage import SimulationStorage
from utils.display import print_info, print_success, print_warning
from config.automation_coordinator import AutomationCoordinator
from monitor.web_monitor import (
    start_monitor, push_snapshot, set_adapter, set_scheduler,
    set_reset_callback, push_final_statistics, push_simulation_summary,
    clear_snapshots, set_storage, set_auto_exit_callback
)

# ========== 全局配置 ==========
SIM_CONFIG = {}

class AdminManager:
    def __init__(self, config_dir="config"):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "admin.json")
        self._ensure_config()
    def _ensure_config(self):
        os.makedirs(self.config_dir, exist_ok=True)
        if not os.path.exists(self.config_file):
            default = {"username": "admin", "password": "admin123"}
            with open(self.config_file, "w") as f:
                json.dump(default, f, indent=2)
    def authenticate(self, username, password):
        with open(self.config_file, "r") as f:
            data = json.load(f)
        return data.get("username") == username and data.get("password") == password
    def change_password(self, username, old_password, new_password):
        if not self.authenticate(username, old_password):
            return False
        with open(self.config_file, "r") as f:
            data = json.load(f)
        data["password"] = new_password
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)
        return True

def load_config():
    global SIM_CONFIG
    try:
        with open("config/config.json", 'r', encoding='utf-8') as f:
            SIM_CONFIG = json.load(f)
    except FileNotFoundError:
        print_warning("配置文件 config/config.json 未找到，使用默认配置。")
        SIM_CONFIG = {
            "simulation": {
                "duration": 120,
                "tick_interval": 0.5,
                "stats_interval": 5,
                "stats_interval_unit": "second"
            }
        }
    return SIM_CONFIG["simulation"]


# ========== 初始化业务层 ==========
def init_business(storage):
    canteen_manager = CanteenManager()

    # 学生第一食堂
    c1 = canteen_manager.add_canteen("学生第一食堂", total_seats=120)
    w1_1 = c1.add_window("快餐窗口", speed=0.8, window_type='normal')
    w1_1.add_dish(Dish("红烧肉套餐", 15.0))
    w1_1.add_dish(Dish("宫保鸡丁", 12.0))
    w1_2 = c1.add_window("面食窗口", speed=1.2, window_type='normal')
    w1_2.add_dish(Dish("牛肉拉面", 12.0))
    w1_2.add_dish(Dish("炸酱面", 10.0))

    # 教工食堂
    c2 = canteen_manager.add_canteen("教工食堂", total_seats=80)
    w2_1 = c2.add_window("教工专窗", speed=1.0, window_type='teacher')
    w2_1.add_dish(Dish("教师套餐A", 18.0))
    w2_1.add_dish(Dish("教师套餐B", 20.0))
    w2_2 = c2.add_window("普通窗口", speed=1.0, window_type='normal')
    w2_2.add_dish(Dish("盖浇饭", 13.0))

    # 风味餐厅
    c3 = canteen_manager.add_canteen("风味餐厅", total_seats=100)
    w3_1 = c3.add_window("麻辣烫", speed=1.5, window_type='normal')
    w3_1.add_dish(Dish("自选麻辣烫", 16.0))
    w3_2 = c3.add_window("铁板饭", speed=1.3, window_type='normal')
    w3_2.add_dish(Dish("黑椒牛肉铁板", 18.0))

    # 用户管理器
    user_manager = UserManager()
    import random
    existing_ids = set()
    while len(existing_ids) < 200:
        year = random.randint(22, 25)
        college = random.randint(1, 50)
        clazz = random.randint(1, 20)
        seq = random.randint(0, 99)
        sid = f"{year:02d}{college:02d}{clazz:02d}{seq:02d}"
        existing_ids.add(sid)
    for sid in existing_ids:
        user_manager.add_user(sid, role='student')
    for i in range(1, 21):
        user_manager.add_user(f"T{i:03d}", role='teacher')

    # 队列引擎 & 座位管理器
    queue_engines = {}
    for canteen in canteen_manager.canteens.values():
        for window in canteen.windows.values():
            global_id = f"{canteen.canteen_id}_{window.window_id}"
            engine = QueueEngine(window)
            queue_engines[global_id] = engine

    seat_managers = {}
    for canteen in canteen_manager.canteens.values():
        seat_managers[canteen.canteen_id] = SeatManager(canteen)

    scheduler = EventScheduler(canteen_manager, storage=storage)
    scheduler.register_all_windows(queue_engines)

    return {
        'canteen_manager': canteen_manager,
        'user_manager': user_manager,
        'queue_engines': queue_engines,
        'seat_managers': seat_managers,
        'scheduler': scheduler
    }


# ========== UI适配器 ==========
class UIAdapter:
    def __init__(self, canteen_manager, user_manager, queue_engines, seat_managers, scheduler):
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
        self.scheduler.register_queue_engine(global_id, engine)
        return global_id

    def add_dish(self, window_global_id, dish_name, price):
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
        result = []
        for cid, canteen in self.cm.canteens.items():
            total_queue = 0
            windows_info = []
            visible_windows = canteen.get_accessible_windows(user) if user else list(canteen.windows.values())
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
                continue
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
            return {"success": False, "message": "加入队列失败"}

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
            seat = seat_mgr.assign_specific_seat(user, seat_id)
            if seat is not None:
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


# ========== 全局仿真状态管理 ==========
class SimulationContext:
    def __init__(self):
        self.storage = None
        self.canteen_manager = None
        self.user_manager = None
        self.queue_engines = None
        self.seat_managers = None
        self.scheduler = None
        self.coordinator = None
        self.adapter = None
        self.sim_thread = None
        self._build_snapshot = None

    def build_snapshot(self, current_time):
        if self._build_snapshot:
            return self._build_snapshot(current_time)
        return {}

current_ctx = SimulationContext()
sim_thread = None
ctx_lock = threading.Lock()
_simulation_started = False

# 用于自动退出的事件
exit_event = threading.Event()

def start_simulation():
    """由前端调用的启动函数（首次启动）"""
    global _simulation_started, current_ctx, duration, tick_interval
    if _simulation_started:
        print_info("⚠️ 仿真已经启动，无需重复启动")
        return
    with ctx_lock:
        if current_ctx.scheduler and not current_ctx.scheduler.is_running:
            start_simulation_thread(current_ctx, duration, tick_interval)
            _simulation_started = True
            print_success("✅ 仿真已手动启动")
        else:
            print_warning("❌ 无法启动：调度器未就绪或已在运行")

def init_simulation_context():
    storage = SimulationStorage(log_dir="logs")
    set_storage(storage)
    biz = init_business(storage)

    canteen_manager = biz['canteen_manager']
    user_manager = biz['user_manager']
    queue_engines = biz['queue_engines']
    seat_managers = biz['seat_managers']
    scheduler = biz['scheduler']

    coordinator = AutomationCoordinator(
        canteen_manager, user_manager, queue_engines, seat_managers, storage,
        config_path="config/config.json"
    )
    coordinator.bind_scheduler(scheduler)
    scheduler.set_serve_finished_callback(coordinator.on_serve_finished)

    def _build_snapshot(current_time):
        windows_data = {}
        for canteen in canteen_manager.canteens.values():
            for window in canteen.windows.values():
                global_id = f"{canteen.canteen_id}_{window.window_id}"
                engine = queue_engines.get(global_id)
                queue_len = engine.queue_length() if engine else 0
                windows_data[window.name] = {
                    "total_served": window.total_served,
                    "queue_length": queue_len
                }
        try:
            from data.statistics import StatisticsAnalyzer
            analyzer = StatisticsAnalyzer(storage)
            stats = analyzer.compute_all()
        except Exception:
            stats = {'total_served': 0, 'avg_wait_time': 0}
        return {
            "time": current_time,
            "total_served": stats['total_served'],
            "avg_wait": stats['avg_wait_time'],
            "windows": windows_data
        }

    adapter = UIAdapter(canteen_manager, user_manager, queue_engines, seat_managers, scheduler)

    ctx = SimulationContext()
    ctx.storage = storage
    ctx.canteen_manager = canteen_manager
    ctx.user_manager = user_manager
    ctx.queue_engines = queue_engines
    ctx.seat_managers = seat_managers
    ctx.scheduler = scheduler
    ctx.coordinator = coordinator
    ctx.adapter = adapter
    ctx._build_snapshot = _build_snapshot
    return ctx


def start_simulation_thread(ctx, duration, tick_interval):
    def run():
        ctx.scheduler.run(duration, real_time_interval=tick_interval)
        ctx.coordinator.tick_post_process(ctx.scheduler.current_time)
        final_snapshot = ctx.build_snapshot(ctx.scheduler.current_time)
        push_snapshot(final_snapshot)
        print_success("\n📊 仿真完成，正在生成统计报告...")
        stats = ctx.coordinator.finalize_statistics(ctx.storage)
        push_final_statistics(stats)
        push_simulation_summary(stats)
        print_success("\n📊 仿真完成，统计结果已发送至前端")
        print_info(f"平均等待时间：{stats['avg_wait_time']:.2f} 分钟")
        print_info(f"总服务人数：{stats['total_served']}")
        print_info(f"平均座位占用率：{stats['avg_seat_occupancy']}")

    global sim_thread
    if sim_thread and sim_thread.is_alive():
        sim_thread.join(timeout=2)
    sim_thread = threading.Thread(target=run, daemon=True)
    sim_thread.start()


def reset_simulation():
    global current_ctx, sim_thread
    print_warning("正在重置仿真...")
    if current_ctx.scheduler:
        current_ctx.scheduler.stop()
    if sim_thread and sim_thread.is_alive():
        sim_thread.join(timeout=2)

    sim_cfg = load_config()
    duration = sim_cfg["duration"]
    tick_interval = sim_cfg["tick_interval"]

    new_ctx = init_simulation_context()
    set_adapter(new_ctx.adapter)
    set_scheduler(new_ctx.scheduler)

    with ctx_lock:
        current_ctx = new_ctx
    start_simulation_thread(new_ctx, duration, tick_interval)
    clear_snapshots()
    _simulation_started = False
    print_success("仿真已重置并重新开始")


def main():
    global current_ctx
    global duration,tick_interval
    from monitor.web_monitor import set_admin_manager
    admin_manager = AdminManager()
    set_admin_manager(admin_manager)
    sim_cfg = load_config()
    duration = sim_cfg["duration"]
    tick_interval = sim_cfg["tick_interval"]
    stats_interval = sim_cfg.get("stats_interval", 5)
    if sim_cfg.get("stats_interval_unit") == "minute":
        stats_interval *= 60

    current_ctx = init_simulation_context()
    set_adapter(current_ctx.adapter)
    set_scheduler(current_ctx.scheduler)
    set_reset_callback(reset_simulation)
    from monitor.web_monitor import set_start_callback
    set_start_callback(start_simulation)
    # 注册自动退出回调：当网页全部关闭时触发

    #start_simulation_thread(current_ctx, duration, tick_interval)

    start_monitor(port=5000)

    import webbrowser
    webbrowser.open('http://localhost:5000')

    print_info("🌐 实时监测仪表盘已启动，请访问 http://localhost:5000")
    print_success("🚀 自动化食堂仿真系统启动")
    print_info(f"⏱️ 仿真时长：{duration} 分钟")
    print_info(f"👥 用户总数：{len(current_ctx.user_manager.get_all_users())}")
    print_info(f"🍽️ 食堂数量：{len(current_ctx.canteen_manager.canteens)}")

    # 主循环
    try:
        while not exit_event.is_set():      # 检查自动退出信号
            # 用 wait 代替 sleep，可被立即中断
            if exit_event.wait(timeout=stats_interval):
                break
            with ctx_lock:
                ctx = current_ctx
            if ctx.scheduler and ctx.scheduler.is_running:
                if not ctx.scheduler.paused:
                    ctx.coordinator.tick_post_process(ctx.scheduler.current_time)
                    snapshot = ctx.build_snapshot(ctx.scheduler.current_time)
                    push_snapshot(snapshot)
                    try:
                        from data.statistics import StatisticsAnalyzer
                        analyzer = StatisticsAnalyzer(ctx.storage)
                        stats = analyzer.compute_all()
                        print_info(f"[t={ctx.scheduler.current_time:.0f}min] "
                                   f"已服务 {stats['total_served']} 人，"
                                   f"平均等待 {stats['avg_wait_time']:.2f} min")
                    except Exception:
                        pass
    except KeyboardInterrupt:
        print_warning("\n⏹️ 用户中断，正在停止仿真...")
    finally:
        print_warning("正在关闭仿真...")
        with ctx_lock:
            ctx = current_ctx
        if ctx.scheduler:
            ctx.scheduler.stop()
        if sim_thread and sim_thread.is_alive():
            sim_thread.join(timeout=2)
        print_success("✅ 仿真系统正常退出")
        #A


if __name__ == "__main__":
    main()