"""Time-token resolution tests."""

from datetime import UTC, datetime, timedelta

from app.services.world import resolve_dt

REF = datetime(2026, 8, 18, 16, 0, tzinfo=UTC)


def test_now_token():
    assert resolve_dt("now", REF) == REF


def test_offset_tokens():
    assert resolve_dt("now+18h", REF) == REF + timedelta(hours=18)
    assert resolve_dt("now-30d", REF) == REF - timedelta(days=30)
    assert resolve_dt("now+45m", REF) == REF + timedelta(minutes=45)


def test_next_occurrence_is_deterministic_relative_to_ref():
    a = resolve_dt("next@10:00", REF)
    b = resolve_dt("next@10:00", REF)
    assert a == b
    assert a > REF


def test_next_with_day_offset():
    base = resolve_dt("next@10:00", REF)
    plus3 = resolve_dt("next@10:00+3", REF)
    assert plus3 - base == timedelta(days=3)


def test_iso_passthrough():
    out = resolve_dt("2026-09-01T09:00:00+00:00", REF)
    assert out.year == 2026 and out.month == 9
