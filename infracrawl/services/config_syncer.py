import logging

logger = logging.getLogger(__name__)


class ConfigSyncer:
    """Synchronize YAML configs on disk with configs stored in the DB."""

    def __init__(self, *, file_store, configs_repo, parser):
        self.file_store = file_store
        self.configs_repo = configs_repo
        self.parser = parser

    def sync(self) -> None:
        loaded_paths: set[str] = set()

        for fname in self.file_store.list_config_files():
            data = None
            try:
                data = self.file_store.load_yaml_dict(fname)
            except Exception as e:
                logger.warning("Could not load config %s: %s", fname, e)
                continue

            if not isinstance(data, dict):
                logger.warning("Config file %s does not contain a dictionary", fname)
                continue

            config_obj = None
            try:
                config_obj = self.parser.parse(config_path=fname, data=data)
            except Exception as e:
                logger.warning("Could not parse config %s: %s", fname, e)
                continue

            if not config_obj:
                # Parser returns None for invalid/unsupported config.
                logger.warning("Config file %s is invalid or missing required fields", fname)
                continue

            result = self.configs_repo.upsert_config(config_obj)
            loaded_paths.add(fname)
            logger.info("Loaded config %s -> id=%s", fname, result.config_id)

        existing_configs = self.configs_repo.list_configs()
        existing_paths = set(c.config_path for c in existing_configs)
        to_remove = existing_paths - loaded_paths
        for path in to_remove:
            self.configs_repo.delete_config(path)
            logger.info("Removed DB config not present on disk: %s", path)
