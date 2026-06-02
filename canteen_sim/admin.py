import json
import os


class AdminManager:
    def __init__(self, config_dir="config"):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "admin.json")
        self.env_username = os.environ.get("ADMIN_USERNAME", "admin")
        self.env_password = os.environ.get("ADMIN_PASSWORD", "admin123")
        self._ensure_config()

    def _ensure_config(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            if not os.path.exists(self.config_file):
                default = {"username": self.env_username, "password": self.env_password}
                with open(self.config_file, "w") as f:
                    json.dump(default, f, indent=2)
        except (OSError, IOError):
            pass

    def authenticate(self, username, password):
        if username == self.env_username and password == self.env_password:
            return True
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
            return data.get("username") == username and data.get("password") == password
        except (FileNotFoundError, json.JSONDecodeError):
            return False

    def change_password(self, username, old_password, new_password):
        if username == self.env_username and old_password == self.env_password:
            try:
                with open(self.config_file, "w") as f:
                    json.dump({"username": username, "password": new_password}, f, indent=2)
                return True
            except (OSError, IOError):
                return False
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
            if data.get("username") == username and data.get("password") == old_password:
                data["password"] = new_password
                with open(self.config_file, "w") as f:
                    json.dump(data, f, indent=2)
                return True
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return False
