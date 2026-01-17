from datetime import datetime, timezone, timedelta

from infracrawl.utils.datetime_utils import parse_to_utc_naive


def test_none_returns_none():
    assert parse_to_utc_naive(None) is None


def test_naive_datetime_returns_same():
    dt = datetime(2020, 1, 1, 12, 0, 0)
    out = parse_to_utc_naive(dt)
    assert out == dt


def test_aware_datetime_converted_to_utc_naive():
    dt = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    out = parse_to_utc_naive(dt)
    # 12:00+02:00 -> 10:00 UTC
    assert out == datetime(2020, 1, 1, 10, 0, 0)


def test_iso_string_without_tz_parsed_as_naive():
    s = "2020-01-01T12:00:00"
    out = parse_to_utc_naive(s)
    assert out == datetime(2020, 1, 1, 12, 0, 0)


def test_iso_string_with_tz_converted_to_utc_naive():
    s = "2020-01-01T12:00:00+02:00"
    out = parse_to_utc_naive(s)
    assert out == datetime(2020, 1, 1, 10, 0, 0)


def test_invalid_string_returns_none():
    assert parse_to_utc_naive("not-a-date") is None
