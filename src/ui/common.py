from utils.display import print_error, print_warning, print_header

def get_user_input(prompt, valid_options=None, allow_empty=False):
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
    print_header("北京交通大学就餐仿真系统")
    print("1. 用户登录")
    print("2. 管理员登录")
    print("0. 退出系统")
    return get_user_input("请选择：", ["1", "2", "0"])

def validate_student_id(student_id):
    """验证北交大学号格式：8位数字，前两位22-25，3-4位01-50，5-6位01-20，后两位任意"""
    if not (student_id.isdigit() and len(student_id) == 8):
        return False
    year = int(student_id[:2])
    if year < 22 or year > 25:
        return False
    college = int(student_id[2:4])
    if college < 1 or college > 50:
        return False
    clazz = int(student_id[4:6])
    if clazz < 1 or clazz > 20:
        return False
    # 后两位不限制
    return True

def validate_teacher_id(teacher_id):
    """验证教师工号格式：以T开头（不区分大小写），后面至少一位数字或字母"""
    return teacher_id.upper().startswith('T') and len(teacher_id) >= 2