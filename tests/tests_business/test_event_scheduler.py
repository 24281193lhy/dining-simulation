# tests/test_event_scheduler.py
import pytest
from unittest.mock import MagicMock, patch, call
from collections import deque

# 假设你的项目结构中 business 包可导入
from business.event_scheduler import EventScheduler


# 辅助工厂函数：创建一个模拟的 CanteenManager，包含一个食堂和两个窗口
def create_mock_canteen_manager():
    """返回一个 MagicMock 即 CanteenManager，带有合适的嵌套结构"""
    mock_manager = MagicMock()
    # 构造 canteens 字典，只放一个食堂
    mock_canteen = MagicMock()
    mock_canteen.canteen_id = 1
    mock_canteen.name = "测试食堂"
    # 构造窗口 (魔法对象)
    window1 = MagicMock()
    window1.window_id = 1
    window1.name = "窗口A"
    window1.serving_user = None
    window1.total_served = 0
    window1.queue_length.return_value = 3   # 模拟队列长度

    window2 = MagicMock()
    window2.window_id = 2
    window2.name = "窗口B"
    window2.serving_user = MagicMock()
    window2.serving_user.user_id = "U2"
    window2.total_served = 5
    window2.queue_length.return_value = 1

    mock_canteen.windows = {1: window1, 2: window2}
    mock_canteen.seats = [MagicMock() for _ in range(10)]
    # 设置 occupied_seats 返回两个占用的座位
    mock_canteen.occupied_seats.return_value = [mock_canteen.seats[0], mock_canteen.seats[2]]

    mock_manager.canteens = {1: mock_canteen}
    return mock_manager


class TestEventScheduler:
    def setup_method(self):
        self.mock_storage = MagicMock()
        self.mock_manager = create_mock_canteen_manager()
        self.scheduler = EventScheduler(self.mock_manager, storage=self.mock_storage)

    def test_init(self):
        assert self.scheduler.current_time == 0
        assert self.scheduler.is_running is False
        assert self.scheduler.paused is False
        assert self.scheduler.snapshots == []
        assert self.scheduler.event_log == []
        assert self.scheduler.arrival_callback is None
        assert self.scheduler.serve_finished_callback is None

    # ---------- 注册队列引擎 ----------
    def test_register_queue_engine(self):
        mock_engine = MagicMock()
        self.scheduler.register_queue_engine(1, mock_engine)
        assert 1 in self.scheduler.queue_engines
        mock_engine.add_event_listener.assert_called_once()
        # 可以进一步验证传入的监听器是 _on_engine_event 方法

    def test_register_all_windows(self):
        engines = {10: MagicMock(), 20: MagicMock(), 30: MagicMock()}
        self.scheduler.register_all_windows(engines)
        assert len(self.scheduler.queue_engines) == 3
        for eid, eng in engines.items():
            assert self.scheduler.queue_engines[eid] == eng
            eng.add_event_listener.assert_called_once()

    # ---------- 回调设置 ----------
    def test_set_arrival_callback(self):
        cb = lambda t: []
        self.scheduler.set_arrival_callback(cb)
        assert self.scheduler.arrival_callback == cb

    def test_set_serve_finished_callback(self):
        cb = lambda uid: None
        self.scheduler.set_serve_finished_callback(cb)
        assert self.scheduler.serve_finished_callback == cb

    # ---------- 控制方法 ----------
    def test_pause_resume_stop(self, capsys):
        self.scheduler.is_running = True
        self.scheduler.pause()
        assert self.scheduler.paused is True
        self.scheduler.resume()
        assert self.scheduler.paused is False
        self.scheduler.stop()
        assert self.scheduler.is_running is False

    def test_reset(self):
        # 设置一些内部状态
        self.scheduler.current_time = 20
        self.scheduler.snapshots.append({"dummy": True})
        self.scheduler.event_log.append({"dummy": True})
        self.scheduler.is_running = True
        self.scheduler.paused = True
        # 保留队列引擎
        mock_eng = MagicMock()
        self.scheduler.queue_engines[1] = mock_eng

        self.scheduler.reset()
        assert self.scheduler.current_time == 0
        assert self.scheduler.snapshots == []
        assert self.scheduler.event_log == []
        assert self.scheduler.is_running == False
        assert self.scheduler.paused == False
        # 引擎应该还在（不清空）
        assert 1 in self.scheduler.queue_engines

    # ---------- tick 逻辑 ----------
    def test_tick_basic(self):
        """测试单次 tick 推进时间、调用引擎、产生快照，无 arrival_callback"""
        mock_engine1 = MagicMock()
        mock_engine2 = MagicMock()
        self.scheduler.queue_engines = {1: mock_engine1, 2: mock_engine2}
        self.scheduler.tick()
        assert self.scheduler.current_time == 1
        mock_engine1.tick.assert_called_once_with(1)
        mock_engine2.tick.assert_called_once_with(1)
        # 应该生成快照
        assert len(self.scheduler.snapshots) == 1
        snapshot = self.scheduler.snapshots[0]
        assert snapshot["time"] == 1
        assert "windows" in snapshot and "seats" in snapshot and "queues" in snapshot
        # 检查 windows 状态
        win_status = snapshot["windows"]
        assert "1_1" in win_status  # global_id = canteen_id_window_id
        assert win_status["1_1"]["queue_length"] == 3   # 模拟的 window1.queue_length
        assert win_status["1_2"]["serving"] == "U2"
        # seats
        assert snapshot["seats"][1]["total"] == 10
        assert snapshot["seats"][1]["occupied"] == 2

    def test_tick_with_arrival_callback(self):
        """arrival_callback 返回到达事件，应记录日志"""
        callback = MagicMock()
        callback.return_value = [
            {"user_id": "U10", "detail": "到达窗口1"},
            {"user_id": "U20", "detail": "到达窗口2"}
        ]
        self.scheduler.set_arrival_callback(callback)
        mock_engine = MagicMock()
        self.scheduler.queue_engines = {1: mock_engine}
        self.scheduler.tick()
        callback.assert_called_once_with(1)  # current_time 此时为 1
        # 检查日志
        assert len(self.scheduler.event_log) == 2
        assert self.scheduler.event_log[0]["event_type"] == "arrival"
        assert self.scheduler.event_log[0]["user_id"] == "U10"
        assert self.scheduler.event_log[1]["user_id"] == "U20"

    def test_tick_arrival_callback_exception(self, capsys):
        """回调异常时不应中断 tick"""
        callback = MagicMock(side_effect=ValueError("boom"))
        self.scheduler.set_arrival_callback(callback)
        mock_engine = MagicMock()
        self.scheduler.queue_engines = {1: mock_engine}
        # 不应抛出异常
        self.scheduler.tick()
        captured = capsys.readouterr().out
        assert "arrival_callback 失败" in captured
        # 引擎仍应被调用
        mock_engine.tick.assert_called_once()

    def test_tick_storage_interaction(self):
        """确保快照和事件都写入了 storage"""
        self.scheduler.tick()
        self.mock_storage.save_snapshot.assert_called_once()
        # 因为没 arrival，事件日志为空，故 log_event 不应调用
        self.mock_storage.log_event.assert_not_called()

        # 再模拟一个到达事件
        self.scheduler.set_arrival_callback(lambda t: [{"user_id": "X", "detail": "test"}])
        self.scheduler.tick()
        self.mock_storage.log_event.assert_called_once_with("arrival", "X", "test", timestamp=2)

    # ---------- 事件处理 ----------
    def test_on_engine_event_serve_finished(self):
        """模拟引擎发出的 serve_finished 事件，应触发回调和日志"""
        callback = MagicMock()
        self.scheduler.set_serve_finished_callback(callback)
        event = {"type": "serve_finished", "user_id": "U100", "detail": "打饭完成"}
        self.scheduler._on_engine_event(event)
        callback.assert_called_once_with("U100")
        # 检查日志
        assert len(self.scheduler.event_log) == 1
        assert self.scheduler.event_log[0]["event_type"] == "serve_finished"
        self.mock_storage.log_event.assert_called_once_with("serve_finished", "U100", "打饭完成", timestamp=0)

    def test_on_engine_event_other_type(self):
        """非 serve_finished 类型不触发回调，但会记录日志？看代码：仅 serve_finished 被显式处理，其他类型不会进入 log_event 分支？原代码中 _on_engine_event 只在 event['type'] == 'serve_finished' 时调用 log_event。所以其他类型不会记录。我们需要确认：源码中并无 else 或通用记录。测试应保持一致（实际上不记录）"""
        self.scheduler._on_engine_event({"type": "queue_update", "user_id": "A", "detail": "xxx"})
        # 日志不应增加
        assert len(self.scheduler.event_log) == 0

    # ---------- run 方法 ----------
    @patch("business.event_scheduler.time.sleep", return_value=None)  # 禁用 sleep
    @patch("business.event_scheduler.time.time", return_value=0)     # 可选
    def test_run_basic(self, mock_sleep, mock_time):
        """运行 5 分钟的仿真，Tick 被调用 5 次"""
        original_tick = self.scheduler.tick
        self.scheduler.tick = MagicMock()
        self.scheduler.run(5, real_time_interval=0.001)  # interval 不影响因为 sleep 被模拟
        assert self.scheduler.tick.call_count == 5

    @patch("business.event_scheduler.time.sleep", return_value=None)
    def test_run_with_early_stop(self, mock_sleep):
        """在运行过程中调用 stop() 提前结束"""
        # 用 side_effect 在 tick 侧模拟 stop
        call_count = 0
        def tick_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                self.scheduler.stop()
            self.scheduler.current_time += 1  # 模拟原始 tick 的时间推进
        self.scheduler.tick = MagicMock(side_effect=tick_side_effect)
        self.scheduler.run(10, real_time_interval=0)
        assert call_count == 3  # 只跑了 3 次
        assert self.scheduler.is_running is False

    @patch("business.event_scheduler.time.sleep", return_value=None)
    def test_run_pause_resume(self, mock_sleep):
        """测试暂停期间 tick 不递增，恢复后继续"""
        # 我们需要一个真实的 tick 简化版，但避免复杂，可以模拟 pause 状态
        run_ticks = 0
        def tick_mock():
            nonlocal run_ticks
            # 暂停时不递增 tick 计数，但这里模拟暂停后循环会等待，我们手动推进
            if not self.scheduler.paused:
                run_ticks += 1
                self.scheduler.current_time += 1
        self.scheduler.tick = MagicMock(side_effect=tick_mock)
        # 启动 run 在另一个线程中？但单线程 run 会阻塞。我们可以测试 run 内部暂停逻辑：直接调用 while 循环的机制不合适。
        # 改为测试控制流程：单独测试 pause 对循环的影响，不测多线程。这里用另一种方式：模拟 run 中的循环，我们手动调用 tick 并观察。
        # 合理的做法：测试 run 方法时尽量简单，不深入测暂停恢复的完整过程，因为那需要并发。
        # 替代方案：测试 run 内部在 paused 时确实调用了 sleep，而不会调用 tick。
        # 我们通过 mock sleep 来检查调用次数。
        self.scheduler.paused = True
        # 直接运行 run(1)，会发现因为 paused 为 True，循环第一次就会进入 while self.paused，所以 tick 不会被调用
        # 但需要将 paused 设为 True 以便测试暂停时的行为。为了避免无限循环，我们需要在 sleep 被调用后修改 paused。
        def sleep_side_effect(sec):
            # 第一次 sleep 后立即恢复
            if self.scheduler.paused:
                self.scheduler.resume()
        mock_sleep.side_effect = sleep_side_effect
        self.scheduler.run(1, real_time_interval=0)
        # tick 应该被调用一次（因为暂停被恢复后继续）
        assert self.scheduler.tick.call_count == 1

    # ---------- 总结打印 ----------
    def test_print_summary(self, capsys):
        self.scheduler._print_summary()
        captured = capsys.readouterr().out
        assert "测试食堂" in captured
        assert "窗口A" in captured
        assert "窗口B" in captured
        assert "服务 0 人" in captured  # window1 total_served = 0
        assert "服务 5 人" in captured  # window2 total_served = 5