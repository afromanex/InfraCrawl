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
        # Only support nested format: fetch: { mode: "http", headless_chromium: { ... } }
        # Mode-specific options go under a key matching the mode name
        if "fetch" not in data:
            return None

        fetch_dict = data.get("fetch", {})
        fetch_mode = fetch_dict.get("mode")
        fetch_options = fetch_dict

        if fetch_mode is None:
            return None

        # Extract mode-specific options from fetch_dict
        http_options = None
        headless_options = None
        if fetch_mode in fetch_dict:
            mode_options = fetch_dict.get(fetch_mode, {})
            if fetch_mode == "http":
                http_options = mode_options
            elif fetch_mode.startswith("headless"):
                headless_options = mode_options

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
            fetch_options=fetch_options,
            http_options=http_options,
            headless_options=headless_options,
            delay_seconds=data.get("delay_seconds", 1.0),
            # Default to True so jobs resume unless explicitly disabled
            resume_on_application_restart=data.get("resume_on_application_restart", True),
        )
