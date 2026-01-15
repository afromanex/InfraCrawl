import importlib
import sys
import builtins
import types
import logging
import os
from pathlib import Path

import pytest


def _reload_config():
    sys.modules.pop("infracrawl.config", None)
    return importlib.import_module("infracrawl.config")


def test_missing_dotenv_logs_warning(monkeypatch, caplog):
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "dotenv" or name.startswith("dotenv."):
            raise ImportError
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    caplog.set_level(logging.WARNING)
    cfg = _reload_config()
    assert "python-dotenv not available" in caplog.text

    # environment fallback works
    monkeypatch.setenv("USER_AGENT", "X-Agent")
    sys.modules.pop("infracrawl.config", None)
    cfg = _reload_config()
    assert cfg.get_str_env("USER_AGENT", "InfraCrawl/0.1") == "X-Agent"


def test_dotenv_present_but_fails_to_load(monkeypatch, tmp_path):
    tmp_path.joinpath(".env").write_text("USER_AGENT=FromFile")
    monkeypatch.chdir(tmp_path)

    fake = types.SimpleNamespace(load_dotenv=lambda: False)
    monkeypatch.setitem(sys.modules, "dotenv", fake)
    sys.modules.pop("infracrawl.config", None)
    with pytest.raises(RuntimeError):
        _reload_config()


def test_dotenv_loads_sets_variables(monkeypatch, tmp_path):
    tmp_path.joinpath(".env").write_text("USER_AGENT=DotenvAgent")
    monkeypatch.chdir(tmp_path)

    def fake_load():
        # emulate dotenv behavior: read .env and set os.environ
        p = Path(".env")
        for line in p.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ[k] = v
        return True

    fake = types.SimpleNamespace(load_dotenv=fake_load)
    monkeypatch.setitem(sys.modules, "dotenv", fake)
    sys.modules.pop("infracrawl.config", None)
    cfg = _reload_config()
    assert cfg.get_str_env("USER_AGENT", "InfraCrawl/0.1") == "DotenvAgent"
