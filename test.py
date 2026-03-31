import sys
import prettytable
import pandas as pd
import colorama
from rich.console import Console

print("Python版本:", sys.version)
print("prettytable版本:", prettytable.__version__)
print("pandas版本:", pd.__version__)
print("colorama版本:", colorama.__version__)

console = Console()
console.print("[bold green]Rich库测试成功！环境配置正确。[/bold green]")