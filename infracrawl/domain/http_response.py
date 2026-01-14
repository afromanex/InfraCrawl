from typing import NamedTuple


class HttpResponse(NamedTuple):
    """Response from HTTP fetch operation."""
    status_code: int
    text: str
