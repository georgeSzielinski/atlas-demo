class MarketDataValidator:
    """Deterministic validation for market data.

    Atlas trusts data only after validation. Every check is deterministic and
    offline-safe. Corporate action awareness and market calendar are explicit
    placeholders until real integrations are wired.
    """

    OHLC_FIELDS = ["open", "high", "low", "close"]

    def validate_rows(self, rows, ticker=None, supported_tickers=None):
        rows = rows or []
        checks = []
        errors = []
        warnings = []

        ticker_ok = True
        if ticker is not None and supported_tickers is not None:
            ticker_ok = ticker in supported_tickers
            if not ticker_ok:
                errors.append(f"Ticker {ticker} is not in the supported list.")
        checks.append(self._check("ticker_exists", ticker_ok))

        has_rows = len(rows) > 0
        if not has_rows:
            errors.append("No market rows were returned.")
        checks.append(self._check("rows_present", has_rows))

        timestamps = [self._timestamp(row) for row in rows]
        ordered = self._is_ordered(timestamps)
        if has_rows and not ordered:
            errors.append("Timestamps are not in ascending order.")
        checks.append(self._check("timestamps_ordered", ordered if has_rows else True))

        duplicates = [
            value for value in timestamps
            if value is not None and timestamps.count(value) > 1
        ]
        no_duplicates = len(duplicates) == 0
        if not no_duplicates:
            errors.append("Duplicate timestamps were detected.")
        checks.append(self._check("no_duplicate_rows", no_duplicates))

        missing_rows = [
            index for index, row in enumerate(rows)
            if self._has_missing(row)
        ]
        no_missing = len(missing_rows) == 0
        if not no_missing:
            errors.append(f"{len(missing_rows)} rows have missing values.")
        checks.append(self._check("no_missing_values", no_missing))

        inconsistent = [
            index for index, row in enumerate(rows)
            if self._ohlc_inconsistent(row)
        ]
        ohlc_ok = len(inconsistent) == 0
        if not ohlc_ok:
            errors.append(f"{len(inconsistent)} rows have inconsistent OHLC values.")
        checks.append(self._check("ohlc_consistent", ohlc_ok))

        checks.append(self._check(
            "corporate_action_awareness",
            True,
            note="Placeholder: corporate actions are not yet reconciled.",
        ))
        checks.append(self._check(
            "market_calendar",
            True,
            note="Placeholder: trading calendar and holidays are not modeled.",
        ))
        warnings.append("Corporate action awareness is a placeholder.")
        warnings.append("Market calendar validation is a placeholder.")

        valid = all(check["passed"] for check in checks)

        return {
            "valid": valid,
            "row_count": len(rows),
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
        }

    def validate_price(self, price, ticker=None, supported_tickers=None):
        checks = []
        errors = []

        ticker_ok = True
        if ticker is not None and supported_tickers is not None:
            ticker_ok = ticker in supported_tickers
            if not ticker_ok:
                errors.append(f"Ticker {ticker} is not in the supported list.")
        checks.append(self._check("ticker_exists", ticker_ok))

        present = price is not None
        if not present:
            errors.append("No price value was returned.")
        checks.append(self._check("price_present", present))

        numeric = present and self._is_number(price)
        if present and not numeric:
            errors.append("Price value is not numeric.")
        checks.append(self._check("price_numeric", numeric if present else False))

        positive = numeric and float(price) > 0
        if numeric and not positive:
            errors.append("Price value is not positive.")
        checks.append(self._check("price_positive", positive if numeric else False))

        valid = all(check["passed"] for check in checks)

        return {
            "valid": valid,
            "price": price,
            "checks": checks,
            "errors": errors,
        }

    def _check(self, name, passed, note=""):
        return {"check": name, "passed": bool(passed), "note": note}

    def _timestamp(self, row):
        return row.get("date") or row.get("timestamp")

    def _is_ordered(self, timestamps):
        clean = [value for value in timestamps if value is not None]

        if len(clean) != len(timestamps):
            return False

        return all(
            clean[index] <= clean[index + 1]
            for index in range(len(clean) - 1)
        )

    def _has_missing(self, row):
        for field in self.OHLC_FIELDS:
            if field in row and row.get(field) is None:
                return True

        if self._timestamp(row) is None:
            return True

        return False

    def _ohlc_inconsistent(self, row):
        values = {field: row.get(field) for field in self.OHLC_FIELDS}

        if any(value is None for value in values.values()):
            return False

        if not all(self._is_number(value) for value in values.values()):
            return True

        high = float(values["high"])
        low = float(values["low"])
        open_price = float(values["open"])
        close = float(values["close"])

        if high < low:
            return True

        if high < open_price or high < close:
            return True

        if low > open_price or low > close:
            return True

        return False

    def _is_number(self, value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
