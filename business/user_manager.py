import re
import random

class User:
    def __init__(self, user_id, role='student'):
        self.user_id = user_id
        self.role = role  # 'student' 或 'teacher'
        self.current_seat = None
        self.current_window = None

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
        """新增用户；如果已存在则直接返回已有用户"""
        if user_id in self.users:
            return self.users[user_id]
        user = User(user_id, role)
        self.users[user_id] = user
        return user

    def get_user(self, user_id):
        return self.users.get(user_id)

    def get_user_object(self, user_id):
        """兼容你 main.py / UIAdapter 的调用习惯"""
        return self.get_user(user_id)

    def get_all_users(self):
        return list(self.users.values())

    def get_users_by_role(self, role):
        return [u for u in self.users.values() if u.role == role]

    def get_random_user(self, role=None):
        """随机获取一个用户，可限定角色"""
        candidates = self.get_all_users()
        if role:
            candidates = [u for u in candidates if u.role == role]
        return random.choice(candidates) if candidates else None

    def verify_student(self, user_id):
        """
        学号格式验证：
        兼容你当前项目里的格式：S + 7位数字，如 S2024001
        """
        return re.fullmatch(r"S\d{7}", str(user_id)) is not None

    def verify_teacher(self, user_id):
        """
        教工号验证：
        兼容格式：T + 至少3位数字，如 T001、T1001
        """
        return re.fullmatch(r"T\d{3,}", str(user_id)) is not None

    def set_current_window(self, user_id, window_id):
        user = self.get_user(user_id)
        if user:
            user.current_window = window_id
            return True
        return False

    def clear_current_window(self, user_id):
        user = self.get_user(user_id)
        if user:
            user.current_window = None
            return True
        return False

    def set_current_seat(self, user_id, seat_id):
        user = self.get_user(user_id)
        if user:
            user.current_seat = seat_id
            return True
        return False

    def clear_current_seat(self, user_id):
        user = self.get_user(user_id)
        if user:
            user.current_seat = None
            return True
        return False

    def clear_user_state(self, user_id):
        """用户离开座位/窗口后统一清理状态"""
        user = self.get_user(user_id)
        if user:
            user.current_seat = None
            user.current_window = None
            return True
        return False

    def create_users_batch(self, prefix='S', start=1, count=100, role='student'):
        """
        批量创建用户
        例：prefix='S', start=1, count=10 -> S0000001, S0000002 ...
        """
        created = []
        for i in range(start, start + count):
            user_id = f"{prefix}{i:07d}"
            created.append(self.add_user(user_id, role))
        return created