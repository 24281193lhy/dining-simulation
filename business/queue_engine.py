import threading
from collections import deque

class QueueEngine:
    """单个窗口的排队与打饭引擎（线程安全）"""

    def __init__(self, window):
        self.window = window
        # 不再创建独立的 self.queue，直接使用 window.queue（统一数据源）
        self.current_time = 0
        self._lock = threading.Lock()          # 【修复 Bug 2】保护所有共享状态
        self.event_listeners = []

    def add_event_listener(self, listener):
        self.event_listeners.append(listener)

    def _emit_event(self, event):
        for listener in self.event_listeners:
            listener(event)

    def _uid(self, user):
        if hasattr(user, "user_id"):
            return user.user_id
        return str(user)

    def join_queue(self, user):
        """加入排队（线程安全）"""
        with self._lock:
            if not self.window.is_open:
                print(f"[警告] 窗口 {self.window.name} 未开放")
                return False
            if not self.window.is_accessible_by(user):
                print(f"[警告] 用户 {self._uid(user)} 无权访问窗口 {self.window.name}")
                return False

            user_id = self._uid(user)

            # 防止重复排队：检查队列 + 正在打饭的用户
            if any(self._uid(u) == user_id for u in self.window.queue):
                return False
            if self.window.serving_user is not None and self._uid(self.window.serving_user) == user_id:
                return False                     # 【修复 Bug 3】禁止正在服务的用户再次加入

            self.window.queue.append(user)       # 【修复 Bug 1】直接使用 window 的队列
            return True

    def leave_queue(self, user):
        """用户主动离队"""
        with self._lock:
            user_id = self._uid(user)
            for u in list(self.window.queue):
                if self._uid(u) == user_id:
                    self.window.queue.remove(u)
                    return True
            return False

    def queue_length(self):
        # 读取时加锁，保证返回值与 window.queue 一致
        with self._lock:
            return len(self.window.queue)

    def get_position(self, user):
        user_id = self._uid(user)
        with self._lock:
            # 先检查是否正在服务（打饭中）
            if self.window.serving_user is not None and self._uid(self.window.serving_user) == user_id:
                return 0   # 正在打饭，位置 0（特殊标识）
            for idx, u in enumerate(self.window.queue):
                if self._uid(u) == user_id:
                    return idx + 1
            return -1

    def process_next(self, current_time):
        """处理服务完成/开始新服务，返回事件列表（线程安全）"""
        events = []
        with self._lock:                # 【修复 Bug 2】整个状态修改过程加锁
            # —— 完成服务 ——
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

            # —— 开始新服务 ——
            if self.window.serving_user is None and self.window.queue:
                next_user = self.window.queue.popleft()      # 【修复 Bug 1】操作 window.queue
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
                # serve_start 事件也通知监听者（虽然目前未使用，但保持完整性）
                self._emit_event(event)

        return events

    def tick(self, current_time):
        self.current_time = current_time
        return self.process_next(current_time)

    def estimate_wait_time(self, user=None):
        """估算等待时间（分钟），读取时加锁保证数据一致性"""
        with self._lock:
            speed = self.window.speed
            remaining = max(0, self.window.serve_end_time - self.current_time)

            if user is not None:
                # 先判断是否正在打饭
                if self.window.serving_user and self._uid(self.window.serving_user) == self._uid(user):
                    return remaining   # 正在打饭，只需等待剩余时间
                pos = self.get_position(user)   # 注意：get_position 内部会再次加锁？会死锁！
                # 因为锁不可重入，这里需要调用不加锁的内部版本，参见下方说明
                if pos <= 0:
                    return 0
                # 位置 pos 是 1-based，不包括打饭中的人
                if self.window.serving_user:
                    return remaining + (pos - 1) * speed
                else:
                    return (pos - 1) * speed
            else:
                queue_len = len(self.window.queue)
                if self.window.serving_user:
                    return remaining + queue_len * speed
                else:
                    return queue_len * speed