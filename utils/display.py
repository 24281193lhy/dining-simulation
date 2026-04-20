# utils/display.py
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
    width = 0
    for ch in s:
        if '\u4e00' <= ch <= '\u9fff' or '\uff00' <= ch <= '\uffef':
            width += 2
        else:
            width += 1
    return width

def pad_string(s, width):
    current = get_display_width(s)
    if current >= width:
        return s
    return s + ' ' * (width - current)

def print_table(headers, rows, title=None):
    col_count = len(headers)
    col_widths = [0] * col_count
    for i, h in enumerate(headers):
        col_widths[i] = max(col_widths[i], get_display_width(h))
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], get_display_width(str(cell)))
    col_widths = [w + 2 for w in col_widths]

    def draw_line(char='-'):
        line = '+'
        for w in col_widths:
            line += char * w + '+'
        return line

    lines = []
    if title:
        lines.append(title.center(sum(col_widths) + col_count + 1))
    lines.append(draw_line('='))
    header_line = '|'
    for i, h in enumerate(headers):
        header_line += pad_string(' ' + h + ' ', col_widths[i]) + '|'
    lines.append(header_line)
    lines.append(draw_line('-'))
    for row in rows:
        data_line = '|'
        for i, cell in enumerate(row):
            cell_str = str(cell)
            padded = pad_string(' ' + cell_str + ' ', col_widths[i])
            data_line += padded + '|'
        lines.append(data_line)
    lines.append(draw_line('='))
    print('\n'.join(lines))

def print_info(msg):
    print(Fore.GREEN + msg)

def print_success(msg):
    print(Fore.GREEN + Style.BRIGHT + msg)

def print_error(msg):
    print(Fore.RED + msg)

def print_warning(msg):
    print(Fore.YELLOW + msg)

def print_header(msg):
    print(Fore.BLUE + Style.BRIGHT + "\n" + "=" * 50)
    print(Fore.BLUE + Style.BRIGHT + msg.center(50))
    print(Fore.BLUE + Style.BRIGHT + "=" * 50 + "\n")