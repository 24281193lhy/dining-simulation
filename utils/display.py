import os
import platform
from colorama import init, Fore, Style

init(autoreset=True)

def clear_screen():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def get_display_width(s):
    """计算字符串的显示宽度（中文占2，英文占1）"""
    width = 0
    for ch in s:
        if '\u4e00' <= ch <= '\u9fff' or '\uff00' <= ch <= '\uffef':  # 中文字符或全角字符
            width += 2
        else:
            width += 1
    return width

def pad_string(s, width):
    """将字符串填充到指定宽度（按显示宽度）"""
    current = get_display_width(s)
    if current >= width:
        return s
    return s + ' ' * (width - current)

def print_table(headers, rows, title=None):
    """
    手动绘制表格，保证中英文混排对齐
    """
    # 计算每列的最大显示宽度
    col_count = len(headers)
    col_widths = [0] * col_count
    # 先计算表头宽度
    for i, h in enumerate(headers):
        col_widths[i] = max(col_widths[i], get_display_width(h))
    # 计算每行数据的宽度
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], get_display_width(str(cell)))
    # 增加左右边距
    col_widths = [w + 2 for w in col_widths]  # 左右各加一个空格
    # 绘制分隔线
    def draw_line(char='-'):
        line = '+'
        for w in col_widths:
            line += char * w + '+'
        return line
    # 绘制表头
    lines = []
    if title:
        lines.append(title.center(sum(col_widths) + col_count + 1))
    lines.append(draw_line('='))
    header_line = '|'
    for i, h in enumerate(headers):
        header_line += pad_string(' ' + h + ' ', col_widths[i]) + '|'
    lines.append(header_line)
    lines.append(draw_line('-'))
    # 绘制数据行
    for row in rows:
        data_line = '|'
        for i, cell in enumerate(row):
            cell_str = str(cell)
            padded = pad_string(' ' + cell_str + ' ', col_widths[i])
            data_line += padded + '|'
        lines.append(data_line)
    lines.append(draw_line('='))
    # 输出
    print('\n'.join(lines))

def print_info(msg):
    print(Fore.GREEN + msg)

def print_error(msg):
    print(Fore.RED + msg)

def print_warning(msg):
    print(Fore.YELLOW + msg)

def print_header(msg):
    print(Fore.BLUE + Style.BRIGHT + "\n" + "=" * 50)
    print(Fore.BLUE + Style.BRIGHT + msg.center(50))
    print(Fore.BLUE + Style.BRIGHT + "=" * 50 + "\n")