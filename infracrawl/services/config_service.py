import os
import logging
import yaml
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain.config import CrawlerConfig
from typing import Optional

logger = logging.getLogger(__name__)

class ConfigService:
    # CLAUDE: Suggested split: 1) _load_config_from_file() 2) _sync_config_to_db() 3) _remove_orphaned_configs() 4) sync_configs_with_disk() orchestrates
    def sync_configs_with_disk(self):
        """
        Scan the configs directory for YAML files, upsert configs into the DB by name and config_path,
        and remove DB configs not present on disk.
        """
        loaded_paths = set()
        # TODO: os.listdir() will raise if configs_dir doesn't exist - no error handling
        # RESPONSE: This is intended. 
        for fname in os.listdir(self.configs_dir):
            if not (fname.endswith(".yml") or fname.endswith(".yaml")):
                continue
            full_path = os.path.join(self.configs_dir, fname)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    # TODO: yaml.safe_load() can raise YAMLError - should be caught specifically
                    data = yaml.safe_load(f)
                # Identify configs by filename (config_path). If YAML is malformed, skip.
                if not isinstance(data, dict):
                    continue
                config_obj = self._create_config_from_yaml(fname, data, config_id=None)
                cid = self.configs_repo.upsert_config(config_obj)
                loaded_paths.add(fname)
                logger.info("Loaded config %s -> id=%s", fname, cid)
            except Exception as e:
                # CLAUDE: Catch specific errors: IOError (file read), yaml.YAMLError (parse), but generic fallback OK for unexpected issues
                logger.warning("Could not load config %s: %s", fname, e)

        # Remove any configs in DB that are not present on disk
        existing_configs = self.configs_repo.list_configs()
        existing_paths = set(c.config_path for c in existing_configs)
        to_remove = existing_paths - loaded_paths
        for path in to_remove:
            self.configs_repo.delete_config(path)
            logger.info("Removed DB config not present on disk: %s", path)

    def __init__(self, configs_repo: Optional[ConfigsRepository] = None, configs_dir: Optional[str] = None):
        self.configs_repo = configs_repo or ConfigsRepository()
        self.configs_dir = configs_dir or os.path.join(os.getcwd(), "configs")

    def list_configs(self):
        """Return all configs in the DB (name + config_path only)."""
        return self.configs_repo.list_configs()

    def _create_config_from_yaml(self, config_path: str, data: dict, config_id: Optional[int] = None, created_at=None, updated_at=None) -> CrawlerConfig:
        """Create CrawlerConfig from parsed YAML data."""
        return CrawlerConfig(
            config_id=config_id,
            config_path=config_path,
            root_urls=data.get("root_urls", []),
            max_depth=data.get("max_depth"),
            robots=data.get("robots", True),
            refresh_days=data.get("refresh_days"),
            schedule=data.get("schedule"),
            created_at=created_at,
            updated_at=updated_at
        )

    # TODO: No validation of root_urls format, max_depth >= 0, etc.
    # CLAUDE: Add validation in CrawlerConfig.__post_init__ or separate validator. Defer until invalid configs cause issues.
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
        return self._create_config_from_yaml(
            config_path=db_cfg.config_path,
            data=data,
            config_id=db_cfg.config_id,
            created_at=db_cfg.created_at,
            updated_at=db_cfg.updated_at
        )
            config_path=db_cfg.config_path,
            root_urls=data.get("root_urls", []),
            max_depth=data.get("max_depth"),
            robots=data.get("robots", True),
            refresh_days=data.get("refresh_days"),
            schedule=data.get("schedule"),
            created_at=db_cfg.created_at,
            updated_at=db_cfg.updated_at,
        )

    def get_config_yaml(self, name: str) -> Optional[str]:
        """Return the raw YAML content of a config file."""
        db_cfg = self.configs_repo.get_config(name)
        if not db_cfg:
            return None
        path = db_cfg.config_path
        full_path = path if os.path.isabs(path) else os.path.join(self.configs_dir, path)
        if not os.path.isfile(full_path):
            return None
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
