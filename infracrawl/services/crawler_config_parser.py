import os
from typing import Optional

from infracrawl.domain.config import CrawlerConfig


class CrawlerConfigParser:
    """Parse a YAML dict into a CrawlerConfig.

    Responsibility: schema/validation for YAML config files.
    It does NOT perform filesystem IO and does NOT talk to the database.
    """

    def parse(
        self,
        *,
        config_path: str,
        data: dict,
        config_id: Optional[int] = None,
        created_at=None,
        updated_at=None,
    ) -> Optional[CrawlerConfig]:
        fetch_mode = data.get("fetch_mode")
        if fetch_mode is None:
            return None

        return CrawlerConfig(
            config_id=config_id,
            config_path=os.path.basename(config_path),
            root_urls=data.get("root_urls", []),
            max_depth=data.get("max_depth"),
            robots=data.get("robots", True),
            refresh_days=data.get("refresh_days"),
            fetch_mode=fetch_mode,
            schedule=data.get("schedule"),
            created_at=created_at,
            updated_at=updated_at,
        )
