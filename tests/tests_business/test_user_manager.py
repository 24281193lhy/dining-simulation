# tests/test_user_manager.py

import pytest
import re
from unittest.mock import patch
from business.user_manager import User, UserManager


class TestUser:
    def test_init_student(self):
        user = User("S2024001", "student")
        assert user.user_id == "S2024001"
        assert user.role == "student"
        assert user.current_seat is None
        assert user.current_window is None

    def test_init_teacher(self):
        user = User("T001", "teacher")
        assert user.role == "teacher"

    def test_is_teacher(self):
        student = User("S1", "student")
        teacher = User("T1", "teacher")
        assert student.is_teacher() is False
        assert teacher.is_teacher() is True

    def test_is_student(self):
        student = User("S1", "student")
        teacher = User("T1", "teacher")
        assert student.is_student() is True
        assert teacher.is_student() is False

    def test_str(self):
        student = User("S2024001", "student")
        assert str(student) == "[student] S2024001"
        teacher = User("T001", "teacher")
        assert str(teacher) == "[teacher] T001"


class TestUserManager:
    def setup_method(self):
        self.manager = UserManager()

    # ---------- add_user ----------
    def test_add_new_user(self):
        user = self.manager.add_user("S0000001", "student")
        assert user.user_id == "S0000001"
        assert user.role == "student"
        assert "S0000001" in self.manager.users

    def test_add_existing_user_returns_same_object(self):
        user1 = self.manager.add_user("S0000001", "student")
        user2 = self.manager.add_user("S0000001", "student")
        assert user1 is user2

    def test_add_user_default_role(self):
        user = self.manager.add_user("U123")
        assert user.role == "student"

    # ---------- get_user / get_user_object ----------
    def test_get_user_exists(self):
        self.manager.add_user("U1")
        u = self.manager.get_user("U1")
        assert u.user_id == "U1"

    def test_get_user_not_exists(self):
        assert self.manager.get_user("Ghost") is None

    def test_get_user_object_alias(self):
        self.manager.add_user("U1")
        u = self.manager.get_user_object("U1")
        assert u.user_id == "U1"

    # ---------- get_all_users / get_users_by_role ----------
    def test_get_all_users_empty(self):
        assert self.manager.get_all_users() == []

    def test_get_all_users(self):
        self.manager.add_user("U1", "student")
        self.manager.add_user("U2", "teacher")
        all_users = self.manager.get_all_users()
        assert len(all_users) == 2
        ids = {u.user_id for u in all_users}
        assert ids == {"U1", "U2"}

    def test_get_users_by_role(self):
        self.manager.add_user("S1", "student")
        self.manager.add_user("S2", "student")
        self.manager.add_user("T1", "teacher")
        students = self.manager.get_users_by_role("student")
        assert len(students) == 2
        assert all(u.role == "student" for u in students)
        teachers = self.manager.get_users_by_role("teacher")
        assert len(teachers) == 1
        assert teachers[0].user_id == "T1"

    # ---------- get_random_user ----------
    def test_get_random_user_no_role(self):
        self.manager.add_user("U1")
        self.manager.add_user("U2")
        # 使用 patch 固定随机选择
        with patch('random.choice') as mock_choice:
            mock_choice.return_value = self.manager.users["U1"]
            user = self.manager.get_random_user()
            assert user.user_id == "U1"
            mock_choice.assert_called_once()

    def test_get_random_user_with_role(self):
        self.manager.add_user("S1", "student")
        self.manager.add_user("S2", "student")
        self.manager.add_user("T1", "teacher")
        with patch('random.choice') as mock_choice:
            mock_choice.return_value = self.manager.users["S2"]
            user = self.manager.get_random_user(role="student")
            assert user.user_id == "S2"
            # 检查 candidates 被正确过滤
            call_args = mock_choice.call_args[0][0]
            assert len(call_args) == 2
            assert all(u.role == "student" for u in call_args)

    def test_get_random_user_no_candidates(self):
        # 没有任何用户
        user = self.manager.get_random_user()
        assert user is None
        # 有用户但角色不匹配
        self.manager.add_user("T1", "teacher")
        user = self.manager.get_random_user(role="student")
        assert user is None

    # ---------- 验证方法 ----------
    def test_verify_student_valid(self):
        assert self.manager.verify_student("S2024001") is True
        assert self.manager.verify_student("S0000000") is True

    def test_verify_student_invalid(self):
        assert self.manager.verify_student("T001") is False
        assert self.manager.verify_student("S123") is False       # 非7位
        assert self.manager.verify_student("S12345678") is False  # 8位
        assert self.manager.verify_student("student1") is False

    def test_verify_teacher_valid(self):
        assert self.manager.verify_teacher("T001") is True
        assert self.manager.verify_teacher("T12345") is True

    def test_verify_teacher_invalid(self):
        assert self.manager.verify_teacher("S1234567") is False
        assert self.manager.verify_teacher("T0") is False         # 少于3位
        assert self.manager.verify_teacher("T12") is False
        assert self.manager.verify_teacher("teacher") is False

    # ---------- 窗口状态管理 ----------
    def test_set_current_window(self):
        self.manager.add_user("U1")
        assert self.manager.set_current_window("U1", 5) is True
        u = self.manager.get_user("U1")
        assert u.current_window == 5

    def test_set_current_window_invalid_user(self):
        assert self.manager.set_current_window("Ghost", 5) is False

    def test_clear_current_window(self):
        self.manager.add_user("U1")
        self.manager.set_current_window("U1", 5)
        assert self.manager.clear_current_window("U1") is True
        u = self.manager.get_user("U1")
        assert u.current_window is None

    def test_clear_current_window_no_user(self):
        assert self.manager.clear_current_window("Ghost") is False

    # ---------- 座位状态管理 ----------
    def test_set_current_seat(self):
        self.manager.add_user("U1")
        assert self.manager.set_current_seat("U1", 12) is True
        u = self.manager.get_user("U1")
        # 注意：UserManager.set_current_seat 直接设置 user.current_seat = seat_id（整数）
        assert u.current_seat == 12

    def test_clear_current_seat(self):
        self.manager.add_user("U1")
        self.manager.set_current_seat("U1", 12)
        assert self.manager.clear_current_seat("U1") is True
        u = self.manager.get_user("U1")
        assert u.current_seat is None

    # ---------- clear_user_state ----------
    def test_clear_user_state(self):
        self.manager.add_user("U1")
        self.manager.set_current_window("U1", 5)
        self.manager.set_current_seat("U1", 3)
        assert self.manager.clear_user_state("U1") is True
        u = self.manager.get_user("U1")
        assert u.current_seat is None
        assert u.current_window is None

    def test_clear_user_state_no_user(self):
        assert self.manager.clear_user_state("Ghost") is False

    # ---------- create_users_batch ----------
    def test_create_users_batch_default(self):
        users = self.manager.create_users_batch()
        assert len(users) == 100
        # 检查第一个和最后一个 ID
        assert users[0].user_id == "S0000001"
        assert users[99].user_id == "S0000100"
        assert all(u.role == "student" for u in users)

    def test_create_users_batch_custom_prefix_and_start(self):
        users = self.manager.create_users_batch(prefix="T", start=100, count=5, role="teacher")
        assert len(users) == 5
        expected_ids = [f"T{i:07d}" for i in range(100, 105)]
        for u, eid in zip(users, expected_ids):
            assert u.user_id == eid
            assert u.role == "teacher"

    def test_create_users_batch_zero_count(self):
        users = self.manager.create_users_batch(count=0)
        assert users == []

    def test_create_users_batch_adds_to_manager(self):
        self.manager.create_users_batch(prefix="X", start=1, count=3)
        assert "X0000001" in self.manager.users
        assert "X0000002" in self.manager.users
        assert "X0000003" in self.manager.users