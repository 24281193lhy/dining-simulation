from collections import deque


class QueueEngine:
    """单个窗口的排队与打饭引擎"""

    def __init__(self, window):
        self.window = window        # 关联的Window对象
        self.queue = deque()        # 排队队列，存储User对象
        self.current_time = 0       # 当前仿真时间（分钟）

    # ──────────────────────────────
    # 排队操作
    # ──────────────────────────────

    def join_queue(self, user):
        """用户加入队列"""
        if not self.window.is_open:
            #print(f"❌ 窗口'{self.window.name}'已关闭，无法排队")
            return False
        if not self.window.is_accessible_by(user):
            #print(f"❌ {user} 无权使用'{self.window.name}'（教工专窗）")
            return False
        if user in self.queue:
            #print(f"⚠️ {user} 已在队列中")
            return False

        self.queue.append(user)
        #pos = len(self.queue)
        #print(f"✅ {user} 加入'{self.window.name}'队列，当前排第{pos}位")
        return True

    def leave_queue(self, user):
        """用户主动退出队列"""
        if user in self.queue:
            self.queue.remove(user)
            print(f"🚶 {user} 已退出'{self.window.name}'队列")
            return True
        print(f"⚠️ {user} 不在队列中")
        return False

    def queue_length(self):
        return len(self.queue)

    def get_position(self, user):
        """获取用户在队列中的位置（从1开始）"""
        queue_list = list(self.queue)
        if user in queue_list:
            return queue_list.index(user) + 1
        return -1

    # ──────────────────────────────
    # 打饭进度模拟
    # ──────────────────────────────

    def process_next(self, current_time):
        if self.window.serving_user is not None:
            if current_time < self.window.serve_end_time:
                return None
            done_user = self.window.serving_user
            self.window.serving_user = None
            self.window.total_served += 1
            # 不再直接print，改为记录到日志
            self._log(f"{done_user} 在'{self.window.name}'打饭完成（t={current_time}min）")

        if self.queue:
            next_user = self.queue.popleft()
            self.window.serving_user = next_user
            self.window.serve_end_time = current_time + self.window.speed
            self._log(f"{next_user} 开始打饭，预计完成时间 t={self.window.serve_end_time}min")
            return None
        return None

    def _log(self, msg):
        """内部日志，不干扰UI输出"""
        self._last_log = msg  # 存起来，不print

    def tick(self, current_time):
        """每个时间步调用一次，自动推进打饭进度"""
        self.current_time = current_time
        self.process_next(current_time)

    # ──────────────────────────────
    # 等待时间估算
    # ──────────────────────────────

    def estimate_wait_time(self, user=None):
        speed = self.window.speed
        current = self.current_time  # 使用当前仿真时间

        # 当前服务剩余时间（分钟）
        remaining = max(0, self.window.serve_end_time - current)

        if user is not None:
            pos = self.get_position(user)
            if pos == -1:
                return 0
            return remaining + (pos - 1) * speed
        else:
            queue_len = self.queue_length()
            if self.window.serving_user:
                return remaining + queue_len * speed
            else:
                return queue_len * speed

    def status_summary(self):
        """打印当前窗口排队状态"""
        serving = (f"正在服务: {self.window.serving_user} "
                   f"(预计完成t={self.window.serve_end_time}min)"
                   if self.window.serving_user else "当前空闲")
        print(f"── {self.window.name} ──")
        print(f"  {serving}")
        print(f"  排队人数: {self.queue_length()}")
        print(f"  新加入预计等待: {self.estimate_wait_time():.1f} min")
        print(f"  累计服务人数: {self.window.total_served}")