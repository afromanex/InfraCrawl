"""Protocol (interface) definitions for services."""

from typing import Protocol


class ConfigProvider(Protocol):
    """Minimal interface for config access - ensures Interface Segregation Principle.
    
    Only defines methods needed by consumers to avoid tight coupling.
    """
    def list_configs(self):
        """Return list of crawler configs."""
        ...

    def get_config(self, config_path: str):
        """Return a specific crawler config by path."""
        ...

    def sync_configs_with_disk(self) -> None:
        """Reload configs from disk."""
        ...
