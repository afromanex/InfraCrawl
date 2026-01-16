from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class CrawlerConfigMetadata:
    """Persistence-oriented fields for a crawler configuration."""

    config_id: Optional[int]
    config_path: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class CrawlerConfigData:
    """Crawl-behavior fields for a crawler configuration."""

    root_urls: list[str]
    max_depth: Optional[int]
    robots: bool
    refresh_days: Optional[int]
    fetch_mode: str
    schedule: Optional[Any] = None
    fetch_options: Optional[dict] = None
    http_options: Optional[dict] = None
    headless_options: Optional[dict] = None


class CrawlerConfig:
    """Configuration record composed of metadata + crawl settings.

    This keeps the existing public constructor stable for callers, while
    allowing new code to depend only on `data` (crawl settings) when possible.
    """

    def __init__(
        self,
        config_id: Optional[int],
        config_path: str,
        root_urls=None,
        max_depth=None,
        robots=True,
        refresh_days=None,
        fetch_mode: str = None,
        schedule: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        fetch_options: Optional[dict] = None,
        http_options: Optional[dict] = None,
        headless_options: Optional[dict] = None,
    ):
        if fetch_mode is None or (isinstance(fetch_mode, str) and fetch_mode.strip() == ""):
            raise ValueError("fetch_mode is required")

        self.meta = CrawlerConfigMetadata(
            config_id=config_id,
            config_path=config_path,
            created_at=created_at,
            updated_at=updated_at,
        )
        self.data = CrawlerConfigData(
            root_urls=list(root_urls or []),
            max_depth=max_depth,
            robots=bool(robots),
            refresh_days=refresh_days,
            fetch_mode=fetch_mode,
            schedule=schedule,
            fetch_options=fetch_options,
            http_options=http_options,
            headless_options=headless_options,
        )

    @property
    def config_id(self) -> Optional[int]:
        return self.meta.config_id

    @property
    def config_path(self) -> str:
        return self.meta.config_path

    @property
    def created_at(self) -> Optional[datetime]:
        return self.meta.created_at

    @property
    def updated_at(self) -> Optional[datetime]:
        return self.meta.updated_at

    @property
    def root_urls(self) -> list[str]:
        return self.data.root_urls

    @property
    def max_depth(self) -> Optional[int]:
        return self.data.max_depth

    @property
    def robots(self) -> bool:
        return self.data.robots

    @property
    def refresh_days(self) -> Optional[int]:
        return self.data.refresh_days

    @property
    def fetch_mode(self) -> str:
        return self.data.fetch_mode

    @property
    def schedule(self) -> Optional[Any]:
        return self.data.schedule

    @property
    def fetch_options(self) -> Optional[dict]:
        return self.data.fetch_options

    @property
    def http_options(self) -> Optional[dict]:
        return self.data.http_options

    @property
    def headless_options(self) -> Optional[dict]:
        return self.data.headless_options

    def __repr__(self):
        return f"<CrawlerConfig id={self.config_id} path={self.config_path} schedule={self.schedule}>"
