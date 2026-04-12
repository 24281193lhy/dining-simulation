import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business.canteen_manager import CanteenManager
from business.queue_engine import QueueEngine
from business.seat_manager import SeatManager
from business.user_manager import UserManager
from business.event_scheduler import EventScheduler
from ui.student_ui import StudentUI
from ui.admin_ui import AdminUI
from ui.common import show_main_menu
from utils.display import print_info, print_error


# ========== 初始化业务层 ==========
def init_business():
    # 创建食堂管理器
    canteen_manager = CanteenManager()

    # 添加食堂（根据任务书：学一、学二、教工餐厅）
    canteen1 = canteen_manager.add_canteen("学一食堂", total_seats=200)
    canteen2 = canteen_manager.add_canteen("学二食堂", total_seats=150)
    canteen3 = canteen_manager.add_canteen("教工餐厅", total_seats=80)

    # 为食堂添加窗口
    # 学一食堂：普通窗口1、2，教工专窗
    w1 = canteen1.add_window("普通窗口1", speed=1.5, window_type='normal')
    w2 = canteen1.add_window("普通窗口2", speed=1.5, window_type='normal')
    w3 = canteen1.add_window("教工专窗", speed=1.0, window_type='teacher')
    # 添加菜品（示例）
    from business.canteen_manager import Dish
    w1.add_dish(Dish("红烧肉", 12))
    w1.add_dish(Dish("清炒时蔬", 6))
    w2.add_dish(Dish("宫保鸡丁", 15))
    w2.add_dish(Dish("米饭", 1))
    w3.add_dish(Dish("教师特餐", 18))

    # 学二食堂：两个普通窗口
    w4 = canteen2.add_window("普通窗口1", speed=1.2, window_type='normal')
    w5 = canteen2.add_window("普通窗口2", speed=1.2, window_type='normal')
    w4.add_dish(Dish("牛肉面", 20))
    w5.add_dish(Dish("饺子", 15))

    # 教工餐厅：一个教工专窗
    w6 = canteen3.add_window("教工专窗", speed=0.8, window_type='teacher')
    w6.add_dish(Dish("教工套餐", 25))

    # 创建用户管理器
    user_manager = UserManager()
    # 预置一些测试用户（可选）
    user_manager.add_user("S2024001", role='student')
    user_manager.add_user("T001", role='teacher')

    # 为每个窗口创建 QueueEngine，并建立 window_id -> engine 的映射
    queue_engines = {}
    for canteen in canteen_manager.canteens.values():
        for window in canteen.windows.values():
            engine = QueueEngine(window)
            queue_engines[window.window_id] = engine

    # 为每个食堂创建 SeatManager
    seat_managers = {}
    for canteen in canteen_manager.canteens.values():
        seat_managers[canteen.canteen_id] = SeatManager(canteen)

    # 创建事件调度器（传入canteen_manager和storage，storage可为None或后续实现）
    scheduler = EventScheduler(canteen_manager, storage=None)
    # 注册所有窗口的QueueEngine
    scheduler.register_all_windows(queue_engines)

    return {
        'canteen_manager': canteen_manager,
        'user_manager': user_manager,
        'queue_engines': queue_engines,
        'seat_managers': seat_managers,
        'scheduler': scheduler
    }


# ========== 启动仿真时钟线程 ==========
def start_simulation_thread(scheduler, duration=10000, interval=1.0):
    """在后台线程中运行仿真时钟，每隔 interval 秒推进一分钟"""

    def run():
        # 运行很长时间，直到手动停止
        scheduler.run(duration, real_time_interval=interval)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


# ========== 主程序 ==========
def main():
    # 初始化业务组件
    biz = init_business()
    canteen_manager = biz['canteen_manager']
    user_manager = biz['user_manager']
    queue_engines = biz['queue_engines']
    seat_managers = biz['seat_managers']
    scheduler = biz['scheduler']

    # 启动后台仿真时钟
    sim_thread = start_simulation_thread(scheduler)

    # 为了UI能获取实时状态，我们需要将业务对象传递给UI
    # 同时需要为UI提供一些适配函数，因为原始UI期望的方法名和数据结构可能不同
    # 下面创建适配包装类（也可以直接在UI中修改）

    class UIAdapter:
        """为UI层提供统一的接口，隐藏内部业务对象细节"""

        def __init__(self, canteen_manager, user_manager, queue_engines, seat_managers):
            self.cm = canteen_manager
            self.um = user_manager
            self.qe = queue_engines
            self.sm = seat_managers

        def authenticate(self, user_id, user_type):
            """验证并返回用户信息字典"""
            # 如果用户不存在，自动创建
            user = self.um.get_user(user_id)
            if user is None:
                role = 'student' if user_type == 'student' else 'teacher'
                user = self.um.add_user(user_id, role)
            return {"id": user.user_id, "name": user.user_id, "type": user.role}

        def get_all_canteens_status(self):
            """返回实时状态列表，格式与之前Mock相同"""
            result = []
            for cid, canteen in self.cm.canteens.items():
                total_queue = 0
                windows_info = []
                for window in canteen.windows.values():
                    engine = self.qe.get(window.window_id)
                    queue_len = engine.queue_length() if engine else 0
                    wait_time = engine.estimate_wait_time() if engine else 0
                    total_queue += queue_len
                    windows_info.append({
                        "id": window.window_id,
                        "name": window.name,
                        "type": "教工专窗" if window.window_type == 'teacher' else "普通",
                        "queue_len": queue_len,
                        "wait_time": int(wait_time * 60)  # 分钟转秒
                    })
                free_seats = len(canteen.available_seats())
                result.append({
                    "id": cid,
                    "name": canteen.name,
                    "free_seats": free_seats,
                    "total_queue": total_queue,
                    "windows": windows_info
                })
            return result

        def get_window_dishes(self, window_id):
            """返回菜品列表，格式 [{name, price}]"""
            # 需要遍历找到窗口
            for canteen in self.cm.canteens.values():
                window = canteen.get_window(window_id)
                if window:
                    return [{"name": d.name, "price": d.price} for d in window.dishes]
            return []

        def join_queue(self, user_id, window_id):
            """加入队列，返回结果字典"""
            user = self.um.get_user(user_id)
            if not user:
                return {"success": False, "message": "用户不存在"}
            engine = self.qe.get(window_id)
            if not engine:
                return {"success": False, "message": "窗口不存在"}
            success = engine.join_queue(user)
            if success:
                wait_min = engine.estimate_wait_time(user)
                return {"success": True, "wait_time": int(wait_min * 60)}
            else:
                return {"success": False, "message": "加入队列失败，可能已在队列中或权限不足"}

        def get_user_queue_status(self, user_id):
            """获取用户排队状态"""
            user = self.um.get_user(user_id)
            if not user:
                return None
            # 查找用户所在的窗口
            for engine in self.qe.values():
                pos = engine.get_position(user)
                if pos > 0:
                    return {
                        "window_name": engine.window.name,
                        "ahead": pos - 1,
                        "wait_time": int(engine.estimate_wait_time(user) * 60)
                    }
            return None

        def assign_seat(self, user_id, canteen_id):
            """自动分配座位"""
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
            """获取空闲座位列表"""
            seat_mgr = self.sm.get(canteen_id)
            if not seat_mgr:
                return []
            available = seat_mgr.canteen.available_seats()
            return [{"id": s.seat_id, "location": f"座位{s.seat_id}"} for s in available[:10]]

        def occupy_seat(self, user_id, seat_id):
            """手动占座"""
            user = self.um.get_user(user_id)
            if not user:
                return False
            # 需要找到座位所属的食堂
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
            """释放座位"""
            user = self.um.get_user(user_id)
            if not user or not user.current_seat:
                return False
            # 找到座位所属食堂的 SeatManager
            for canteen in self.cm.canteens.values():
                if user.current_seat in canteen.seats:
                    seat_mgr = self.sm.get(canteen.canteen_id)
                    return seat_mgr.release_seat(user)
            return False

        def get_all_canteens_config(self):
            """管理员查看配置，返回包含 total_seats 和窗口 speed 的数据"""
            result = []
            for cid, canteen in self.cm.canteens.items():
                windows_info = []
                for window in canteen.windows.values():
                    windows_info.append({
                        "id": window.window_id,
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

    # 创建适配器
    adapter = UIAdapter(canteen_manager, user_manager, queue_engines, seat_managers)

    # 创建模拟的storage（因为成员C尚未完成，暂时用打印模拟）
    class MockStorage:
        def log_event(self, event_type, user_id, detail):
            print(f"[日志] {event_type} - {user_id} - {detail}")

        def get_statistics(self):
            return {"avg_wait_time": 0, "window_busy_rate": "0%", "peak_hours": "暂无", "total_served": 0}

    storage = MockStorage()

    # 启动UI
    while True:
        choice = show_main_menu()
        if choice == "1":
            student_ui = StudentUI(adapter, adapter, adapter, storage)  # 三个都是adapter
            # 注意 StudentUI 的 __init__ 需要四个参数，这里传同一个adapter即可
            # 但我们之前 StudentUI 的 __init__ 是 (canteen_manager, queue_engine, seat_manager, storage)
            # 现在 adapter 实现了所有需要的方法，所以可以传递 adapter 三次
            student_ui.run()
        elif choice == "2":
            admin_ui = AdminUI(adapter, storage)
            admin_ui.run()
        elif choice == "0":
            print_info("感谢使用，再见！")
            sys.exit(0)


if __name__ == "__main__":
    main()