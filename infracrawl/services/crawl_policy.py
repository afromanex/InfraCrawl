from datetime import datetime
from typing import Optional
from infracrawl.domain.crawl_context import CrawlContext
from infracrawl.repository.pages import PagesRepository
from infracrawl.utils.datetime_utils import parse_to_utc_naive
import logging

logger = logging.getLogger(__name__)


class CrawlPolicy:
    """Encapsulates crawl decision rules: depth limits, refresh policies, and robots.txt compliance.
    
    Separates policy decisions from crawl orchestration logic.
    """
    
    def __init__(self, pages_repo: PagesRepository, robots_service=None):
        self.pages_repo = pages_repo
        self.robots_service = robots_service
    
    def should_skip_due_to_depth(self, depth: int) -> bool:
        """Check if URL should be skipped due to max depth reached."""
        if depth < 0:
            logger.debug("Skipping (max depth reached) at depth %s", depth)
            return True
        return False
    
    def should_skip_due_to_robots(self, url: str, context: CrawlContext) -> bool:
        """Check if URL should be skipped due to robots.txt restrictions."""
        if self.robots_service is None:
            return False
        
        cfg_robots = True
        if context and context.config is not None:
            cfg_robots = context.config.robots
        
        if not self.robots_service.allowed_by_robots(url, cfg_robots):
            logger.info("Skipping (robots) %s", url)
            return True
        return False
    
    def should_skip_due_to_refresh(self, url: str, context: CrawlContext) -> bool:
        """Check if URL should be skipped due to recent fetch (within refresh_days)."""
        cfg_refresh_days = None
        if context and context.config is not None:
            cfg_refresh_days = context.config.refresh_days
        
        if cfg_refresh_days is None:
            return False
        
        page = self.pages_repo.get_page_by_url(url)
        if not page or not page.fetched_at:
            return False
        
        last_dt_utc = parse_to_utc_naive(page.fetched_at)
        if last_dt_utc is None:
            return False
        
        delta_days = (datetime.utcnow() - last_dt_utc).days
        if delta_days < int(cfg_refresh_days):
            logger.info("Skipping %s; fetched %s days ago (< %s)", url, delta_days, cfg_refresh_days)
            return True
        
        return False
