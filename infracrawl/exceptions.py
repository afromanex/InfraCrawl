"""Custom exceptions for InfraCrawl services."""


class ConfigNotFoundError(Exception):
    """Raised when a requested config cannot be found in DB or filesystem."""
    
    def __init__(self, config_path: str, reason: str = "not found"):
        self.config_path = config_path
        self.reason = reason
        super().__init__(f"Config '{config_path}' {reason}")


class HttpFetchError(Exception):
    """Raised when an HTTP fetch fails due to network/transport errors."""

    def __init__(self, url: str, original: Exception):
        self.url = url
        self.original = original
        super().__init__(f"HTTP fetch failed for {url}: {original}")
