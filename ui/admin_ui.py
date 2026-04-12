from utils.display import clear_screen, print_table, print_info, print_error, print_header, print_warning
from ui.common import get_user_input
import time

class AdminUI:
    def __init__(self, canteen_manager, storage):
        self.canteen_manager = canteen_manager
        self.storage = storage

    def run(self):
        """管理员主菜单"""
        while True:
            clear_screen()
            print_header("管理员控制台")
            print("1. 食堂与窗口配置")
            print("2. 实时监控（动态刷新）")
            print("3. 查看统计报表")
            print("0. 退出管理员模式")
            choice = get_user_input("请选择：", ["1","2","3","0"])
            if choice == "1":
                self.config_menu()
            elif choice == "2":
                self.realtime_monitor()
            elif choice == "3":
                self.show_statistics()
            elif choice == "0":
                break

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
        """添加/修改食堂（模拟）"""
        print_info("此功能需业务层支持，演示阶段暂只显示提示。")
        input("按回车返回...")

    def edit_window(self):
        print_info("此功能需业务层支持，演示阶段暂只显示提示。")
        input("按回车返回...")

    def config_dishes(self):
        print_info("此功能需业务层支持，演示阶段暂只显示提示。")
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
                        rows.append([w['name'], w['type'], w['queue_len'], f"服务中", w['wait_time']])
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