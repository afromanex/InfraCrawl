import os
from typing import Optional

import yaml


class ConfigFileStore:
    """Filesystem/YAML IO for crawler config files.

    Responsibility: locate, read, and parse YAML files on disk.
    It does NOT know about the database.
    """

    def __init__(self, *, configs_dir: str):
        self.configs_dir = configs_dir

    def list_config_files(self) -> list[str]:
        return [
            fname
            for fname in os.listdir(self.configs_dir)
            if fname.endswith(".yml") or fname.endswith(".yaml")
        ]

    def _resolve_path(self, config_path: str) -> str:
        return config_path if os.path.isabs(config_path) else os.path.join(self.configs_dir, config_path)

    def load_yaml_dict(self, config_path: str) -> Optional[dict]:
        """Return parsed YAML dict for `config_path`, or None if missing/invalid."""
        full_path = self._resolve_path(config_path)
        if not os.path.isfile(full_path):
            return None
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def read_raw_yaml(self, config_path: str) -> Optional[str]:
        """Return raw YAML contents for `config_path`, or None if missing/unreadable."""
        full_path = self._resolve_path(config_path)
        if not os.path.isfile(full_path):
            return None
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
