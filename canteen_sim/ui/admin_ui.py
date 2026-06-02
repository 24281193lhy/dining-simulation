# ui/admin_ui.py
from canteen_sim.utils.display import clear_screen, print_table, print_info, print_error, print_header, print_warning
from canteen_sim.ui.common import get_user_input
import time
from canteen_sim.data.statistics import StatisticsAnalyzer


class AdminUI:
    """管理员命令行界面，依赖 UIAdapter 与调度器"""

    def __init__(self, adapter, storage, scheduler, admin_manager):
        """
        :param adapter: UIAdapter 实例（提供所有业务接口）
        :param storage: SimulationStorage 实例（用于统计分析）
        :param scheduler: EventScheduler 实例（用于查看运行状态）
        :param admin_manager: 管理员认证管理器
        """
        self.adapter = adapter         # 替代直接使用 canteen_manager
        self.storage = storage
        self.scheduler = scheduler     # 用于获取仿真状态
        self.admin_manager = admin_manager
        self.current_admin = None

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
        if not self.login():
            return
        while True:
            clear_screen()
            print_header("管理员控制台")
            print("1. 食堂与窗口配置")
            print("2. 实时监控（动态刷新）")
            print("3. 查看统计报表")
            print("4. 修改密码")
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
        # 通过 adapter 获取配置
        config = self.adapter.get_all_canteens_config()
        if not config:
            print_warning("暂无食堂配置")
            input("按回车继续...")
            return
        for c in config:
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
        print_header("添加新食堂")
        # 检查仿真是否运行且在运行中不可添加
        if self.scheduler and self.scheduler.is_running and not self.scheduler.paused:
            print_error("仿真正在运行，请先暂停或停止仿真再添加食堂。")
            input("按回车返回...")
            return
        name = get_user_input("请输入食堂名称：", allow_empty=False)
        seats = get_user_input("请输入座位总数（默认100）：", allow_empty=True)
        total_seats = int(seats) if seats.isdigit() else 100
        cid = self.adapter.add_canteen(name, total_seats)
        print_info(f"食堂 '{name}' 添加成功，ID={cid}")
        input("按回车返回...")

    def edit_window(self):
        print_header("添加新窗口")
        if self.scheduler and self.scheduler.is_running and not self.scheduler.paused:
            print_error("仿真正在运行，请先暂停或停止仿真再添加窗口。")
            input("按回车返回...")
            return
        # 列出已有食堂
        canteens = self.adapter.list_canteens()
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
        global_id = self.adapter.add_window(cid, name, speed, window_type)
        if global_id:
            print_info(f"窗口 '{name}' 添加成功，全局ID={global_id}")
        else:
            print_error("添加失败，请检查食堂ID是否正确。")
        input("按回车返回...")

    def config_dishes(self):
        print_header("配置窗口菜品")
        if self.scheduler and self.scheduler.is_running and not self.scheduler.paused:
            print_error("仿真正在运行，请先暂停或停止仿真再添加菜品。")
            input("按回车返回...")
            return
        # 获取所有窗口
        all_canteens = self.adapter.get_all_canteens_config()
        if not all_canteens:
            print_error("没有食堂和窗口，请先添加。")
            input("按回车返回...")
            return
        print("现有窗口：")
        for canteen in all_canteens:
            for win in canteen['windows']:
                print(f"窗口ID: {win['id']} - {canteen['name']} - {win['name']} (当前菜品: {win['dishes']})")
        win_id = get_user_input("请输入要添加菜品的窗口ID：", allow_empty=False)
        dish_name = get_user_input("请输入菜品名称：", allow_empty=False)
        price_str = get_user_input("请输入价格（元）：", allow_empty=False)
        try:
            price = float(price_str)
        except ValueError:
            print_error("价格必须是数字。")
            input("按回车返回...")
            return
        success = self.adapter.add_dish(win_id, dish_name, price)
        if success:
            print_info(f"菜品 '{dish_name}' 已添加到窗口 {win_id}")
        else:
            print_error("添加失败，请检查窗口ID是否正确。")
        input("按回车返回...")

    def realtime_monitor(self):
        """实时监控，使用 adapter 获取状态"""
        print_header("实时监控（按 Ctrl+C 停止）")
        try:
            while True:
                clear_screen()
                print_header("实时运营数据")
                # 获取所有食堂状态（不传入用户，显示全量）
                statuses = self.adapter.get_all_canteens_status()
                if not statuses:
                    print_warning("暂无数据")
                for canteen in statuses:
                    print(f"\n【{canteen['name']}】 空座位: {canteen['free_seats']}  总排队: {canteen['total_queue']}")
                    headers = ["窗口", "类型", "排队人数", "预计等待(秒)"]
                    rows = []
                    for w in canteen['windows']:
                        rows.append([w['name'], w['type'], w['queue_len'], w['wait_time']])
                    print_table(headers, rows)
                time.sleep(1)
        except KeyboardInterrupt:
            print_info("\n停止监控，返回上级菜单。")
            input("按回车继续...")

    def show_statistics(self):
        """从存储中生成并显示统计"""
        print_header("数据统计报表")
        try:
            analyzer = StatisticsAnalyzer(self.storage)
            stats = analyzer.compute_all()
            print(f"平均等待时间: {stats['avg_wait_time']:.2f} 分钟")
            print(f"总服务人数: {stats['total_served']}")
            # 窗口繁忙率
            busy = stats.get('window_busy_rate', {})
            if busy:
                print("窗口繁忙度（人次/分钟）：")
                for win_id, rate in busy.items():
                    print(f"  {win_id}: {rate:.3f}")
            # 座位占用率
            seat_occ = stats.get('avg_seat_occupancy', {})
            if seat_occ:
                print("食堂平均座位占用率（%）：")
                for cid, occ in seat_occ.items():
                    print(f"  食堂 {cid}: {occ:.1f}%")
            # 高峰时段
            peaks = stats.get('peak_hours', [])
            if peaks:
                print("排队高峰时段：")
                for p in peaks:
                    print(f"  {p['start_time']}-{p['end_time']} 分钟，排队人数: {p['queue_length']}")
        except Exception as e:
            print_error(f"统计生成失败: {e}")
        input("按回车继续...")
        #A