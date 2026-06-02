import re
import random

class User:
    def __init__(self, user_id, role='student'):
        self.user_id = user_id
        self.role = role            # 'student' / 'teacher'
        self.current_seat = None    # Seat 对象（由 SeatManager 设置）
        # self.current_window = None  # 移除不存在的属性，系统不跟踪用户当前窗口

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    def __str__(self):
        return f"[{self.role}] {self.user_id}"


class UserManager:
    def __init__(self):
        self.users = {}  # user_id -> User

    def add_user(self, user_id, role='student'):
        """新建或返回已有用户"""
        if user_id in self.users:
            return self.users[user_id]
        user = User(user_id, role)
        self.users[user_id] = user
        return user

    def get_user(self, user_id):
        return self.users.get(user_id)

    def get_user_object(self, user_id):
        """兼容 UIAdapter 的调用"""
        return self.get_user(user_id)

    def get_all_users(self):
        return list(self.users.values())

    def get_users_by_role(self, role):
        return [u for u in self.users.values() if u.role == role]

    def get_random_user(self, role=None):
        candidates = self.get_all_users()
        if role:
            candidates = [u for u in candidates if u.role == role]
        return random.choice(candidates) if candidates else None

    # ── 以下方法修复 / 移除 ──
    # 移除 set_current_seat / clear_current_seat（座位应由 SeatManager 管理）
    # 移除 set_current_window / clear_current_window（无对应属性）

    def clear_user_state(self, user_id):
        """清理用户座位状态（仅清理 current_seat，不可越权）"""
        user = self.get_user(user_id)
        if user:
            # 不直接修改 current_seat，而是通知 SeatManager 完成释放
            # 如果外部已经释放，这里确保引用为 None
            user.current_seat = None
            return True
        return False

    def create_users_batch(self, prefix='S', start=1, count=100, role='student'):
        """批量创建用户，ID 格式：prefix + 7位数字"""
        created = []
        for i in range(start, start + count):
            user_id = f"{prefix}{i:07d}"
            created.append(self.add_user(user_id, role))
        return created

    # 验证方法（更新为与 main.py 一致，若未使用可删除）
    def verify_student(self, user_id):
        """学号格式：2位年份 + 2位学院 + 2位班级 + 2位序号"""
        return bool(re.fullmatch(r"\d{8}", str(user_id)))

    def verify_teacher(self, user_id):
        """教工号格式：T + 至少3位数字"""
        return bool(re.fullmatch(r"T\d{3,}", str(user_id)))

#A