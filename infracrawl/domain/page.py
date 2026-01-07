from datetime import datetime
from typing import Optional

class Page:
    def __init__(self, page_id: int, page_url: str, page_content: Optional[str] = None, plain_text: Optional[str] = None, http_status: Optional[int] = None, fetched_at: Optional[datetime] = None, config_id: Optional[int] = None):
        self.page_id = page_id
        self.page_url = page_url
        self.page_content = page_content
        self.plain_text = plain_text
        self.http_status = http_status
        self.fetched_at = fetched_at
        self.config_id = config_id

    def __repr__(self):
        return f"<Page id={self.page_id} url={self.page_url}>"
