import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import tempfile
import pytest
from utils.config_loader import ConfigLoader, DEFAULT_CONFIG

class TestConfigLoader:
    def test_load_default_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            loader = ConfigLoader(config_path)
            config = loader.load()
            assert config == DEFAULT_CONFIG
            assert os.path.exists(config_path)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            loader = ConfigLoader(config_path)
            custom_config = {"canteens": [], "users": []}
            loader.save(custom_config)
            loaded = loader.load()
            assert loaded == custom_config