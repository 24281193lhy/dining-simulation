from utils.display import clear_screen, print_table, print_info, print_error, print_warning, print_header
from ui.common import get_user_input
import time
import random

class StudentUI:
    def __init__(self, canteen_manager, queue_engine, seat_manager, storage):
        """
        注入业务层和数据层对象（此处为模拟对象）
        """
        self.canteen_manager = canteen_manager
        self.queue_engine = queue_engine
        self.seat_manager = seat_manager
        self.storage = storage
        self.current_user = None   # 当前登录用户 {"id": xxx, "type": "student"/"teacher"}
        self.current_canteen = None # 当前选择的食堂

    def run(self):
        """学生主流程"""
        if not self.login():
            return
        while True:
            clear_screen()
            self.show_canteen_overview()  # 显示所有食堂概况
            print("\n--- 学生功能菜单 ---")
            print("1. 加入队列并点餐")
            print("2. 查看我的排队状态")
            print("3. 手动选座")
            print("4. 离开食堂")
            print("0. 退出登录")
            choice = get_user_input("请选择：", ["1","2","3","4","0"])
            if choice == "1":
                self.join_queue_and_order()
            elif choice == "2":
                self.check_queue_status()
            elif choice == "3":
                self.select_seat()
            elif choice == "4":
                self.leave_canteen()
            elif choice == "0":
                break

    def login(self):
        """身份识别"""
        print_header("学生/教师登录")
        user_id = get_user_input("请输入学号/工号：", allow_empty=False)
        user_type = get_user_input("请选择身份（1-学生，2-教师）：", ["1","2"])
        user_type = "student" if user_type == "1" else "teacher"
        # 调用身份验证接口（模拟）
        self.current_user = self.canteen_manager.authenticate(user_id, user_type)
        if self.current_user:
            print_info(f"欢迎 {self.current_user['name']}（{self.current_user['type']}）！")
            input("按回车继续...")
            return True
        else:
            print_error("身份验证失败！")
            input("按回车返回...")
            return False

    def show_canteen_overview(self):
        """展示所有食堂实时概况"""
        canteens = self.canteen_manager.get_all_canteens_status()
        print_header("食堂实时概况")
        for canteen in canteens:
            print(f"\n【{canteen['name']}】  空座位数: {canteen['free_seats']}  总排队人数: {canteen['total_queue']}")
            headers = ["窗口ID", "窗口名称", "类型", "排队人数", "预计等待(秒)"]
            rows = []
            for win in canteen['windows']:
                rows.append([win['id'], win['name'], win['type'], win['queue_len'], win['wait_time']])
            print_table(headers, rows)

    def join_queue_and_order(self):
        """加入队列并点餐"""
        # 选择食堂
        canteens = self.canteen_manager.get_all_canteens_status()
        print("\n可选食堂：")
        for i, c in enumerate(canteens, 1):
            print(f"{i}. {c['name']}")
        choice = get_user_input("请选择食堂序号：", [str(i) for i in range(1, len(canteens)+1)])
        selected_canteen = canteens[int(choice)-1]
        # 选择窗口（需根据身份过滤教工专窗）
        windows = selected_canteen['windows']
        if self.current_user['type'] == 'student':
            windows = [w for w in windows if w['type'] != '教工专窗']
        if not windows:
            print_error("没有可用的普通窗口，请联系管理员。")
            input("按回车返回...")
            return
        print("\n可用窗口：")
        for i, w in enumerate(windows, 1):
            print(f"{i}. {w['name']}（排队{w['queue_len']}人，预计等待{w['wait_time']}秒）")
        win_choice = get_user_input("请选择窗口序号：", [str(i) for i in range(1, len(windows)+1)])
        window = windows[int(win_choice)-1]
        # 加入队列
        result = self.queue_engine.join_queue(self.current_user['id'], window['id'])
        if result['success']:
            print_info(f"成功加入 {selected_canteen['name']} - {window['name']} 队列，预计等待 {result['wait_time']} 秒。")
            # 模拟排队过程（实际应该由事件驱动，这里简化）
            print_info("请稍候，正在排队打饭...")
            time.sleep(2)  # 模拟等待
            # 打饭完成，触发点餐
            dishes = self.canteen_manager.get_window_dishes(window['id'])
            if dishes:
                print("\n--- 窗口菜品 ---")
                for i, dish in enumerate(dishes, 1):
                    print(f"{i}. {dish['name']}  ¥{dish['price']}")
                dish_choice = get_user_input("请选择菜品序号：", [str(i) for i in range(1, len(dishes)+1)])
                selected_dish = dishes[int(dish_choice)-1]
                print_info(f"您已点餐：{selected_dish['name']}，请等待取餐。")
                # 模拟取餐完成
                time.sleep(1)
            # 打饭完成，分配座位
            seat = self.seat_manager.assign_seat(self.current_user['id'], selected_canteen['id'])
            if seat:
                print_info(f"系统自动为您分配座位：{seat['id']}（{seat['location']}）")
                self.current_canteen = selected_canteen
            else:
                print_warning("暂时没有空闲座位，请稍后手动选座。")
                self.current_canteen = None
        else:
            print_error(result['message'])
        input("按回车继续...")

    def check_queue_status(self):
        """查看当前用户的排队状态（模拟）"""
        status = self.queue_engine.get_user_queue_status(self.current_user['id'])
        if status:
            print_info(f"您正在排队：窗口 {status['window_name']}，前面还有 {status['ahead']} 人，预计还需 {status['wait_time']} 秒。")
        else:
            print_warning("您当前没有排队。")
        input("按回车继续...")

    def select_seat(self):
        """手动选座"""
        if not self.current_canteen:
            print_error("请先完成打饭后再选座。")
            input("按回车返回...")
            return
        seats = self.seat_manager.get_free_seats(self.current_canteen['id'])
        if not seats:
            print_warning("当前没有空闲座位。")
        else:
            print("\n空闲座位列表：")
            for i, seat in enumerate(seats, 1):
                print(f"{i}. {seat['id']} - {seat['location']}")
            choice = get_user_input("请选择座位序号：", [str(i) for i in range(1, len(seats)+1)])
            selected = seats[int(choice)-1]
            if self.seat_manager.occupy_seat(self.current_user['id'], selected['id']):
                print_info(f"您已成功选择座位 {selected['id']}。")
            else:
                print_error("选座失败，可能已被占用。")
        input("按回车继续...")

    def leave_canteen(self):
        """离开食堂，释放座位并记录"""
        if self.current_canteen:
            self.seat_manager.release_seat(self.current_user['id'])
            self.storage.log_event("离开", self.current_user['id'], f"离开{self.current_canteen['name']}")
            print_info("您已离开食堂，感谢用餐！")
            self.current_canteen = None
        else:
            print_warning("您尚未入座或已离开。")
        input("按回车继续...")