from utils.display import print_error, print_warning, print_header

def get_user_input(prompt, valid_options=None, allow_empty=False):
    """
    获取用户输入，并进行有效性验证
    :param prompt: 提示信息
    :param valid_options: 可选的有效选项列表（字符串）
    :param allow_empty: 是否允许空输入
    :return: 用户输入的字符串（已strip）
    """
    while True:
        value = input(prompt).strip()
        if not value and not allow_empty:
            print_warning("输入不能为空，请重新输入。")
            continue
        if valid_options is not None and value not in valid_options:
            print_error(f"无效输入，请从 {valid_options} 中选择。")
            continue
        return value

def show_main_menu():
    """显示主菜单，返回用户选择"""
    print_header("北京交通大学就餐仿真系统")
    print("1. 学生登录")
    print("2. 管理员登录")
    print("0. 退出系统")
    return get_user_input("请选择：", ["1", "2", "0"])