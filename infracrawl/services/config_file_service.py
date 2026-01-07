import os
import yaml
from typing import Optional, Dict, Any, List

class ConfigFileService:
    def __init__(self, configs_dir: Optional[str] = None):
        self.configs_dir = configs_dir or os.path.join(os.getcwd(), "configs")

    def list_config_files(self) -> List[str]:
        """Return a list of config filenames in the configs directory."""
        if not os.path.isdir(self.configs_dir):
            return []
        return [f for f in os.listdir(self.configs_dir) if f.endswith(('.yml', '.yaml'))]

    def load_config_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load and parse a YAML config file by filename (relative to configs_dir)."""
        full_path = filename if os.path.isabs(filename) else os.path.join(self.configs_dir, filename)
        if not os.path.isfile(full_path):
            return None
        with open(full_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except Exception:
                return None
        return data

    def validate_config(self, data: Dict[str, Any]) -> bool:
        """Basic validation: check for required fields."""
        required = ["name", "root_urls", "max_depth"]
        return all(field in data for field in required)
