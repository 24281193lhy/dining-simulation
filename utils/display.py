import os
import platform
from prettytable import PrettyTable
from colorama import init, Fore, Style

# 初始化colorama，自动适配Windows
init(autoreset=True)

def clear_screen():
    """清空控制台"""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def print_table(headers, rows, title=None):
    """使用PrettyTable打印表格"""
    table = PrettyTable()
    table.field_names = headers
    for row in rows:
        table.add_row(row)
    if title:
        print(Fore.CYAN + Style.BRIGHT + title)
    print(table)

def print_info(msg):
    """打印信息（绿色）"""
    print(Fore.GREEN + msg)

def print_error(msg):
    """打印错误（红色）"""
    print(Fore.RED + msg)

def print_warning(msg):
    """打印警告（黄色）"""
    print(Fore.YELLOW + msg)

def print_header(msg):
    """打印标题（蓝色加粗）"""
    print(Fore.BLUE + Style.BRIGHT + "\n" + "=" * 50)
    print(Fore.BLUE + Style.BRIGHT + msg.center(50))
    print(Fore.BLUE + Style.BRIGHT + "=" * 50 + "\n")