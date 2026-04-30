from collections import deque

class QueueEngine:
    """单个窗口的排队与打饭引擎"""

    def __init__(self, window):
        self.window = window
        self.queue = deque()
        self.current_time = 0
        self._last_log = None
        self._event_buffer = []
        # 新增：事件回调列表
        self.event_listeners = []

    def add_event_listener(self, listener):
        """listener 是一个可调用对象，接收事件字典"""
        self.event_listeners.append(listener)

    def _emit_event(self, event):
        for listener in self.event_listeners:
            listener(event)

    def _uid(self, user):
        if hasattr(user, "user_id"):
            return user.user_id
        return str(user)

    def join_queue(self, user):
        if not self.window.is_open:
            print(f"[警告] 窗口 {self.window.name} 未开放")
            return False
        if not self.window.is_accessible_by(user):
            print(f"[警告] 用户 {self._uid(user)} 无权访问窗口 {self.window.name}")
            return False
        user_id = self._uid(user)
        if any(self._uid(u) == user_id for u in self.queue):
            return False
        self.queue.append(user)
        # 注意：queue_join 事件由 AutomationCoordinator 记录，避免重复
        return True

    def leave_queue(self, user):
        user_id = self._uid(user)
        for u in list(self.queue):
            if self._uid(u) == user_id:
                self.queue.remove(u)
                return True
        return False

    def queue_length(self):
        return len(self.queue)

    def get_position(self, user):
        user_id = self._uid(user)
        for idx, u in enumerate(self.queue):
            if self._uid(u) == user_id:
                return idx + 1
        return -1

    def process_next(self, current_time):
        events = []
        # 完成服务
        if self.window.serving_user is not None:
            if current_time >= self.window.serve_end_time:
                done_user = self.window.serving_user
                self.window.serving_user = None
                self.window.total_served += 1
                done_uid = self._uid(done_user)
                event = {
                    "type": "serve_finished",
                    "user": done_user,
                    "user_id": done_uid,
                    "window_id": self.window.window_id,
                    "time": current_time,
                    "detail": f"{done_uid} 打饭完成"
                }
                events.append(event)
                self._emit_event(event)

        # 开始新服务
        if self.window.serving_user is None and self.queue:
            next_user = self.queue.popleft()
            self.window.serving_user = next_user
            self.window.serve_end_time = current_time + self.window.speed
            next_uid = self._uid(next_user)
            event = {
                "type": "serve_start",
                "user": next_user,
                "user_id": next_uid,
                "window_id": self.window.window_id,
                "time": current_time,
                "detail": f"{next_uid} 开始打饭"
            }
            events.append(event)
            self._emit_event(event)

        return events

    def tick(self, current_time):
        self.current_time = current_time
        return self.process_next(current_time)

    def estimate_wait_time(self, user=None):
        speed = self.window.speed
        remaining = max(0, self.window.serve_end_time - self.current_time)
        if user is not None:
            pos = self.get_position(user)
            if pos == -1:
                return 0
            if self.window.serving_user:
                return remaining + (pos - 1) * speed
            else:
                return (pos - 1) * speed
        queue_len = self.queue_length()
        if self.window.serving_user:
            return remaining + queue_len * speed
        else:
            return queue_len * speed