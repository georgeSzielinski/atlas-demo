"""Tests for the timezone-aware exchange trading calendar.

Covers weekends, regular sessions and boundaries, US market holidays, early
closes, daylight saving, timezone-aware input conversion, naive-as-New-York
interpretation, and the explicit unavailable state outside coverage.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from market.market_calendar import MarketCalendar


ET = ZoneInfo("America/New_York")
calendar = MarketCalendar()


def session(as_of):
    return calendar.session(as_of)


# ----------------------------------------------------------------------
# Weekends and regular sessions
# ----------------------------------------------------------------------
# 2026-06-28 is a Sunday.
weekend = session("2026-06-28T10:00:00")
assert weekend["is_open"] is False
assert weekend["is_session"] is False
assert weekend["is_holiday"] is False  # weekend is not a holiday
assert weekend["available"] is True

# 2026-06-29 is a normal Monday.
regular = session("2026-06-29T10:00:00")
assert regular["is_open"] is True
assert regular["session"] == "open"
assert regular["is_session"] is True
assert regular["is_early_close"] is False
assert regular["regular_close"] == "16:00"
assert regular["market_calendar_placeholder"] is False

# Session boundaries: 09:30 open (inclusive), 16:00 closed (exclusive).
assert session("2026-06-29T09:29:00")["is_open"] is False
assert session("2026-06-29T09:30:00")["is_open"] is True
assert session("2026-06-29T15:59:00")["is_open"] is True
assert session("2026-06-29T16:00:00")["is_open"] is False
assert session("2026-06-29T18:00:00")["is_open"] is False


# ----------------------------------------------------------------------
# US market holidays (all closed, flagged as holidays on weekdays)
# ----------------------------------------------------------------------
holidays_2026 = [
    "2026-01-01",  # New Year's Day (Thu)
    "2026-01-19",  # MLK Day
    "2026-02-16",  # Presidents' Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day observed (Jul 4 is Sat)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
]
for day in holidays_2026:
    status = session(f"{day}T10:00:00")
    assert status["is_open"] is False, f"{day} should be closed"
    assert status["is_session"] is False, f"{day} should not be a session"
    assert status["is_holiday"] is True, f"{day} should be a holiday"


# ----------------------------------------------------------------------
# Early closes (close at 13:00 ET)
# ----------------------------------------------------------------------
for early_day in ["2026-11-27", "2026-12-24"]:  # day after Thanksgiving, Xmas Eve
    before = session(f"{early_day}T12:00:00")
    assert before["is_open"] is True, f"{early_day} 12:00 should be open"
    assert before["is_early_close"] is True, f"{early_day} should be early close"
    assert before["regular_close"] == "13:00"
    at_close = session(f"{early_day}T13:00:00")
    assert at_close["is_open"] is False, f"{early_day} 13:00 should be closed"
    assert at_close["is_early_close"] is True
    after = session(f"{early_day}T13:30:00")
    assert after["is_open"] is False


# ----------------------------------------------------------------------
# Daylight saving: 10:00 ET is open in both EST (January) and EDT (July)
# ----------------------------------------------------------------------
winter = session("2026-01-05T10:00:00")  # Monday, EST
summer = session("2026-07-06T10:00:00")  # Monday, EDT
assert winter["is_open"] is True
assert summer["is_open"] is True
# Offsets differ, confirming timezone awareness (EST -05:00, EDT -04:00).
assert winter["as_of"].endswith("-05:00")
assert summer["as_of"].endswith("-04:00")


# ----------------------------------------------------------------------
# Timezone-aware input is converted to New York time
# ----------------------------------------------------------------------
# 14:00 UTC on 2026-07-06 == 10:00 EDT -> open.
aware_open = session(datetime(2026, 7, 6, 14, 0, tzinfo=timezone.utc))
assert aware_open["is_open"] is True
# 13:00 UTC on 2026-01-05 == 08:00 EST (pre-open) -> closed.
aware_closed = session(datetime(2026, 1, 5, 13, 0, tzinfo=timezone.utc))
assert aware_closed["is_open"] is False

# An aware ET datetime is handled directly.
aware_et = session(datetime(2026, 6, 29, 10, 0, tzinfo=ET))
assert aware_et["is_open"] is True


# ----------------------------------------------------------------------
# Naive datetimes are interpreted as New York wall-clock time
# ----------------------------------------------------------------------
naive = session(datetime(2026, 6, 29, 10, 0))  # no tzinfo
assert naive["is_open"] is True
assert naive["as_of"].endswith("-04:00")  # localized to America/New_York (EDT)
# Same wall-clock string routes to the same result.
assert session("2026-06-29T10:00:00")["is_open"] is True


# ----------------------------------------------------------------------
# Unavailable / fail-loud state: a date outside calendar coverage
# ----------------------------------------------------------------------
uncovered = session("2099-06-29T10:00:00")
assert uncovered["is_open"] is False
assert uncovered["available"] is False
assert uncovered["session"] == "unavailable"
assert "coverage" in uncovered["error"]
assert uncovered["is_session"] is None

# is_open() convenience mirrors session()["is_open"].
assert calendar.is_open("2026-06-29T10:00:00") is True
assert calendar.is_open("2026-06-28T10:00:00") is False


print("MarketCalendar test passed.")
