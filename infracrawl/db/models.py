from __future__ import annotations


from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Page(Base):
    __tablename__ = "pages"

    page_id = Column(Integer, primary_key=True)
    page_url = Column(Text, unique=True, nullable=False)
    page_content = Column(Text, nullable=True)
    plain_text = Column(Text, nullable=True)
    http_status = Column(Integer, nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=True)
    config_id = Column(Integer, nullable=True)


class Link(Base):
    __tablename__ = "links"

    link_id = Column(Integer, primary_key=True)
    link_from_id = Column(Integer, ForeignKey("pages.page_id"), nullable=False)
    link_to_id = Column(Integer, ForeignKey("pages.page_id"), nullable=False)
    anchor_text = Column(Text, nullable=True)

    from_page = relationship("Page", foreign_keys=[link_from_id])
    to_page = relationship("Page", foreign_keys=[link_to_id])


class CrawlerConfig(Base):
    __tablename__ = "crawler_configs"

    config_id = Column(Integer, primary_key=True)
    config_path = Column(Text, unique=True, nullable=False)  # Path or filename of the YAML config
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
