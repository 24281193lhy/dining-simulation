# 北交大食堂仿真系统

## 👥 团队成员与分工

| 姓名  | GitHub 账号 | 负责模块                     | 主要工作内容 |
|-----|------------|--------------------------|--------------|
| 游政航 | youyouyou333555-hash | `business/`、`monitor/` 、`templates/` | 核心业务逻辑：食堂管理者、排队引擎、座位分配、事件调度器、数据存储与统计 |
| 李汇洋 | 2428193lhy | `ui/`、`templates/`       | 人机交互界面：学生端 UI、管理员 UI、通用显示组件、Web 仪表盘前端 |
| 曹楠  | yassay1 | `data/`、`config/`、自动化脚本  | 监控与基础设施：Web 监控后端、自动化协调器、配置加载、测试框架 |

> 注：测试模块 `tests/` 由各成员按自己负责的模块编写对应测试，全体参与。

## 📁 项目结构与分工对应

dining-simulation/
├── business/ # [游政航] 食堂业务、排队引擎、座位管理

├── config/ # [曹榆] 自动化协调器、配置管理

├── data/ # [曹榆] 数据存储、统计功能

├── monitor/ # [游政航] Web 监控仪表盘

├── templates/ # [李汇洋、游政航] 前端 HTML 模板

├── tests/ # [全体] 各模块单元测试

├── ui/ # [李汇洋] 学生端、管理端界面及通用组件

├── utils/ # [全体] 工具函数、日志等

├── main.py # 入口文件

└── requirements.txt # 依赖列表


## Contributors

感谢所有为本项目做出贡献的成员：
<a href="https://github.com/24281193lhy/dining-simulation/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=24281193lhy/dining-simulation" />
</a>