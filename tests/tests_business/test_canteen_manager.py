# 文件: tests/test_canteen_manager.py

import pytest
from business.canteen_manager import (
    Dish, Window, Seat, Canteen, CanteenManager
)

# 创建一个简单的 Mock 用户类，用于测试 Window 的 is_accessible_by 和 Seat 的占用
class MockUser:
    def __init__(self, user_id, is_teacher=False):
        self.user_id = user_id
        self.is_teacher_flag = is_teacher

    def is_teacher(self):
        return self.is_teacher_flag


# -------------------- Dish --------------------
class TestDish:
    def test_dish_creation(self):
        d = Dish("红烧肉", 12.5)
        assert d.name == "红烧肉"
        assert d.price == 12.5

    def test_dish_str(self):
        d = Dish("番茄炒蛋", 5.0)
        assert str(d) == "番茄炒蛋 (¥5.0)"


# -------------------- Window --------------------
class TestWindow:
    def setup_method(self):
        self.window = Window(1, "一号窗", speed=1.5, window_type='normal')

    def test_init(self):
        assert self.window.window_id == 1
        assert self.window.name == "一号窗"
        assert self.window.speed == 1.5
        assert self.window.window_type == 'normal'
        assert self.window.is_open is True
        assert self.window.serve_end_time == 0
        assert self.window.total_served == 0
        assert self.window.queue_length() == 0
        assert self.window.serving_user is None

    def test_add_dish(self):
        d = Dish("宫保鸡丁", 15)
        self.window.add_dish(d)
        assert len(self.window.dishes) == 1
        assert self.window.dishes[0].name == "宫保鸡丁"

    def test_remove_dish(self):
        d1 = Dish("鱼香肉丝", 14)
        d2 = Dish("麻婆豆腐", 10)
        self.window.add_dish(d1)
        self.window.add_dish(d2)
        self.window.remove_dish("鱼香肉丝")
        assert len(self.window.dishes) == 1
        assert self.window.dishes[0].name == "麻婆豆腐"

    def test_remove_nonexistent_dish(self):
        self.window.add_dish(Dish("青菜", 4))
        # 不会崩溃，只是列表不变
        self.window.remove_dish("不存在")
        assert len(self.window.dishes) == 1

    def test_queue_length(self):
        # 模拟往队列里添加一些东西（实际队列是 deque，但 Window 没有提供 enqueue 方法，
        # 需要在其他模块里操作，这里只测初始状态）
        assert self.window.queue_length() == 0

    def test_is_accessible_by_normal(self):
        student = MockUser("S001", is_teacher=False)
        teacher = MockUser("T001", is_teacher=True)
        # normal 窗口所有人都可以
        assert self.window.is_accessible_by(student) is True
        assert self.window.is_accessible_by(teacher) is True

    def test_is_accessible_by_teacher_window(self):
        teacher_window = Window(2, "教工窗口", window_type='teacher')
        student = MockUser("S002", is_teacher=False)
        teacher = MockUser("T002", is_teacher=True)
        assert teacher_window.is_accessible_by(student) is False
        assert teacher_window.is_accessible_by(teacher) is True

    def test_str_representation(self):
        s = str(self.window)
        assert "窗口[1]" in s
        assert "一号窗" in s
        assert "normal" in s
        assert "开放" in s


# -------------------- Seat --------------------
class TestSeat:
    def test_init(self):
        seat = Seat(10)
        assert seat.seat_id == 10
        assert seat.is_occupied is False
        assert seat.occupant is None

    def test_occupy_and_release(self):
        seat = Seat(5)
        user = MockUser("U1")
        seat.occupy(user)
        assert seat.is_occupied is True
        assert seat.occupant == user

        seat.release()
        assert seat.is_occupied is False
        assert seat.occupant is None

    def test_str(self):
        seat = Seat(1)
        assert "空闲" in str(seat)

        user = MockUser("U2")
        seat.occupy(user)
        assert "[U2]" in str(seat)


# -------------------- Canteen --------------------
class TestCanteen:
    def setup_method(self):
        self.canteen = Canteen(1, "测试食堂", total_seats=5)

    def test_init(self):
        assert self.canteen.canteen_id == 1
        assert self.canteen.name == "测试食堂"
        assert len(self.canteen.seats) == 5
        assert self.canteen.next_window_id == 1

    def test_add_window(self):
        w = self.canteen.add_window("面馆", speed=2.0, window_type='normal')
        assert self.canteen.next_window_id == 2
        assert w.window_id == 1
        assert w.name == "面馆"
        assert len(self.canteen.windows) == 1

    def test_get_accessible_windows(self):
        # 添加一个普通窗，一个教工窗
        self.canteen.add_window("普通窗", window_type='normal')
        self.canteen.add_window("教工窗", window_type='teacher')
        student = MockUser("S", is_teacher=False)
        teacher = MockUser("T", is_teacher=True)

        accessible_student = self.canteen.get_accessible_windows(student)
        assert len(accessible_student) == 1
        assert accessible_student[0].name == "普通窗"

        accessible_teacher = self.canteen.get_accessible_windows(teacher)
        assert len(accessible_teacher) == 2

    def test_remove_window(self):
        self.canteen.add_window("窗口A")
        assert len(self.canteen.windows) == 1
        self.canteen.remove_window(1)
        assert len(self.canteen.windows) == 0
        # 删除不存在的 ID 不会崩溃
        self.canteen.remove_window(999)

    def test_get_window(self):
        w = self.canteen.add_window("测试窗")
        assert self.canteen.get_window(1) == w
        assert self.canteen.get_window(999) is None

    def test_available_and_occupied_seats(self):
        assert len(self.canteen.available_seats()) == 5
        assert len(self.canteen.occupied_seats()) == 0

        user = MockUser("U")
        self.canteen.seats[0].occupy(user)
        self.canteen.seats[2].occupy(user)

        assert len(self.canteen.available_seats()) == 3
        assert len(self.canteen.occupied_seats()) == 2

    def test_seat_status(self):
        s = self.canteen.seat_status()
        assert "0/5" in s
        self.canteen.seats[0].occupy(MockUser("U"))
        assert "1/5" in self.canteen.seat_status()

    def test_str(self):
        s = str(self.canteen)
        assert "食堂[1]" in s
        assert "测试食堂" in s
        assert "窗口数:0" in s


# -------------------- CanteenManager --------------------
class TestCanteenManager:
    def setup_method(self):
        self.manager = CanteenManager()

    def test_add_canteen(self):
        c = self.manager.add_canteen("一食堂", total_seats=200)
        assert c.canteen_id == 1
        assert c.name == "一食堂"
        assert len(c.seats) == 200
        assert self.manager.next_canteen_id == 2

    def test_add_multiple_canteens(self):
        c1 = self.manager.add_canteen("食堂A")
        c2 = self.manager.add_canteen("食堂B")
        assert c1.canteen_id == 1
        assert c2.canteen_id == 2
        assert len(self.manager.canteens) == 2

    def test_remove_canteen(self):
        self.manager.add_canteen("临时食堂")
        self.manager.remove_canteen(1)
        assert len(self.manager.canteens) == 0

    def test_remove_nonexistent_canteen(self):
        # 不会崩溃，会打印错误消息（可以在测试里忽略）
        self.manager.remove_canteen(999)
        assert len(self.manager.canteens) == 0

    def test_get_canteen(self):
        c = self.manager.add_canteen("食堂X")
        assert self.manager.get_canteen(1) == c
        assert self.manager.get_canteen(2) is None

    def test_list_canteens_empty(self, capsys):
        self.manager.list_canteens()
        captured = capsys.readouterr().out
        assert "当前没有食堂" in captured

    def test_list_canteens_nonempty(self, capsys):
        self.manager.add_canteen("食堂Y")
        self.manager.list_canteens()
        captured = capsys.readouterr().out
        assert "食堂Y" in captured

    def test_get_all_windows(self):
        c1 = self.manager.add_canteen("C1")
        c2 = self.manager.add_canteen("C2")
        c1.add_window("W1")
        c1.add_window("W2")
        c2.add_window("W3")
        all_windows = self.manager.get_all_windows()
        assert len(all_windows) == 3
        names = {w.name for w in all_windows}
        assert names == {"W1", "W2", "W3"}