# ui/admin_ui.py
from utils.display import clear_screen, print_table, print_info, print_error, print_header, print_warning
from src.ui.common import get_user_input
import time

class AdminUI:
    def __init__(self, canteen_manager, storage, admin_manager):
        self.canteen_manager = canteen_manager
        self.storage = storage
        self.admin_manager = admin_manager
        self.current_admin = None   # 记录当前登录的管理员用户名

    def login(self):
        """管理员登录验证"""
        print_header("管理员登录")
        username = get_user_input("请输入用户名：", allow_empty=False)
        password = get_user_input("请输入密码：", allow_empty=False)
        if self.admin_manager.authenticate(username, password):
            self.current_admin = username
            print_info(f"欢迎，管理员 {username}！")
            input("按回车继续...")
            return True
        else:
            print_error("用户名或密码错误！")
            input("按回车返回...")
            return False

    def run(self):
        """管理员主菜单（需要先登录）"""
        if not self.login():
            return
        while True:
            clear_screen()
            print_header("管理员控制台")
            print("1. 食堂与窗口配置")
            print("2. 实时监控（动态刷新）")
            print("3. 查看统计报表")
            print("4. 修改密码")          # 新增选项
            print("0. 退出管理员模式")
            choice = get_user_input("请选择：", ["1","2","3","4","0"])
            if choice == "1":
                self.config_menu()
            elif choice == "2":
                self.realtime_monitor()
            elif choice == "3":
                self.show_statistics()
            elif choice == "4":
                self.change_password()
            elif choice == "0":
                break

    def change_password(self):
        """修改密码"""
        print_header("修改密码")
        old_pwd = get_user_input("请输入原密码：", allow_empty=False)
        new_pwd = get_user_input("请输入新密码：", allow_empty=False)
        confirm = get_user_input("请再次输入新密码：", allow_empty=False)
        if new_pwd != confirm:
            print_error("两次输入的新密码不一致！")
        elif self.admin_manager.change_password(self.current_admin, old_pwd, new_pwd):
            print_info("密码修改成功！")
        else:
            print_error("原密码错误，修改失败！")
        input("按回车继续...")

    def config_menu(self):
        """配置菜单"""
        while True:
            clear_screen()
            print_header("食堂与窗口配置")
            print("1. 查看所有食堂配置")
            print("2. 添加/修改食堂")
            print("3. 添加/修改窗口")
            print("4. 配置窗口菜品")
            print("0. 返回上级")
            choice = get_user_input("请选择：", ["1","2","3","4","0"])
            if choice == "1":
                self.view_canteens()
            elif choice == "2":
                self.edit_canteen()
            elif choice == "3":
                self.edit_window()
            elif choice == "4":
                self.config_dishes()
            elif choice == "0":
                break

    def view_canteens(self):
        """查看所有食堂配置"""
        canteens = self.canteen_manager.get_all_canteens_config()
        for c in canteens:
            print(f"\n食堂ID: {c['id']}  名称: {c['name']}  总座位: {c['total_seats']}")
            headers = ["窗口ID", "名称", "类型", "打饭速度(秒/人)", "菜品数"]
            rows = []
            for w in c['windows']:
                rows.append([w['id'], w['name'], w['type'], w['speed'], len(w['dishes'])])
            if rows:
                print_table(headers, rows)
            else:
                print_warning("暂无窗口")
        input("按回车继续...")

    def edit_canteen(self):
        """添加新食堂"""
        print_header("添加新食堂")
        name = get_user_input("请输入食堂名称：", allow_empty=False)
        seats = get_user_input("请输入座位总数（默认100）：", allow_empty=True)
        total_seats = int(seats) if seats.isdigit() else 100
        canteen_id = self.canteen_manager.add_canteen(name, total_seats)
        print_info(f"食堂 '{name}' 添加成功，ID={canteen_id}")
        input("按回车返回...")

    def edit_window(self):
        """为已有食堂添加新窗口"""
        print_header("添加新窗口")
        canteens = self.canteen_manager.list_canteens()
        if not canteens:
            print_error("没有食堂，请先添加食堂。")
            input("按回车返回...")
            return
        print("现有食堂：")
        for c in canteens:
            print(f"ID: {c['id']} - {c['name']}")
        cid_str = get_user_input("请输入食堂ID：", allow_empty=False)
        if not cid_str.isdigit():
            print_error("食堂ID必须是数字。")
            input("按回车返回...")
            return
        cid = int(cid_str)
        name = get_user_input("请输入窗口名称：", allow_empty=False)
        speed_str = get_user_input("请输入打饭速度（分钟/人，默认1.0）：", allow_empty=True)
        speed = float(speed_str) if speed_str else 1.0
        win_type = get_user_input("窗口类型（1-普通，2-教工专窗）：", ["1", "2"])
        window_type = "normal" if win_type == "1" else "teacher"
        global_id = self.canteen_manager.add_window(cid, name, speed, window_type)
        if global_id:
            print_info(f"窗口 '{name}' 添加成功，全局ID={global_id}")
        else:
            print_error("添加失败，请检查食堂ID是否正确。")
        input("按回车返回...")

    def config_dishes(self):
        """为窗口添加菜品"""
        print_header("配置窗口菜品")
        # 先列出所有窗口供选择
        all_windows = self.canteen_manager.get_all_canteens_config()
        if not all_windows:
            print_error("没有食堂和窗口，请先添加。")
            input("按回车返回...")
            return
        print("现有窗口：")
        for canteen in all_windows:
            for win in canteen['windows']:
                print(f"窗口ID: {win['id']} - {canteen['name']} - {win['name']} (当前菜品: {win['dishes']})")
        win_id = get_user_input("请输入要添加菜品的窗口ID：", allow_empty=False)
        dish_name = get_user_input("请输入菜品名称：", allow_empty=False)
        price_str = get_user_input("请输入价格（元）：", allow_empty=False)
        if not price_str.replace('.', '').isdigit():
            print_error("价格必须是数字。")
            input("按回车返回...")
            return
        price = float(price_str)
        success = self.canteen_manager.add_dish(win_id, dish_name, price)
        if success:
            print_info(f"菜品 '{dish_name}' 已添加到窗口 {win_id}")
        else:
            print_error("添加失败，请检查窗口ID是否正确。")
        input("按回车返回...")

    def realtime_monitor(self):
        """实时监控，每秒刷新显示核心运营数据"""
        print_header("实时监控（按 Ctrl+C 停止）")
        try:
            while True:
                clear_screen()
                print_header("实时运营数据")
                canteens = self.canteen_manager.get_all_canteens_status()
                for canteen in canteens:
                    print(f"\n【{canteen['name']}】 空座位: {canteen['free_seats']}  总排队: {canteen['total_queue']}")
                    headers = ["窗口", "类型", "排队人数", "打饭进度", "预计等待(秒)"]
                    rows = []
                    for w in canteen['windows']:
                        progress = "服务中" if w['queue_len'] > 0 else "空闲"
                        rows.append([w['name'], w['type'], w['queue_len'], progress, w['wait_time']])
                    print_table(headers, rows)
                time.sleep(1)
        except KeyboardInterrupt:
            print_info("\n停止监控，返回上级菜单。")
            input("按回车继续...")

    def show_statistics(self):
        """查看统计报表（从存储层获取）"""
        stats = self.storage.get_statistics()
        print_header("数据统计报表")
        print(f"平均排队时间: {stats['avg_wait_time']} 秒")
        print(f"窗口繁忙度: {stats['window_busy_rate']}")
        print(f"高峰时段: {stats['peak_hours']}")
        print(f"总服务人数: {stats['total_served']}")
        input("按回车继续...")