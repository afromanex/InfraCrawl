from datetime import datetime
from typing import Optional

class Page:
    def __init__(self, page_id: int, page_url: str, page_content: Optional[str] = None, plain_text: Optional[str] = None, filtered_plain_text: Optional[str] = None, http_status: Optional[int] = None, fetched_at: Optional[datetime] = None, config_id: Optional[int] = None, content_hash: Optional[str] = None):
        self.page_id = page_id
        self.page_url = page_url
        self.page_content = page_content
        self.plain_text = plain_text
        self.filtered_plain_text = filtered_plain_text
        self.http_status = http_status
        self.fetched_at = fetched_at
        self.config_id = config_id
        self.content_hash = content_hash

    def __repr__(self):
        return f"<Page id={self.page_id} url={self.page_url}>"
