from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infracrawl.db.models import Base
from infracrawl.repository.crawls import CrawlsRepository


def test_mark_incomplete_runs_sets_end_timestamp_and_exception():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)

    repo = CrawlsRepository(session_factory)
    run_id = repo.create_run(config_id=123)

    # run is incomplete initially
    before = repo.get_run(run_id)
    assert before is not None
    assert before.end_timestamp is None

    marked = repo.mark_incomplete_runs(123, message="recovered")
    assert marked == 1

    after = repo.get_run(run_id)
    assert after is not None
    assert after.end_timestamp is not None
    assert after.exception == "recovered"
