import json
import os
from typing import Dict, Any

DEFAULT_CONFIG = {
    "canteens": [
        {
            "name": "学一食堂",
            "total_seats": 200,
            "windows": [
                {"name": "普通窗口1", "speed": 1.5, "type": "normal",
                 "dishes": ["红烧肉:12", "清炒时蔬:6"]},
                {"name": "普通窗口2", "speed": 1.5, "type": "normal",
                 "dishes": ["宫保鸡丁:15", "米饭:1"]},
                {"name": "教工专窗", "speed": 1.0, "type": "teacher",
                 "dishes": ["教师特餐:18"]}
            ]
        },
        {
            "name": "学二食堂",
            "total_seats": 150,
            "windows": [
                {"name": "普通窗口1", "speed": 1.2, "type": "normal",
                 "dishes": ["牛肉面:20"]},
                {"name": "普通窗口2", "speed": 1.2, "type": "normal",
                 "dishes": ["饺子:15"]}
            ]
        },
        {
            "name": "教工餐厅",
            "total_seats": 80,
            "windows": [
                {"name": "教工专窗", "speed": 0.8, "type": "teacher",
                 "dishes": ["教工套餐:25"]}
            ]
        }
    ],
    "users": [
        {"id": "S2024001", "role": "student"},
        {"id": "T001", "role": "teacher"}
    ]
}

class ConfigLoader:
    """加载/保存 JSON 配置文件，若不存在则生成默认配置"""

    def __init__(self, config_path: str = "config/canteen_config.json"):
        self.config_path = config_path
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            print(f"⚠️ 配置文件 {self.config_path} 不存在，将创建默认配置")
            self.save_default()
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_default(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"✅ 默认配置已保存至 {self.config_path}")

    def save(self, config: Dict):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)