import time


class EventScheduler:
    """
    仿真时钟核心：
    - 维护仿真时间（分钟）
    - 每个tick推进所有窗口的打饭进度
    - 每分钟生成一次状态快照
    """

    def __init__(self, canteen_manager, storage=None):
        self.canteen_manager = canteen_manager  # CanteenManager对象
        self.storage = storage                  # Storage对象（可选，用于写日志）
        self.current_time = 0                   # 当前仿真时间（分钟）
        self.queue_engines = {}                 # window_id -> QueueEngine
        self.is_running = False
        self.snapshots = []                     # 每分钟状态快照列表
        self.event_log = []                     # 事件日志

    # ──────────────────────────────
    # 初始化
    # ──────────────────────────────

    def register_queue_engine(self, window_id, queue_engine):
        """注册窗口对应的QueueEngine"""
        self.queue_engines[window_id] = queue_engine
        print(f"📌 窗口ID={window_id} 的队列引擎已注册")

    def register_all_windows(self, queue_engine_map):
        """批量注册，queue_engine_map: {window_id: QueueEngine}"""
        for wid, engine in queue_engine_map.items():
            self.register_queue_engine(wid, engine)

    # ──────────────────────────────
    # 时间推进
    # ──────────────────────────────

    def tick(self):
        """
        推进一个时间单位（1分钟）
        - 驱动所有窗口的打饭进度
        - 每分钟生成状态快照
        """
        self.current_time += 1
        print(f"\n🕐 仿真时间: t={self.current_time} min")

        # 推进所有窗口打饭进度
        for engine in self.queue_engines.values():
            engine.tick(self.current_time)

        # 每分钟生成快照
        self._take_snapshot()

    def run(self, duration, real_time_interval=0.5):
        """
        运行仿真，持续 duration 分钟
        real_time_interval: 每个tick之间的真实等待秒数（控制演示速度）
        """
        self.is_running = True
        print(f"▶️  仿真开始，共运行 {duration} 分钟")
        print("=" * 40)

        try:
            for _ in range(duration):
                if not self.is_running:
                    break
                self.tick()
                time.sleep(real_time_interval)
        except KeyboardInterrupt:
            print("\n⏹️  仿真被手动中断")

        self.is_running = False
        print("=" * 40)
        print(f"✅ 仿真结束，共运行 {self.current_time} 分钟")
        self._print_summary()

    def stop(self):
        """手动停止仿真"""
        self.is_running = False
        print("⏹️  仿真已停止")

    # ──────────────────────────────
    # 快照与日志
    # ──────────────────────────────

    def _take_snapshot(self):
        """生成当前时刻的状态快照"""
        snapshot = {
            'time': self.current_time,
            'windows': []
        }

        for canteen in self.canteen_manager.canteens.values():
            for window in canteen.windows.values():
                snapshot['windows'].append({
                    'canteen': canteen.name,
                    'window_id': window.window_id,
                    'window_name': window.name,
                    'queue_length': window.queue_length(),
                    'serving_user': str(window.serving_user) if window.serving_user else None,
                    'total_served': window.total_served
                })

        self.snapshots.append(snapshot)

        # 如果有storage模块，写入日志
        if self.storage:
            self.storage.write_log(snapshot)

    def log_event(self, event_type, detail):
        """
        记录一条事件日志
        event_type: 'join_queue' / 'served' / 'seat_taken' / 'leave' 等
        """
        entry = {
            'time': self.current_time,
            'type': event_type,
            'detail': detail
        }
        self.event_log.append(entry)
        print(f"📝 事件记录 [{event_type}] t={self.current_time}: {detail}")

    # ──────────────────────────────
    # 统计摘要
    # ──────────────────────────────

    def _print_summary(self):
        """仿真结束后打印统计摘要"""
        print("\n📊 仿真统计摘要")
        print("=" * 40)

        for canteen in self.canteen_manager.canteens.values():
            print(f"\n🏫 {canteen.name}")
            for window in canteen.windows.values():
                # 从快照中统计该窗口的平均队列长度
                lengths = [
                    w['queue_length']
                    for snap in self.snapshots
                    for w in snap['windows']
                    if w['window_id'] == window.window_id
                ]
                avg_queue = sum(lengths) / len(lengths) if lengths else 0
                print(f"  窗口[{window.window_id}] {window.name}")
                print(f"    累计服务人数: {window.total_served}")
                print(f"    平均排队人数: {avg_queue:.1f}")

        print(f"\n共记录事件: {len(self.event_log)} 条")
        print(f"共生成快照: {len(self.snapshots)} 个")