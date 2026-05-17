from utils.display import clear_screen, print_table, print_info, print_error, print_warning, print_header
from ui.common import get_user_input, validate_student_id, validate_teacher_id
import time

class StudentUI:
    """
    学生/教师终端交互界面，依赖 UIAdapter 提供数据与操作，
    依赖 EventScheduler 获取仿真状态。
    """

    def __init__(self, adapter, scheduler, storage):
        """
        :param adapter: UIAdapter 实例（所有业务接口的统一入口）
        :param scheduler: EventScheduler 实例（用于检查仿真运行状态）
        :param storage: SimulationStorage 实例（用于事件记录）
        """
        self.adapter = adapter
        self.scheduler = scheduler
        self.storage = storage
        self.current_user = None        # 登录信息字典 {"id", "name", "type"}
        self.current_user_obj = None    # User 对象（用于权限判断）
        self.current_canteen = None     # 当前所在食堂的简要信息（含 id, name）

    def run(self):
        if not self.login():
            return
        while True:
            clear_screen()
            self.show_canteen_overview()
            print("\n--- 用户功能菜单 ---")
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
        print_header("学生/教师登录")
        while True:
            user_id = get_user_input("请输入学号/工号：", allow_empty=False)
            user_type = get_user_input("请选择身份（1-学生，2-教师）：", ["1","2"])
            role = "student" if user_type == "1" else "teacher"

            # 格式验证
            if role == "student":
                if not validate_student_id(user_id):
                    print_error("学号格式错误！应为8位数字（22-25开头，学院01-50，班级01-20）。")
                    continue
            else:
                if not validate_teacher_id(user_id):
                    print_error("教师工号格式错误！应以 T 开头，后跟至少3位数字。")
                    continue

            # 通过适配器认证/注册
            auth_result = self.adapter.authenticate(user_id, role)
            if auth_result:
                self.current_user = auth_result
                self.current_user_obj = self.adapter.get_user_object(user_id)
                print_info(f"欢迎 {self.current_user['name']}（{self.current_user['type']}）！")
                input("按回车继续...")
                return True
            else:
                print_error("身份验证失败！")
                continue

    def show_canteen_overview(self):
        """显示所有食堂的实时状态（考虑用户权限）"""
        canteens = self.adapter.get_all_canteens_status(user=self.current_user_obj)
        print_header("食堂实时概况")
        if not canteens:
            print_warning("当前没有可访问的食堂或数据。")
            return
        for canteen in canteens:
            print(f"\n【{canteen['name']}】 空座位数: {canteen['free_seats']}  总排队人数: {canteen['total_queue']}")
            headers = ["窗口ID", "窗口名称", "类型", "排队人数", "预计等待(秒)"]
            rows = [[w['id'], w['name'], w['type'], w['queue_len'], w['wait_time']] for w in canteen['windows']]
            if rows:
                print_table(headers, rows)

    def join_queue_and_order(self):
        """排队并模拟点餐过程"""
        # 获取用户可访问的食堂状态
        all_canteens = self.adapter.get_all_canteens_status(user=self.current_user_obj)
        if not all_canteens:
            print_error("没有可用的食堂。")
            input("按回车返回...")
            return

        print("\n可选食堂：")
        for i, c in enumerate(all_canteens, 1):
            print(f"{i}. {c['name']}")
        choice = get_user_input("请选择食堂序号：", [str(i) for i in range(1, len(all_canteens)+1)])
        selected_canteen = all_canteens[int(choice)-1]

        windows = selected_canteen['windows']
        if not windows:
            print_error("没有可用的窗口。")
            input("按回车返回...")
            return

        print("\n可用窗口：")
        for i, w in enumerate(windows, 1):
            print(f"{i}. {w['name']}（排队{w['queue_len']}人，预计等待{w['wait_time']}秒）")
        win_choice = get_user_input("请选择窗口序号：", [str(i) for i in range(1, len(windows)+1)])
        window = windows[int(win_choice)-1]

        # 通过适配器加入队列（传入 user_id 和窗口全局ID）
        result = self.adapter.join_queue(self.current_user['id'], window['id'])
        if result['success']:
            print_info(f"成功加入 {selected_canteen['name']} - {window['name']} 队列，预计等待 {result['wait_time']} 秒。")
            print_info("请稍候，正在排队打饭...")
            time.sleep(2)

            # 展示菜品
            dishes = self.adapter.get_window_dishes(window['id'])
            if dishes:
                print("\n--- 窗口菜品 ---")
                for i, dish in enumerate(dishes, 1):
                    print(f"{i}. {dish['name']} ¥{dish['price']}")
                dish_choice = get_user_input("请选择菜品序号：", [str(i) for i in range(1, len(dishes)+1)])
                selected_dish = dishes[int(dish_choice)-1]
                print_info(f"您已点餐：{selected_dish['name']}，请等待取餐。")
                time.sleep(1)

            # 模拟取餐完成，询问是否入座
            confirm = get_user_input("打饭完成！是否现在入座？(1-自动分配 / 2-手动选座 / 0-暂不入座)：", ["1", "2", "0"])
            self.current_canteen = selected_canteen   # 记录当前食堂（用于后续选座/离席）

            if confirm == "1":
                seat = self.adapter.assign_seat(self.current_user['id'], selected_canteen['id'])
                if seat:
                    print_info(f"已为您分配座位：{seat['id']}（{seat['location']}）")
                else:
                    print_warning("暂时没有空闲座位，请稍后手动选座。")
            elif confirm == "2":
                seats = self.adapter.get_free_seats(selected_canteen['id'])
                if not seats:
                    print_warning("当前没有空闲座位。")
                else:
                    print("\n空闲座位列表：")
                    for i, seat in enumerate(seats, 1):
                        print(f"{i}. {seat['id']} - {seat['location']}")
                    seat_choice = get_user_input("请选择座位序号：", [str(i) for i in range(1, len(seats)+1)])
                    selected = seats[int(seat_choice)-1]
                    if self.adapter.occupy_seat(self.current_user['id'], selected['id']):
                        print_info(f"您已成功选择座位 {selected['id']}。")
                    else:
                        print_error("选座失败，可能已被占用。")
            else:
                print_info("您可以稍后通过「手动选座」入座。")
        else:
            print_error(result['message'])
        input("按回车继续...")

    def check_queue_status(self):
        """查看当前排队状态"""
        status = self.adapter.get_user_queue_status(self.current_user['id'])
        if status:
            print_info(f"您正在排队：窗口 {status['window_name']}，前面还有 {status['ahead']} 人，预计还需 {status['wait_time']} 秒。")
        else:
            print_warning("您当前没有排队。")
        input("按回车继续...")

    def select_seat(self):
        """手动选座（需已打饭完）"""
        if not self.current_canteen:
            print_error("请先完成打饭后再选座。")
            input("按回车返回...")
            return
        seats = self.adapter.get_free_seats(self.current_canteen['id'])
        if not seats:
            print_warning("当前没有空闲座位。")
        else:
            print("\n空闲座位列表：")
            for i, seat in enumerate(seats, 1):
                print(f"{i}. {seat['id']} - {seat['location']}")
            choice = get_user_input("请选择座位序号：", [str(i) for i in range(1, len(seats)+1)])
            selected = seats[int(choice)-1]
            if self.adapter.occupy_seat(self.current_user['id'], selected['id']):
                print_info(f"您已成功选择座位 {selected['id']}。")
            else:
                print_error("选座失败，可能已被占用。")
        input("按回车继续...")

    def leave_canteen(self):
        """离开食堂，释放座位"""
        if self.current_canteen:
            self.adapter.release_seat(self.current_user['id'])
            # 记录离开事件
            self.storage.log_event("leave", self.current_user['id'],
                                   f"离开{self.current_canteen['name']}",
                                   timestamp=self.scheduler.current_time if self.scheduler else None)
            print_info("您已离开食堂，感谢用餐！")
            self.current_canteen = None
        else:
            print_warning("您尚未入座或已离开。")
        input("按回车继续...")