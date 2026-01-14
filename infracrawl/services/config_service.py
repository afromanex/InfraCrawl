import os
import logging
import yaml
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain.config import CrawlerConfig
from typing import Optional

logger = logging.getLogger(__name__)


class ConfigService:
    """Manages crawler configurations, synchronizing YAML files with database."""
    
    def __init__(self, configs_repo: Optional[ConfigsRepository] = None, configs_dir: Optional[str] = None):
        self.configs_repo = configs_repo or ConfigsRepository()
        self.configs_dir = configs_dir or os.path.join(os.getcwd(), "configs")
    
    def _list_config_files(self) -> list[str]:
        """Return list of YAML filenames in configs directory."""
        return [fname for fname in os.listdir(self.configs_dir)
                if fname.endswith(".yml") or fname.endswith(".yaml")]
    
    def _load_config_from_file(self, config_path: str, config_id: Optional[int] = None,
                              created_at=None, updated_at=None) -> Optional[CrawlerConfig]:
        """Load a CrawlerConfig from a YAML file.
        
        Args:
            config_path: Filename or absolute path to config file
            config_id: Optional database ID to include in config
            created_at: Optional creation timestamp
            updated_at: Optional update timestamp
            
        Returns:
            CrawlerConfig object or None if file cannot be loaded
        """
        full_path = config_path if os.path.isabs(config_path) else os.path.join(self.configs_dir, config_path)
        if not os.path.isfile(full_path):
            return None
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                logger.warning("Config file %s does not contain a dictionary", config_path)
                return None
            
            return CrawlerConfig(
                config_id=config_id,
                config_path=os.path.basename(config_path),
                root_urls=data.get("root_urls", []),
                max_depth=data.get("max_depth"),
                robots=data.get("robots", True),
                refresh_days=data.get("refresh_days"),
                schedule=data.get("schedule"),
                created_at=created_at,
                updated_at=updated_at
            )
        except Exception as e:
            logger.warning("Could not load config %s: %s", config_path, e)
            return None
    
    def _get_config_yaml_content(self, config_path: str) -> Optional[str]:
        """Return raw YAML content of a config file."""
        full_path = config_path if os.path.isabs(config_path) else os.path.join(self.configs_dir, config_path)
        if not os.path.isfile(full_path):
            return None
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning("Could not read config file %s: %s", config_path, e)
            return None
    
    def sync_configs_with_disk(self):
        """Scan configs directory, upsert to DB, remove orphaned DB configs."""
        loaded_paths = set()
        
        for fname in self._list_config_files():
            config_obj = self._load_config_from_file(fname)
            if config_obj:
                cid = self.configs_repo.upsert_config(config_obj)
                loaded_paths.add(fname)
                logger.info("Loaded config %s -> id=%s", fname, cid)
        
        # Remove configs in DB that are not present on disk
        existing_configs = self.configs_repo.list_configs()
        existing_paths = set(c.config_path for c in existing_configs)
        to_remove = existing_paths - loaded_paths
        for path in to_remove:
            self.configs_repo.delete_config(path)
            logger.info("Removed DB config not present on disk: %s", path)

    def list_configs(self):
        """Return all configs in the DB (name + config_path only)."""
        return self.configs_repo.list_configs()

    def get_config(self, config_path: str) -> Optional[CrawlerConfig]:
        """Load full config from YAML using config_path from DB."""
        db_cfg = self.configs_repo.get_config(config_path)
        if not db_cfg:
            return None
        
        return self._load_config_from_file(
            db_cfg.config_path,
            config_id=db_cfg.config_id,
            created_at=db_cfg.created_at,
            updated_at=db_cfg.updated_at
        )

    def get_config_yaml(self, config_path: str) -> Optional[str]:
        """Return the raw YAML content of a config file."""
        db_cfg = self.configs_repo.get_config(config_path)
        if not db_cfg:
            return None
        return self._get_config_yaml_content(db_cfg.config_path)
