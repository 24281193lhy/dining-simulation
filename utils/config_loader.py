import json
import os
from typing import Dict, Any

DEFAULT_CONFIG = {
    "canteens": [
        {
            "name": "学生第一食堂",
            "total_seats": 120,
            "windows": [
                {
                    "name": "快餐窗口",
                    "speed": 0.8,
                    "type": "normal",
                    "dishes": ["红烧肉套餐:15.0", "宫保鸡丁:12.0"]
                },
                {
                    "name": "面食窗口",
                    "speed": 1.2,
                    "type": "normal",
                    "dishes": ["牛肉拉面:12.0", "炸酱面:10.0"]
                }
            ]
        },
        {
            "name": "教工食堂",
            "total_seats": 80,
            "windows": [
                {
                    "name": "教工专窗",
                    "speed": 1.0,
                    "type": "teacher",
                    "dishes": ["教师套餐A:18.0", "教师套餐B:20.0"]
                },
                {
                    "name": "普通窗口",
                    "speed": 1.0,
                    "type": "normal",
                    "dishes": ["盖浇饭:13.0"]
                }
            ]
        },
        {
            "name": "风味餐厅",
            "total_seats": 100,
            "windows": [
                {
                    "name": "麻辣烫",
                    "speed": 1.5,
                    "type": "normal",
                    "dishes": ["自选麻辣烫:16.0"]
                },
                {
                    "name": "铁板饭",
                    "speed": 1.3,
                    "type": "normal",
                    "dishes": ["黑椒牛肉铁板:18.0"]
                }
            ]
        }
    ],
    "users": [
        # 批量创建逻辑在代码中实现，这里不列出具体ID
    ],
    "user_generation": {
        "students": 200,
        "teachers": 20
    }
}


class ConfigLoader:
    """加载/保存 JSON 配置文件，若不存在则生成与 main.py 一致的默认配置"""

    def __init__(self, config_path: str = "config/canteen_config.json"):
        self.config_path = config_path
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            print(f"⚠️ 配置文件 {self.config_path} 不存在，将创建默认配置")
            self.save_default()
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"❌ 配置文件读取失败: {e}，将使用默认配置并覆盖原文件")
            self.save_default()
            config = DEFAULT_CONFIG
        return config

    def save_default(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"✅ 默认配置已保存至 {self.config_path}")

    def save(self, config: Dict):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)