import time
import random

class EventScheduler:
    def __init__(self, canteen_manager, storage=None):
        self.canteen_manager = canteen_manager
        self.storage = storage
        self.current_time = 0
        self.queue_engines = {}
        self.is_running = False
        self.snapshots = []
        self.event_log = []
        self.arrival_callback = None
        # 新增：打饭完成后的外部回调
        self.serve_finished_callback = None

    def register_queue_engine(self, window_id, queue_engine):
        self.queue_engines[window_id] = queue_engine
        # 为每个引擎添加事件监听，以便捕获 serve_finished
        queue_engine.add_event_listener(self._on_engine_event)

    def register_all_windows(self, queue_engine_map):
        for wid, engine in queue_engine_map.items():
            self.register_queue_engine(wid, engine)

    def set_arrival_callback(self, callback):
        self.arrival_callback = callback

    def set_serve_finished_callback(self, callback):
        """设置打饭完成后的回调，用于触发占座用餐流程"""
        self.serve_finished_callback = callback

    def _on_engine_event(self, event):
        """QueueEngine 产生事件时触发"""
        if event["type"] == "serve_finished":
            self.log_event(event["type"], event["user_id"], event["detail"])
            if self.serve_finished_callback:
                self.serve_finished_callback(event["user_id"])

    def tick(self):
        self.current_time += 1

        if self.arrival_callback:
            try:
                arrivals = self.arrival_callback(self.current_time)
                for item in arrivals:
                    self.log_event("arrival", item["user_id"], item["detail"])
            except Exception as e:
                print(f"⚠️ arrival_callback 失败: {e}")

        for engine in self.queue_engines.values():
            engine.tick(self.current_time)

        self._take_snapshot()

    def run(self, duration, real_time_interval=0.5):
        self.is_running = True
        try:
            for _ in range(duration):
                if not self.is_running:
                    break
                self.tick()
                time.sleep(real_time_interval)
        except KeyboardInterrupt:
            print("\n⏹️  仿真被手动中断")
        self.is_running = False
        print(f"✅ 仿真结束，共运行 {self.current_time} 分钟")
        self._print_summary()

    def stop(self):
        self.is_running = False

    def _take_snapshot(self):
        windows_status = {}
        queues_length = {}
        for canteen in self.canteen_manager.canteens.values():
            for window in canteen.windows.values():
                global_id = f"{canteen.canteen_id}_{window.window_id}"
                windows_status[global_id] = {
                    "window_id": window.window_id,
                    "canteen_id": canteen.canteen_id,
                    "serving": window.serving_user.user_id if window.serving_user else None,
                    "total_served": window.total_served,
                    "queue_length": window.queue_length()
                }
                queues_length[global_id] = window.queue_length()

        seats_status = {}
        for canteen in self.canteen_manager.canteens.values():
            seats_status[canteen.canteen_id] = {
                "total": len(canteen.seats),
                "occupied": len(canteen.occupied_seats())
            }

        if self.storage:
            self.storage.save_snapshot(
                time=self.current_time,
                windows_status=windows_status,
                seats_status=seats_status,
                queues_length=queues_length
            )

        self.snapshots.append({
            "time": self.current_time,
            "windows": windows_status,
            "seats": seats_status,
            "queues": queues_length
        })

    def log_event(self, event_type, user_id, detail):
        record = {
            "time": self.current_time,
            "event_type": event_type,
            "user_id": user_id,
            "detail": detail
        }
        self.event_log.append(record)
        if self.storage:
            self.storage.log_event(event_type, user_id, detail, timestamp=self.current_time)

    def _print_summary(self):
        print("\n📊 仿真统计摘要")
        for canteen in self.canteen_manager.canteens.values():
            print(f"\n🏫 {canteen.name}")
            for window in canteen.windows.values():
                print(f"  窗口[{window.window_id}] {window.name}: 服务 {window.total_served} 人")