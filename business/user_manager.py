# 2.4 用户角色管理

class User:
    def __init__(self, user_id, role='student'):
        self.user_id = user_id
        self.role = role  # 'student' 或 'teacher'
        self.current_seat = None
        self.current_window = None

    def is_teacher(self):
        return self.role == 'teacher'

    def __str__(self):
        return f"[{self.role}] {self.user_id}"


class UserManager:
    def __init__(self):
        self.users = {}  # user_id -> User

    def add_user(self, user_id, role='student'):
        user = User(user_id, role)
        self.users[user_id] = user
        return user

    def get_user(self, user_id):
        return self.users.get(user_id)

    def verify_student(self, user_id):
        """学号格式验证，北交大学号为8位数字"""
        return str(user_id).isdigit() and len(str(user_id)) == 8

    def verify_teacher(self, user_id):
        """教工号验证"""
        return str(user_id).startswith('T') and len(str(user_id)) >= 5