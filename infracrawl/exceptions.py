"""Custom exceptions for InfraCrawl services."""


class ConfigNotFoundError(Exception):
    """Raised when a requested config cannot be found in DB or filesystem."""
    
    def __init__(self, config_path: str, reason: str = "not found"):
        self.config_path = config_path
        self.reason = reason
        super().__init__(f"Config '{config_path}' {reason}")
