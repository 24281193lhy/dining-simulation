# tests/test_queue_engine.py

import pytest
from collections import deque
from unittest.mock import MagicMock

from business.canteen_manager import Window, Dish
from business.queue_engine import QueueEngine


class MockUser:
    """模拟用户对象，模拟 is_teacher 和 user_id 属性"""
    def __init__(self, user_id, is_teacher=False):
        self.user_id = user_id
        self.is_teacher_flag = is_teacher

    def is_teacher(self):
        return self.is_teacher_flag

    def __repr__(self):
        return f"MockUser({self.user_id})"


class TestQueueEngine:
    def setup_method(self):
        # 创建一个普通的窗口，速度 2 分钟/人
        self.window = Window(1, "测试窗口", speed=2.0, window_type='normal')
        self.engine = QueueEngine(self.window)
        # 添加一些菜品（不影响引擎测试，但保持窗口真实）
        self.window.add_dish(Dish("宫保鸡丁", 15))

    # ---------- 基础属性 ----------
    def test_init(self):
        assert self.engine.window == self.window
        assert isinstance(self.engine.queue, deque)
        assert len(self.engine.queue) == 0
        assert self.engine.current_time == 0
        assert self.engine.event_listeners == []

    # ---------- 事件监听器 ----------
    def test_add_event_listener(self):
        listener = MagicMock()
        self.engine.add_event_listener(listener)
        assert listener in self.engine.event_listeners

    def test_emit_event(self):
        listener1 = MagicMock()
        listener2 = MagicMock()
        self.engine.add_event_listener(listener1)
        self.engine.add_event_listener(listener2)

        event = {"type": "test", "data": 123}
        self.engine._emit_event(event)
        listener1.assert_called_once_with(event)
        listener2.assert_called_once_with(event)

    # ---------- _uid ----------
    def test_uid_with_user_id_attr(self):
        user = MockUser("U42")
        assert self.engine._uid(user) == "U42"

    def test_uid_without_user_id(self):
        user = "U_string"
        assert self.engine._uid(user) == "U_string"

    # ---------- join_queue ----------
    def test_join_queue_normal(self):
        user = MockUser("U1")
        result = self.engine.join_queue(user)
        assert result is True
        assert len(self.engine.queue) == 1
        assert self.engine.queue[0] == user

    def test_join_queue_window_closed(self):
        self.window.is_open = False
        user = MockUser("U2")
        result = self.engine.join_queue(user)
        assert result is False
        assert len(self.engine.queue) == 0

    def test_join_queue_teacher_window_denied(self):
        # 创建一个教工专窗
        teacher_window = Window(2, "教工窗", window_type='teacher')
        eng = QueueEngine(teacher_window)
        student = MockUser("S1", is_teacher=False)
        teacher = MockUser("T1", is_teacher=True)

        assert eng.join_queue(student) is False
        assert eng.join_queue(teacher) is True
        assert len(eng.queue) == 1
        assert eng.queue[0] == teacher

    def test_join_queue_duplicate(self):
        user = MockUser("U3")
        self.engine.join_queue(user)
        # 再次加入同一个用户应该被拒绝
        result = self.engine.join_queue(user)
        assert result is False
        assert len(self.engine.queue) == 1

    def test_join_queue_multiple_users(self):
        users = [MockUser(f"U{i}") for i in range(5)]
        for u in users:
            assert self.engine.join_queue(u) is True
        assert self.engine.queue_length() == 5

    # ---------- leave_queue ----------
    def test_leave_queue_existing_user(self):
        u1 = MockUser("U1")
        u2 = MockUser("U2")
        self.engine.join_queue(u1)
        self.engine.join_queue(u2)

        removed = self.engine.leave_queue(u1)
        assert removed is True
        assert self.engine.queue_length() == 1
        assert self.engine.queue[0] == u2

    def test_leave_queue_non_existing(self):
        u1 = MockUser("U1")
        assert self.engine.leave_queue(u1) is False

    # ---------- queue_length & get_position ----------
    def test_queue_length(self):
        assert self.engine.queue_length() == 0
        self.engine.join_queue(MockUser("U1"))
        assert self.engine.queue_length() == 1

    def test_get_position_normal(self):
        users = [MockUser("A"), MockUser("B"), MockUser("C")]
        for u in users:
            self.engine.join_queue(u)
        assert self.engine.get_position(users[0]) == 1
        assert self.engine.get_position(users[1]) == 2
        assert self.engine.get_position(users[2]) == 3

    def test_get_position_not_in_queue(self):
        user = MockUser("X")
        assert self.engine.get_position(user) == -1

    # ---------- process_next ----------
    def test_process_next_nobody_serving_and_queue_empty(self):
        events = self.engine.process_next(10)
        # 不应该有任何事件
        assert events == []

    def test_process_next_start_service(self):
        user = MockUser("U1")
        self.engine.join_queue(user)
        events = self.engine.process_next(5)  # current_time=5
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "serve_start"
        assert event["user"] == user
        assert event["window_id"] == 1
        assert event["time"] == 5
        assert "开始打饭" in event["detail"]

        # 检查窗口状态
        assert self.window.serving_user == user
        assert self.window.serve_end_time == 5 + self.window.speed  # 7
        assert self.window.total_served == 0   # 还没完成

    def test_process_next_finish_service(self):
        user = MockUser("U1")
        self.engine.join_queue(user)
        # 先开始服务
        self.engine.process_next(5)  # serve_end_time = 7
        # 在时间 7 时应该完成
        events = self.engine.process_next(7)
        assert len(events) == 1
        event = events[0]
        assert event["type"] == "serve_finished"
        assert event["user"] == user
        assert self.window.serving_user is None
        assert self.window.total_served == 1

    def test_process_next_finish_and_start_next(self):
        u1 = MockUser("U1")
        u2 = MockUser("U2")
        self.engine.join_queue(u1)
        self.engine.join_queue(u2)
        # 开始服务 u1，时间 5，速度 2 -> 结束于 7
        self.engine.process_next(5)
        # 在时间 7 时，u1 完成，应同时触发 finish 和新的 start（服务于 u2）
        events = self.engine.process_next(7)
        assert len(events) == 2
        finish_event = events[0]
        start_event = events[1]
        assert finish_event["type"] == "serve_finished"
        assert finish_event["user"] == u1
        assert start_event["type"] == "serve_start"
        assert start_event["user"] == u2
        # 窗口状态
        assert self.window.serving_user == u2
        assert self.window.serve_end_time == 7 + self.window.speed  # 9
        assert self.window.total_served == 1   # u1 完成，u2 尚未完成

    def test_process_next_finish_before_time(self):
        """如果 current_time 小于服务结束时间，不触发完成事件"""
        user = MockUser("U1")
        self.engine.join_queue(user)
        self.engine.process_next(5)     # 结束于 7
        events = self.engine.process_next(6)  # 还没到时间
        assert events == []
        assert self.window.serving_user == user  # 仍在服务

    def test_process_next_with_listener_notification(self):
        """验证事件通过 _emit_event 发送给监听器"""
        listener = MagicMock()
        self.engine.add_event_listener(listener)
        user = MockUser("U1")
        self.engine.join_queue(user)
        self.engine.process_next(5)  # 开始服务
        listener.assert_called_once()
        call_args = listener.call_args[0][0]
        assert call_args["type"] == "serve_start"

        listener.reset_mock()
        self.engine.process_next(7)  # 完成服务
        assert listener.call_count == 1  # 只有一个事件，服务完成
        call_args = listener.call_args[0][0]
        assert call_args["type"] == "serve_finished"

    # ---------- tick ----------
    def test_tick_updates_time_and_calls_process_next(self):
        user = MockUser("U1")
        self.engine.join_queue(user)
        events = self.engine.tick(8)
        assert self.engine.current_time == 8
        # 应开始服务
        assert len(events) == 1
        assert events[0]["type"] == "serve_start"

    # ---------- estimate_wait_time ----------
    def test_estimate_wait_time_empty_queue(self):
        # 没有人排队，没有人在服务
        assert self.engine.estimate_wait_time() == 0

    def test_estimate_wait_time_serving_but_no_queue(self):
        # 模拟有一个正在服务的用户，但排队为空
        user = MockUser("U1")
        self.engine.join_queue(user)
        self.engine.tick(10)  # 开始服务，serve_end_time = 12
        # 此时队列为空（因为 u1 被 pop 到 serving_user）
        # 服务剩余时间 = 12 - 10 = 2（但 current_time 已变为 10）
        # 注意 current_time 是 10，serve_end_time 是 12
        wait = self.engine.estimate_wait_time()  # 无 user 参数
        # 队列长度 0，但有 serving_user，公式：remaining + queue_len * speed = 2 + 0*2 = 2
        assert wait == 2.0

    def test_estimate_wait_time_queue_no_serving(self):
        # 队列中有 2 人，没有正在服务的人
        u1 = MockUser("A")
        u2 = MockUser("B")
        self.engine.join_queue(u1)
        self.engine.join_queue(u2)
        # current_time = 0, serving_user = None
        wait = self.engine.estimate_wait_time()
        # queue_len(2) * speed(2.0) = 4
        assert wait == 4.0

    def test_estimate_wait_time_for_specific_user(self):
        # 队列中有 A, B, C，且正在服务 D
        u_d = MockUser("D")
        self.engine.join_queue(u_d)
        self.engine.tick(5)   # u_d 开始服务，serve_end_time = 7
        u_a = MockUser("A")
        u_b = MockUser("B")
        u_c = MockUser("C")
        self.engine.join_queue(u_a)
        self.engine.join_queue(u_b)
        self.engine.join_queue(u_c)
        # 当前时间 5，剩余服务时间 2，speed=2
        # position: A=1, B=2, C=3
        # wait for A: remaining + (1-1)*speed = 2
        # wait for B: remaining + (2-1)*speed = 2 + 2 = 4
        # wait for C: remaining + (3-1)*speed = 2 + 4 = 6
        assert self.engine.estimate_wait_time(u_a) == 2.0
        assert self.engine.estimate_wait_time(u_b) == 4.0
        assert self.engine.estimate_wait_time(u_c) == 6.0

    def test_estimate_wait_time_user_not_in_queue(self):
        user = MockUser("Ghost")
        assert self.engine.estimate_wait_time(user) == 0