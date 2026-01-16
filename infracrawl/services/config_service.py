import logging
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain.config import CrawlerConfig
from infracrawl.exceptions import ConfigNotFoundError
from typing import Optional

from infracrawl.services.config_file_store import ConfigFileStore
from infracrawl.services.crawler_config_parser import CrawlerConfigParser
from infracrawl.services.config_syncer import ConfigSyncer

logger = logging.getLogger(__name__)


class ConfigService:
    """Manages crawler configurations, synchronizing YAML files with database."""
    
    def __init__(
        self,
        configs_repo: ConfigsRepository,
        configs_dir: Optional[str] = None,
        file_store: Optional[ConfigFileStore] = None,
        parser: Optional[CrawlerConfigParser] = None,
        syncer: Optional[ConfigSyncer] = None,
    ):
        self.configs_repo = configs_repo
        configs_dir_final = configs_dir
        if configs_dir_final is None:
            import os

            configs_dir_final = os.path.join(os.getcwd(), "configs")
        self.configs_dir = configs_dir_final

        self.file_store = file_store or ConfigFileStore(configs_dir=self.configs_dir)
        self.parser = parser or CrawlerConfigParser()
        self.syncer = syncer or ConfigSyncer(file_store=self.file_store, configs_repo=self.configs_repo, parser=self.parser)
    
    def sync_configs_with_disk(self):
        """Scan configs directory, upsert to DB, remove orphaned DB configs."""
        self.syncer.sync()

    def list_configs(self):
        """Return all configs in the DB (name + config_path only)."""
        return self.configs_repo.list_configs()

    def get_config(self, config_path: str) -> CrawlerConfig:
        """Load full config from YAML using config_path from DB.
        
        Raises:
            ConfigNotFoundError: If config not in DB or YAML file missing/invalid
        """
        db_cfg = self.configs_repo.get_config(config_path)
        if not db_cfg:
            raise ConfigNotFoundError(config_path, "not found in database")

        data = self.file_store.load_yaml_dict(db_cfg.config_path)
        if not isinstance(data, dict):
            raise ConfigNotFoundError(config_path, "YAML file missing or invalid")

        full_config = self.parser.parse(
            config_path=db_cfg.config_path,
            data=data,
            config_id=db_cfg.config_id,
            created_at=db_cfg.created_at,
            updated_at=db_cfg.updated_at,
        )
        if not full_config:
            raise ConfigNotFoundError(config_path, "YAML file missing or invalid")

        return full_config

    def get_config_yaml(self, config_path: str) -> Optional[str]:
        """Return the raw YAML content of a config file."""
        db_cfg = self.configs_repo.get_config(config_path)
        if not db_cfg:
            return None
        try:
            return self.file_store.read_raw_yaml(db_cfg.config_path)
        except Exception as e:
            logger.warning("Could not read config file %s: %s", db_cfg.config_path, e)
            return None
