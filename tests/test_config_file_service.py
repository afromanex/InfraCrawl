import os
import pytest
from infracrawl.services.config_file_service import ConfigFileService

CONFIGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")
STARKPARKS_FILE = "starkparks.yml"

def test_list_config_files():
    svc = ConfigFileService(configs_dir=CONFIGS_DIR)
    files = svc.list_config_files()
    assert STARKPARKS_FILE in files

def test_load_config_file():
    svc = ConfigFileService(configs_dir=CONFIGS_DIR)
    data = svc.load_config_file(STARKPARKS_FILE)
    assert data["name"] == "starkparks"
    assert "https://starkparks.com/" in data["root_urls"]
    assert data["max_depth"] == 2
    assert data["robots"] is True
    assert data["refresh_days"] == 7

def test_validate_config():
    svc = ConfigFileService(configs_dir=CONFIGS_DIR)
    data = svc.load_config_file(STARKPARKS_FILE)
    assert svc.validate_config(data)
    # Remove a required field
    del data["name"]
    assert not svc.validate_config(data)
