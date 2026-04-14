# 2.1 食堂管理模块
from collections import deque


class Dish:
    """菜品"""
    def __init__(self, name, price):
        self.name = name
        self.price = price

    def __str__(self):
        return f"{self.name} (¥{self.price:.1f})"


class Window:
    """打饭窗口"""
    def __init__(self, window_id, name, speed=1.0, window_type='normal'):
        self.window_id = window_id
        self.name = name
        self.speed = speed          # 每位顾客打饭所需分钟数
        self.window_type = window_type  # 'normal' 普通窗口 / 'teacher' 教工专窗
        self.dishes = []            # 菜品列表
        self.queue = deque()        # 排队队列
        self.is_open = True         # 窗口是否开放
        self.serving_user = None    # 当前正在打饭的用户
        self.serve_end_time = 0     # 当前服务结束时间（仿真分钟）
        self.total_served = 0       # 累计服务人数

    def add_dish(self, dish):
        self.dishes.append(dish)

    def remove_dish(self, dish_name):
        self.dishes = [d for d in self.dishes if d.name != dish_name]

    def queue_length(self):
        return len(self.queue)

    def is_accessible_by(self, user):
        """判断用户是否能使用该窗口"""
        if self.window_type == 'teacher':
            return user.is_teacher()
        return True

    def __str__(self):
        status = '开放' if self.is_open else '关闭'
        return (f"窗口[{self.window_id}] {self.name} "
                f"| 类型:{self.window_type} | 速度:{self.speed}min/人 "
                f"| 队列:{self.queue_length()}人 | {status}")


class Seat:
    """座位"""
    def __init__(self, seat_id):
        self.seat_id = seat_id
        self.is_occupied = False
        self.occupant = None  # 占用该座位的用户

    def occupy(self, user):
        self.is_occupied = True
        self.occupant = user

    def release(self):
        self.is_occupied = False
        self.occupant = None

    def __str__(self):
        state = f"[{self.occupant.user_id}]" if self.is_occupied else "空闲"
        return f"座位{self.seat_id}: {state}"


class Canteen:
    """食堂"""
    def __init__(self, canteen_id, name, total_seats=100):
        self.canteen_id = canteen_id
        self.name = name
        self.windows = {}       # window_id -> Window
        self.seats = [Seat(i) for i in range(1, total_seats + 1)]
        self.next_window_id = 1

    def get_accessible_windows(self, user):
        """返回用户可见的窗口列表"""
        return [w for w in self.windows.values() if w.is_accessible_by(user)]

    def add_window(self, name, speed=1.0, window_type='normal'):
        wid = self.next_window_id
        window = Window(wid, name, speed, window_type)
        self.windows[wid] = window
        self.next_window_id += 1
        return window

    def remove_window(self, window_id):
        if window_id in self.windows:
            del self.windows[window_id]

    def get_window(self, window_id):
        return self.windows.get(window_id)

    def available_seats(self):
        return [s for s in self.seats if not s.is_occupied]

    def occupied_seats(self):
        return [s for s in self.seats if s.is_occupied]

    def seat_status(self):
        total = len(self.seats)
        occupied = len(self.occupied_seats())
        return f"座位: {occupied}/{total} 已占用"

    def __str__(self):
        return (f"食堂[{self.canteen_id}] {self.name} "
                f"| 窗口数:{len(self.windows)} "
                f"| {self.seat_status()}")


class CanteenManager:
    """食堂管理器，管理所有食堂"""
    def __init__(self):
        self.canteens = {}      # canteen_id -> Canteen
        self.next_canteen_id = 1

    def add_canteen(self, name, total_seats=100):
        cid = self.next_canteen_id
        canteen = Canteen(cid, name, total_seats)
        self.canteens[cid] = canteen
        self.next_canteen_id += 1
        #print(f"✅ 食堂'{name}'已添加，ID={cid}")
        return canteen

    def remove_canteen(self, canteen_id):
        if canteen_id in self.canteens:
            name = self.canteens[canteen_id].name
            del self.canteens[canteen_id]
            print(f"🗑️ 食堂'{name}'已删除")
        else:
            print(f"❌ 未找到食堂ID={canteen_id}")

    def get_canteen(self, canteen_id):
        return self.canteens.get(canteen_id)

    def list_canteens(self):
        if not self.canteens:
            print("当前没有食堂")
            return
        for canteen in self.canteens.values():
            print(canteen)

    def get_all_windows(self):
        """获取所有食堂的所有窗口"""
        result = []
        for canteen in self.canteens.values():
            result.extend(canteen.windows.values())
        return result