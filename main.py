# main.py 测试入口
from business.canteen_manager import CanteenManager, Dish
from business.queue_engine import QueueEngine
from business.seat_manager import SeatManager
from business.user_manager import UserManager
from business.event_scheduler import EventScheduler


def main():
    print("=" * 50)
    print("   北京交通大学食堂就餐仿真系统 - 测试运行")
    print("=" * 50)

    # ──────────────────────────────
    # 1. 初始化用户
    # ──────────────────────────────
    print("\n【1】初始化用户")
    user_manager = UserManager()
    s1 = user_manager.add_user("20231001", role="student")
    s2 = user_manager.add_user("20231002", role="student")
    t1 = user_manager.add_user("T10086", role="teacher")
    print(f"  已创建: {s1}, {s2}, {t1}")

    # ──────────────────────────────
    # 2. 初始化食堂和窗口
    # ──────────────────────────────
    print("\n【2】初始化食堂")
    canteen_manager = CanteenManager()
    canteen = canteen_manager.add_canteen("第一食堂", total_seats=10)

    # 添加窗口
    w1 = canteen.add_window("窗口1-炒菜", speed=2.0, window_type="normal")
    w2 = canteen.add_window("窗口2-面食", speed=1.5, window_type="normal")
    w3 = canteen.add_window("窗口3-教工专窗", speed=1.0, window_type="teacher")

    # 添加菜品
    w1.add_dish(Dish("宫保鸡丁", 12.0))
    w1.add_dish(Dish("鱼香肉丝", 10.0))
    w2.add_dish(Dish("牛肉面", 14.0))
    w3.add_dish(Dish("红烧肉", 18.0))

    print(f"\n  {canteen}")
    for w in canteen.windows.values():
        print(f"  {w}")

    # ──────────────────────────────
    # 3. 测试排队逻辑
    # ──────────────────────────────
    print("\n【3】测试排队")
    engine1 = QueueEngine(w1)
    engine2 = QueueEngine(w2)
    engine3 = QueueEngine(w3)

    # 学生排队
    engine1.join_queue(s1)
    engine1.join_queue(s2)
    engine2.join_queue(s1)  # 同一学生排两个窗口（测试）

    # 教师尝试普通窗口和专窗
    engine1.join_queue(t1)
    engine3.join_queue(t1)

    # 学生尝试教工专窗（应该被拒绝）
    engine3.join_queue(s1)

    print(f"\n  窗口1队列长度: {engine1.queue_length()}")
    print(f"  窗口1预计新加入等待: {engine1.estimate_wait_time():.1f} min")

    # ──────────────────────────────
    # 4. 测试座位分配
    # ──────────────────────────────
    print("\n【4】测试座位分配")
    seat_manager = SeatManager(canteen)

    seat_manager.assign_seat(s1, strategy='nearest')
    seat_manager.assign_seat(s2, strategy='random')
    seat_manager.assign_specific_seat(t1, seat_id=5)

    seat_manager.print_status()

    # 释放座位
    seat_manager.release_seat(s1)
    seat_manager.print_status()

    # ──────────────────────────────
    # 5. 测试事件调度器（仿真推进）
    # ──────────────────────────────
    print("\n【5】测试事件调度器（仿真推进5分钟）")
    scheduler = EventScheduler(canteen_manager)
    scheduler.register_queue_engine(w1.window_id, engine1)
    scheduler.register_queue_engine(w2.window_id, engine2)
    scheduler.register_queue_engine(w3.window_id, engine3)

    # 推进5分钟（不用真实等待）
    for _ in range(5):
        scheduler.tick()

    # 打印各窗口状态
    print("\n  各窗口状态：")
    engine1.status_summary()
    engine2.status_summary()
    engine3.status_summary()

    print("\n" + "=" * 50)
    print("✅ 测试完成，所有模块运行正常")
    print("=" * 50)


if __name__ == "__main__":
    main()