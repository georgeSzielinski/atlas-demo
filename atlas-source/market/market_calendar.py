"""Timezone-aware exchange trading calendar.

This is the single place that knows whether a given moment is inside a real
exchange trading session. It wraps the maintained ``exchange_calendars``
library (NYSE / ``XNYS`` by default) so weekends, US market holidays, and early
closes are handled correctly instead of a naive weekday/time guess.

Design rules:

- Timezone aware. Sessions are evaluated in ``America/New_York`` via
  :class:`zoneinfo.ZoneInfo`. Aware inputs are converted to New York time;
  naive inputs are interpreted as New York wall-clock time (documented and
  tested behavior).
- No silent fallback. When the calendar cannot determine the session (library
  unavailable, a date outside the calendar's coverage, or a lookup failure) the
  result is an explicit ``available: False`` / ``session: "unavailable"`` state
  with ``is_open`` False, so automatic trading cannot run on an unknown session.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo


MARKET_TZ = ZoneInfo("America/New_York")
REGULAR_CLOSE = time(16, 0)
DEFAULT_EXCHANGE = "XNYS"


class MarketCalendar:
    """Real exchange trading calendar for a single exchange (default NYSE)."""

    def __init__(self, exchange=DEFAULT_EXCHANGE):
        self.exchange = exchange

    def is_open(self, as_of=None):
        return bool(self.session(as_of).get("is_open"))

    def session(self, as_of=None):
        """Return the trading session state for ``as_of``.

        ``as_of`` may be a ``datetime`` (aware or naive), an ISO string, or
        ``None`` (meaning now). Naive datetimes/strings are interpreted as
        America/New_York wall-clock time.
        """
        moment = self._to_et(as_of)
        is_weekday = moment.weekday() < 5

        try:
            import pandas as pd

            calendar = self._calendar()
        except Exception as error:
            return self._unavailable(
                moment, is_weekday, f"exchange calendar unavailable: {error}"
            )

        session_day = pd.Timestamp(moment.date())
        if not (calendar.first_session <= session_day <= calendar.last_session):
            return self._unavailable(
                moment,
                is_weekday,
                (
                    "date outside exchange calendar coverage "
                    f"({calendar.first_session.date()} to "
                    f"{calendar.last_session.date()})"
                ),
            )

        try:
            is_session = bool(calendar.is_session(session_day))
            is_open = False
            is_early_close = False
            regular_close = None
            if is_session:
                close_et = calendar.session_close(session_day).tz_convert(MARKET_TZ)
                regular_close = close_et.strftime("%H:%M")
                is_early_close = close_et.time() < REGULAR_CLOSE
                is_open = bool(calendar.is_open_on_minute(pd.Timestamp(moment)))
        except Exception as error:
            return self._unavailable(
                moment, is_weekday, f"session lookup failed: {error}"
            )

        return {
            "is_open": is_open,
            "session": "open" if is_open else "closed",
            "available": True,
            "is_weekday": is_weekday,
            "is_session": is_session,
            "is_holiday": (not is_session) and is_weekday,
            "is_early_close": is_early_close,
            "regular_close": regular_close,
            "as_of": moment.isoformat(),
            "timezone": "America/New_York",
            "market_calendar_placeholder": False,
            "calendar": self.exchange,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _calendar(self):
        import exchange_calendars as xcals

        return xcals.get_calendar(self.exchange)

    def _to_et(self, as_of):
        if as_of is None:
            return datetime.now(MARKET_TZ)

        if isinstance(as_of, datetime):
            moment = as_of
        else:
            try:
                moment = datetime.fromisoformat(str(as_of))
            except ValueError:
                return datetime.now(MARKET_TZ)

        if moment.tzinfo is None:
            # Naive input is interpreted as New York wall-clock time.
            return moment.replace(tzinfo=MARKET_TZ)

        return moment.astimezone(MARKET_TZ)

    def _unavailable(self, moment, is_weekday, reason):
        return {
            "is_open": False,
            "session": "unavailable",
            "available": False,
            "is_weekday": is_weekday,
            "is_session": None,
            "is_holiday": None,
            "is_early_close": None,
            "regular_close": None,
            "as_of": moment.isoformat(),
            "timezone": "America/New_York",
            "market_calendar_placeholder": False,
            "calendar": self.exchange,
            "error": reason,
            "note": (
                "Market session could not be determined; automatic trading "
                "must not run."
            ),
        }
