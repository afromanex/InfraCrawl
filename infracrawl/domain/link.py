from typing import Optional

class Link:
    def __init__(self, link_id: int, link_from_id: int, link_to_id: int, anchor_text: Optional[str] = None):
        self.link_id = link_id
        self.link_from_id = link_from_id
        self.link_to_id = link_to_id
        self.anchor_text = anchor_text

    def __repr__(self):
        return f"<Link id={self.link_id} from={self.link_from_id} to={self.link_to_id}>"
