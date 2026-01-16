from typing import NamedTuple, Optional


class HttpResponse(NamedTuple):
    """Response from HTTP fetch operation."""
    status_code: int
    text: str
    content_type: Optional[str] = None
