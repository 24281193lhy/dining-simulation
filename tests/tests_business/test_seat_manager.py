# tests/test_seat_manager.py

import pytest
from unittest.mock import patch
from business.canteen_manager import Canteen, Seat
from business.seat_manager import SeatManager


class MockUser:
    """模拟用户，拥有 user_id 和 current_seat 属性"""
    def __init__(self, user_id):
        self.user_id = user_id
        self.current_seat = None

    def __repr__(self):
        return f"MockUser({self.user_id})"


class TestSeatManager:
    def setup_method(self):
        self.canteen = Canteen(1, "测试食堂", total_seats=5)
        self.manager = SeatManager(self.canteen)
        # 预先创建一些用户
        self.user1 = MockUser("U1")
        self.user2 = MockUser("U2")
        self.user3 = MockUser("U3")

    # ---------- 辅助方法 ----------
    def test_get_seat_exists(self):
        seat = self.manager._get_seat(3)
        assert seat is not None
        assert seat.seat_id == 3

    def test_get_seat_not_exists(self):
        assert self.manager._get_seat(99) is None

    # ---------- assign_seat: 就近策略 ----------
    def test_assign_nearest_first_seat(self):
        seat = self.manager.assign_seat(self.user1, strategy='nearest')
        assert seat is not None
        assert seat.seat_id == 1                # 最小编号的空位
        assert seat.is_occupied is True
        assert seat.occupant == self.user1
        assert self.user1.current_seat == seat

    def test_assign_nearest_second_seat(self):
        # 先占 1 号座位
        self.manager.assign_seat(self.user1, strategy='nearest')
        seat = self.manager.assign_seat(self.user2, strategy='nearest')
        assert seat.seat_id == 2              # 1 已被占，应取 2
        assert self.user2.current_seat == seat

    def test_assign_nearest_full(self):
        # 占满所有 5 个座位
        for i in range(5):
            user = MockUser(f"U{i}")
            assert self.manager.assign_seat(user, 'nearest') is not None
        # 第 6 个用户应无法分配
        user6 = MockUser("U6")
        assert self.manager.assign_seat(user6, 'nearest') is None

    # ---------- assign_seat: 随机策略 ----------
    def test_assign_random_returns_available_seat(self):
        # 固定随机种子保证可重复
        with patch('random.choice') as mock_choice:
            seat3 = self.canteen.seats[2]  # seat_id = 3
            mock_choice.return_value = seat3
            seat = self.manager.assign_seat(self.user1, strategy='random')
            assert seat == seat3
            mock_choice.assert_called_once()
            # 确认座位被占用
            assert seat3.is_occupied is True
            assert self.user1.current_seat == seat3

    def test_assign_random_full(self):
        # 占满所有座位
        for i in range(5):
            self.manager.assign_seat(MockUser(f"U{i}"))
        user6 = MockUser("U6")
        assert self.manager.assign_seat(user6, strategy='random') is None

    # ---------- assign_specific_seat ----------
    def test_assign_specific_seat_success(self):
        seat = self.manager.assign_specific_seat(self.user1, 2)
        assert seat is not None
        assert seat.seat_id == 2
        assert seat.is_occupied is True
        assert self.user1.current_seat == seat

    def test_assign_specific_seat_already_occupied(self):
        self.manager.assign_seat(self.user1, 'nearest')  # 占 1 号
        # 尝试将 user2 分配到已经占用 1 号
        seat = self.manager.assign_specific_seat(self.user2, 1)
        assert seat is None
        # user2 不应该有座位
        assert self.user2.current_seat is None

    def test_assign_specific_seat_invalid_id(self):
        seat = self.manager.assign_specific_seat(self.user1, 999)
        assert seat is None

    # ---------- release_seat (通过用户) ----------
    def test_release_seat_success(self):
        self.manager.assign_seat(self.user1, 'nearest')
        result = self.manager.release_seat(self.user1)
        assert result is True
        assert self.user1.current_seat is None
        # 座位恢复空闲
        assert self.canteen.seats[0].is_occupied is False
        assert self.canteen.seats[0].occupant is None

    def test_release_seat_no_current_seat(self):
        # 用户没有座位时释放应返回 False
        assert self.manager.release_seat(self.user1) is False

    # ---------- release_seat_by_id ----------
    def test_release_by_id_success(self):
        self.manager.assign_seat(self.user1, 'nearest')  # 占 1 号
        result = self.manager.release_seat_by_id(1)
        assert result is True
        assert self.user1.current_seat is None
        assert self.canteen.seats[0].is_occupied is False

    def test_release_by_id_already_empty(self):
        result = self.manager.release_seat_by_id(1)
        assert result is False

    def test_release_by_id_invalid(self):
        result = self.manager.release_seat_by_id(99)
        assert result is False

    # ---------- get_status ----------
    def test_get_status_empty(self):
        status = self.manager.get_status()
        assert status == {
            'total': 5,
            'occupied': 0,
            'available': 5,
            'rate': 0.0
        }

    def test_get_status_partial(self):
        self.manager.assign_seat(self.user1)
        self.manager.assign_seat(self.user2)
        status = self.manager.get_status()
        assert status['occupied'] == 2
        assert status['available'] == 3
        assert status['rate'] == 40.0

    def test_get_status_full(self):
        for i in range(5):
            self.manager.assign_seat(MockUser(f"U{i}"))
        status = self.manager.get_status()
        assert status['occupied'] == 5
        assert status['available'] == 0
        assert status['rate'] == 100.0

    # ---------- print 方法（仅检查无异常，不校验具体输出） ----------
    def test_print_status(self, capsys):
        self.manager.assign_seat(self.user1)
        self.manager.print_status()
        captured = capsys.readouterr().out
        assert "测试食堂" in captured
        assert "总座位: 5" in captured
        assert "已占用: 1" in captured

    def test_print_all_seats(self, capsys):
        self.manager.print_all_seats()
        captured = capsys.readouterr().out
        # 应打印 5 个座位状态
        assert captured.count("座位") >= 5