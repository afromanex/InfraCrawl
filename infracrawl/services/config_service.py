import os
import yaml
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain.config import CrawlerConfig
from typing import Optional

class ConfigService:
    def __init__(self, configs_repo: Optional[ConfigsRepository] = None, configs_dir: Optional[str] = None):
        self.configs_repo = configs_repo or ConfigsRepository()
        self.configs_dir = configs_dir or os.path.join(os.getcwd(), "configs")

    def list_configs(self):
        """Return all configs in the DB (name + config_path only)."""
        return self.configs_repo.list_configs()

    def get_config(self, name: str) -> Optional[CrawlerConfig]:
        """Load full config from YAML using config_path from DB."""
        db_cfg = self.configs_repo.get_config(name)
        if not db_cfg:
            return None
        path = db_cfg.config_path
        full_path = path if os.path.isabs(path) else os.path.join(self.configs_dir, path)
        if not os.path.isfile(full_path):
            return None
        with open(full_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Populate all config fields from YAML
        return CrawlerConfig(
            config_id=db_cfg.config_id,
            name=db_cfg.name,
            config_path=db_cfg.config_path,
            root_urls=data.get("root_urls", []),
            max_depth=data.get("max_depth"),
            robots=data.get("robots", True),
            refresh_days=data.get("refresh_days"),
            created_at=db_cfg.created_at,
            updated_at=db_cfg.updated_at
        )
