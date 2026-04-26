import sys
import os
import threading
import time
import json
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from business.canteen_manager import CanteenManager, Dish
from business.queue_engine import QueueEngine
from business.seat_manager import SeatManager
from business.user_manager import UserManager
from business.event_scheduler import EventScheduler
from data.storage import SimulationStorage
from data.statistics import StatisticsAnalyzer
from utils.display import print_info, print_success, print_error, print_warning
from automation_coordinator import AutomationCoordinator
from monitor.web_monitor import start_monitor, push_snapshot

def init_business(storage):
    canteen_manager = CanteenManager()

    # ---------- 创建食堂、窗口、菜品 ----------
    c1 = canteen_manager.add_canteen("学生第一食堂", total_seats=120)
    w1_1 = c1.add_window("快餐窗口", speed=0.8, window_type='normal')
    w1_1.add_dish(Dish("红烧肉套餐", 15.0))
    w1_1.add_dish(Dish("宫保鸡丁", 12.0))
    w1_2 = c1.add_window("面食窗口", speed=1.2, window_type='normal')
    w1_2.add_dish(Dish("牛肉拉面", 12.0))
    w1_2.add_dish(Dish("炸酱面", 10.0))

    c2 = canteen_manager.add_canteen("教工食堂", total_seats=80)
    w2_1 = c2.add_window("教工专窗", speed=1.0, window_type='teacher')
    w2_1.add_dish(Dish("教师套餐A", 18.0))
    w2_1.add_dish(Dish("教师套餐B", 20.0))
    w2_2 = c2.add_window("普通窗口", speed=1.0, window_type='normal')
    w2_2.add_dish(Dish("盖浇饭", 13.0))

    c3 = canteen_manager.add_canteen("风味餐厅", total_seats=100)
    w3_1 = c3.add_window("麻辣烫", speed=1.5, window_type='normal')
    w3_1.add_dish(Dish("自选麻辣烫", 16.0))
    w3_2 = c3.add_window("铁板饭", speed=1.3, window_type='normal')
    w3_2.add_dish(Dish("黑椒牛肉铁板", 18.0))

    # ---------- 用户管理器 ----------
    user_manager = UserManager()
    student_ids = set()
    while len(student_ids) < 200:
        year = random.randint(22, 25)
        college = random.randint(1, 50)
        clazz = random.randint(1, 20)
        seq = random.randint(0, 99)
        sid = f"{year:02d}{college:02d}{clazz:02d}{seq:02d}"
        student_ids.add(sid)
    for sid in student_ids:
        user_manager.add_user(sid, role='student')
    for i in range(1, 21):
        user_manager.add_user(f"T{i:03d}", role='teacher')

    # ---------- 队列引擎和座位管理器 ----------
    queue_engines = {}
    for canteen in canteen_manager.canteens.values():
        for window in canteen.windows.values():
            global_id = f"{canteen.canteen_id}_{window.window_id}"
            engine = QueueEngine(window)
            queue_engines[global_id] = engine

    seat_managers = {}
    for canteen in canteen_manager.canteens.values():
        seat_managers[canteen.canteen_id] = SeatManager(canteen)

    # ---------- 事件调度器 ----------
    scheduler = EventScheduler(canteen_manager, storage=storage)
    scheduler.register_all_windows(queue_engines)

    return {
        'canteen_manager': canteen_manager,
        'user_manager': user_manager,
        'queue_engines': queue_engines,
        'seat_managers': seat_managers,
        'scheduler': scheduler
    }

def main():
    with open("config.json", 'r', encoding='utf-8') as f:
        config = json.load(f)

    sim_cfg = config["simulation"]
    duration = sim_cfg["duration"]
    tick_interval = sim_cfg["tick_interval"]
    stats_interval = sim_cfg["stats_interval"]
    log_dir = sim_cfg["log_dir"]

    storage = SimulationStorage(log_dir=log_dir)
    biz = init_business(storage)

    canteen_manager = biz['canteen_manager']
    user_manager = biz['user_manager']
    queue_engines = biz['queue_engines']
    seat_managers = biz['seat_managers']
    scheduler = biz['scheduler']

    # 创建自动化协调器
    coordinator = AutomationCoordinator(
        canteen_manager, user_manager, queue_engines, seat_managers, storage,
        config_path="config.json"
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
                    "queue_length": queue_len  # 使用引擎的队列长度
                }
        from data.statistics import StatisticsAnalyzer
        analyzer = StatisticsAnalyzer(storage)
        stats = analyzer.compute_all()
        result = {
            "time": current_time,
            "total_served": stats['total_served'],
            "avg_wait": stats['avg_wait_time'],
            "windows": windows_data
        }
        return result

    start_monitor(port=5000)
    print_info("🌐 实时监测仪表盘已启动，请访问 http://localhost:5000")

    print_success("🚀 自动化食堂仿真系统启动")
    print_info(f"⏱️  仿真时长：{duration} 分钟")
    print_info(f"👥 用户总数：{len(user_manager.get_all_users())}")
    print_info(f"🍽️  食堂数量：{len(canteen_manager.canteens)}")

    def run_simulation():
        scheduler.run(duration, real_time_interval=tick_interval)
        # 仿真结束后额外处理一次用餐结束
        coordinator.tick_post_process(scheduler.current_time)

        final_snapshot = _build_snapshot(scheduler.current_time)
        push_snapshot(final_snapshot)

        print_success("\n📊 仿真完成，正在生成统计报告...")
        stats = coordinator.finalize_statistics(storage)
        print_info(f"平均等待时间：{stats['avg_wait_time']:.2f} 分钟")
        print_info(f"总服务人数：{stats['total_served']}")
        print_info(f"平均座位占用率：{stats['avg_seat_occupancy']}")

    sim_thread = threading.Thread(target=run_simulation, daemon=True)
    sim_thread.start()

    try:
        while sim_thread.is_alive():
            print(">>> 进入主循环迭代")
            time.sleep(stats_interval)
            coordinator.tick_post_process(scheduler.current_time)
            analyzer = StatisticsAnalyzer(storage)
            stats = analyzer.compute_all()

            # ✅ 这两行必须存在且缩进正确（在 while 内部）
            snapshot = _build_snapshot(scheduler.current_time)
            push_snapshot(snapshot)

            print_info(f"[t={scheduler.current_time:.0f}min] "
                       f"已服务 {stats['total_served']} 人，"
                       f"平均等待 {stats['avg_wait_time']:.2f} min")
    except KeyboardInterrupt:
        print_warning("\n⏹️  用户中断，正在停止仿真...")
        scheduler.stop()

    sim_thread.join()
    print_success("✅ 仿真系统正常退出")

if __name__ == "__main__":
    main()