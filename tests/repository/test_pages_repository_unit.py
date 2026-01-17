from datetime import datetime
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SASession, sessionmaker

import pytest

from infracrawl.db.models import Base, Page as DBPage
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain import Page as DomainPage


def test_ensure_page_handles_integrity_race(tmp_path):
    # Use a file-backed SQLite DB to allow concurrent connections across threads
    dbfile = tmp_path / "race.db"
    engine = create_engine(f"sqlite:///{dbfile}", future=True, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    repo = PagesRepository(session_factory)

    url = "http://example.com/race"
    results = []

    def worker():
        pid = repo.ensure_page(url)
        results.append(pid)

    import threading

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 2
    assert results[0] == results[1]

    with repo.get_session() as s:
        rows = s.execute(select(DBPage).where(DBPage.page_url == url)).scalars().all()
        assert len(rows) == 1


def test_upsert_preserves_datetime():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    repo = PagesRepository(session_factory)

    now = datetime.utcnow()
    domain = DomainPage(
        page_id=None,
        page_url="http://example.com/time",
        page_content="content",
        plain_text=None,
        filtered_plain_text=None,
        http_status=None,
        fetched_at=now,
        config_id=None,
    )

    out = repo.upsert_page(domain)
    assert isinstance(out.fetched_at, datetime)

    with repo.get_session() as s:
        dbp = s.execute(select(DBPage).where(DBPage.page_url == "http://example.com/time")).scalars().first()
        assert dbp is not None
        assert isinstance(dbp.fetched_at, datetime)
        assert abs((dbp.fetched_at - now).total_seconds()) < 5


def test_upsert_strips_nul_characters():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    repo = PagesRepository(session_factory)

    # Prepare domain page with NULs in text fields
    domain = DomainPage(
        page_id=None,
        page_url="http://example.com/nul",
        page_content="abc\x00def",
        plain_text="x\x00y",
        filtered_plain_text="z\x00",
        http_status=200,
        fetched_at=datetime.utcnow(),
        config_id=None,
    )

    out = repo.upsert_page(domain)
    assert "\x00" not in (out.page_content or "")
    assert "\x00" not in (out.plain_text or "")
    assert "\x00" not in (out.filtered_plain_text or "")

    with repo.get_session() as s:
        dbp = s.execute(select(DBPage).where(DBPage.page_url == "http://example.com/nul")).scalars().first()
        assert dbp is not None
        assert "\x00" not in (dbp.page_content or "")
        assert "\x00" not in (dbp.plain_text or "")
        assert "\x00" not in (dbp.filtered_plain_text or "")
