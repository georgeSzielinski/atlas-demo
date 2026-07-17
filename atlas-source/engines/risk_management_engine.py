class RiskManagementEngine:
    """Deterministic paper-trading risk gate for proposed orders."""

    DEFAULT_LIMITS = {
        "max_position_size": 0.25,
        "max_portfolio_exposure": 0.95,
        "minimum_cash_reserve": 0.0,
        "max_sector_exposure": 0.40,
        "max_position_count": 20,
        "max_correlation": 0.80,
    }

    SAFETY_FIELDS = {
        "paper_only": True,
        "broker_integration": False,
        "real_money": False,
        "human_approval_required_for_real_trading": True,
    }

    def size_positions(
        self,
        recommendations,
        portfolio=None,
        market_data=None,
        sizing_policy=None,
    ):
        portfolio = portfolio or {}
        market_data = market_data or {}
        sizing_policy = sizing_policy or {}
        positions = self._normalize_positions(portfolio.get("positions", {}))
        cash = self._number(portfolio.get("cash", 0))
        portfolio_value = self._portfolio_value_from_prices(
            cash,
            positions,
            market_data.get("prices", {}),
        )

        results = []
        for recommendation in recommendations:
            results.append(
                self._size_one_position(
                    recommendation,
                    positions,
                    portfolio_value,
                    market_data,
                    sizing_policy,
                )
            )

        return {
            **self.SAFETY_FIELDS,
            "status": "COMPLETED",
            "portfolio_value": round(portfolio_value, 4),
            "orders": results,
        }

    def _size_one_position(
        self,
        recommendation,
        positions,
        portfolio_value,
        market_data,
        sizing_policy,
    ):
        symbol = str(
            recommendation.get("symbol") or recommendation.get("ticker") or ""
        ).upper()
        sector = recommendation.get("sector")
        derivation = {
            "base_target_weight": None,
            "confidence_adjustment": None,
            "volatility_adjustment": None,
            "risk_budget_adjustment": None,
            "final_target_weight": None,
            "final_target_value": None,
            "current_value": None,
            "proposed_value": None,
            "proposed_quantity": None,
            "price_used": None,
            "skipped_adjustments": [],
        }

        if not symbol:
            return self._invalid_sizing_result(
                symbol,
                sector,
                derivation,
                "symbol is required for sizing.",
            )

        price = self._price_for_symbol(symbol, recommendation, market_data)
        derivation["price_used"] = price
        if price <= 0:
            return self._invalid_sizing_result(
                symbol,
                sector,
                derivation,
                "Valid positive price is required for sizing.",
            )

        base_weight = self._target_weight(recommendation, sizing_policy)
        if base_weight is None or base_weight <= 0:
            return self._invalid_sizing_result(
                symbol,
                sector,
                derivation,
                "Positive base target weight is required for sizing.",
            )
        derivation["base_target_weight"] = round(base_weight, 6)

        confidence = recommendation.get("confidence")
        if confidence is None:
            return self._invalid_sizing_result(
                symbol,
                sector,
                derivation,
                "Recommendation confidence is required for sizing.",
            )
        confidence_multiplier = round(self._number(confidence) / 100, 6)
        adjusted_weight = base_weight * confidence_multiplier
        derivation["confidence_adjustment"] = {
            "status": "APPLIED",
            "confidence": self._number(confidence),
            "multiplier": confidence_multiplier,
            "weight_after_adjustment": round(adjusted_weight, 6),
            "reason": "Base target weight multiplied by confidence percentage.",
        }

        volatility = self._lookup_metric(market_data, "volatility", symbol)
        if volatility is None:
            self._skip_adjustment(
                derivation,
                "volatility",
                "Volatility data is unavailable; no volatility adjustment applied.",
            )
        else:
            target_volatility = sizing_policy.get("target_volatility")
            if target_volatility is None or self._number(target_volatility) <= 0:
                return self._invalid_sizing_result(
                    symbol,
                    sector,
                    derivation,
                    "Positive target_volatility is required when volatility data exists.",
                )
            volatility = self._number(volatility)
            if volatility <= 0:
                return self._invalid_sizing_result(
                    symbol,
                    sector,
                    derivation,
                    "Volatility must be positive when provided.",
                )
            volatility_multiplier = round(self._number(target_volatility) / volatility, 6)
            adjusted_weight *= volatility_multiplier
            derivation["volatility_adjustment"] = {
                "status": "APPLIED",
                "volatility": volatility,
                "target_volatility": self._number(target_volatility),
                "multiplier": volatility_multiplier,
                "weight_after_adjustment": round(adjusted_weight, 6),
                "reason": "Confidence-adjusted weight multiplied by target volatility divided by observed volatility.",
            }

        risk_budget = self._lookup_metric(market_data, "risk_budget", symbol)
        if risk_budget is None:
            self._skip_adjustment(
                derivation,
                "risk_budget",
                "Risk budget data is unavailable; no risk budget adjustment applied.",
            )
        else:
            risk_multiplier = self._risk_budget_multiplier(risk_budget)
            if risk_multiplier is None or risk_multiplier <= 0:
                return self._invalid_sizing_result(
                    symbol,
                    sector,
                    derivation,
                    "Positive risk budget multiplier is required when risk budget data exists.",
                )
            adjusted_weight *= risk_multiplier
            derivation["risk_budget_adjustment"] = {
                "status": "APPLIED",
                "risk_budget": risk_budget,
                "multiplier": round(risk_multiplier, 6),
                "weight_after_adjustment": round(adjusted_weight, 6),
                "reason": "Volatility-adjusted weight multiplied by risk budget multiplier.",
            }

        final_target_value = portfolio_value * adjusted_weight
        current_value = self._position_value(
            positions.get(symbol, {}),
            fallback_price=price,
        )
        proposed_value = final_target_value - current_value
        side = "BUY" if proposed_value >= 0 else "SELL"
        proposed_quantity = round(abs(proposed_value) / price, 6)

        derivation["final_target_weight"] = round(adjusted_weight, 6)
        derivation["final_target_value"] = round(final_target_value, 4)
        derivation["current_value"] = round(current_value, 4)
        derivation["proposed_value"] = round(proposed_value, 4)
        derivation["proposed_quantity"] = proposed_quantity

        order = {
            "symbol": symbol,
            "side": side,
            "quantity": proposed_quantity,
            "price": price,
            "sector": sector,
        }

        return {
            "symbol": symbol,
            "status": "VALID",
            "order": order,
            "derivation": derivation,
        }

    def evaluate(self, order, portfolio=None, limits=None, market_data=None):
        portfolio = portfolio or {}
        limits = {**self.DEFAULT_LIMITS, **(limits or {})}
        market_data = market_data or {}

        normalized_order = self._normalize_order(order)
        positions = self._normalize_positions(portfolio.get("positions", {}))
        cash = self._number(portfolio.get("cash", 0))
        symbol = normalized_order["symbol"]
        side = normalized_order["side"]
        quantity = normalized_order["quantity"]
        price = normalized_order["price"]
        order_value = round(quantity * price, 4)

        holdings = positions.get(symbol, {"quantity": 0, "price": price, "sector": None})
        current_quantity = self._number(holdings.get("quantity", 0))
        sector = normalized_order.get("sector") or holdings.get("sector") or "UNKNOWN"

        current_total_value = self._portfolio_value(cash, positions, symbol, price)
        post_positions = self._post_order_positions(
            positions,
            symbol,
            side,
            quantity,
            price,
            sector,
        )
        post_cash = cash - order_value if side == "BUY" else cash + order_value
        post_total_value = self._portfolio_value(post_cash, post_positions, symbol, price)

        checks = [
            self._affordability_check(side, cash, order_value),
            self._sell_quantity_check(side, quantity, current_quantity),
            self._minimum_cash_reserve_check(post_cash, limits),
            self._max_position_size_check(symbol, post_positions, post_total_value, limits),
            self._max_portfolio_exposure_check(post_positions, post_total_value, limits),
            self._sector_exposure_check(sector, post_positions, post_total_value, limits),
            self._max_position_count_check(post_positions, limits),
            self._correlation_check(symbol, post_positions, market_data, limits),
        ]

        rejections = [check for check in checks if check["status"] == "REJECTED"]
        status = "REJECTED" if rejections else "APPROVED"

        return {
            **self.SAFETY_FIELDS,
            "status": status,
            "approved": status == "APPROVED",
            "order": {
                **normalized_order,
                "requested_quantity": quantity,
                "order_value": order_value,
            },
            "portfolio_before": {
                "cash": round(cash, 4),
                "total_value": round(current_total_value, 4),
                "position_count": self._position_count(positions),
            },
            "portfolio_after": {
                "cash": round(post_cash, 4),
                "total_value": round(post_total_value, 4),
                "position_count": self._position_count(post_positions),
            },
            "checks": checks,
            "rejections": rejections,
        }

    def _normalize_order(self, order):
        symbol = str(order.get("symbol") or order.get("ticker") or "").upper()
        side = str(order.get("side") or order.get("action") or "").upper()
        quantity = self._number(order.get("quantity", order.get("shares", 0)))
        price = self._number(order.get("price", order.get("limit_price", 0)))

        if not symbol:
            raise ValueError("order symbol is required")
        if side not in {"BUY", "SELL"}:
            raise ValueError("order side must be BUY or SELL")
        if quantity <= 0:
            raise ValueError("order quantity must be positive")
        if price <= 0:
            raise ValueError("order price must be positive")

        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "sector": order.get("sector"),
        }

    def _normalize_positions(self, raw_positions):
        positions = {}
        for symbol, raw in raw_positions.items():
            if isinstance(raw, dict):
                quantity = self._number(
                    raw.get("quantity", raw.get("shares", raw.get("qty", 0)))
                )
                price = self._number(raw.get("price", raw.get("market_price", 0)))
                market_value = raw.get("market_value")
                if price == 0 and market_value is not None and quantity:
                    price = self._number(market_value) / quantity
                sector = raw.get("sector")
            else:
                quantity = self._number(raw)
                price = 0
                sector = None

            if quantity > 0:
                positions[str(symbol).upper()] = {
                    "quantity": quantity,
                    "price": price,
                    "sector": sector,
                }
        return positions

    def _post_order_positions(self, positions, symbol, side, quantity, price, sector):
        post = {
            ticker: {
                "quantity": data["quantity"],
                "price": data["price"],
                "sector": data.get("sector"),
            }
            for ticker, data in sorted(positions.items())
        }
        current = post.get(symbol, {"quantity": 0, "price": price, "sector": sector})

        if side == "BUY":
            current["quantity"] = current.get("quantity", 0) + quantity
            current["price"] = price
            current["sector"] = sector
            post[symbol] = current
        else:
            current["quantity"] = current.get("quantity", 0) - quantity
            current["price"] = price
            current["sector"] = sector
            if current["quantity"] > 0:
                post[symbol] = current
            elif symbol in post:
                del post[symbol]

        return post

    def _affordability_check(self, side, cash, order_value):
        if side != "BUY":
            return self._approved(
                "affordability",
                "available cash",
                cash,
                "Affordability applies only to buy orders.",
            )

        if order_value <= cash:
            return self._approved(
                "affordability",
                cash,
                order_value,
                "Buy order value is within available cash.",
            )

        return self._rejected(
            "affordability",
            cash,
            order_value,
            "Buy order value exceeds available cash; order is rejected without clipping.",
        )

    def _sell_quantity_check(self, side, quantity, current_quantity):
        if side != "SELL":
            return self._approved(
                "sell_quantity_not_exceeding_holdings",
                "current holdings",
                current_quantity,
                "Sell quantity check applies only to sell orders.",
            )

        if quantity <= current_quantity:
            return self._approved(
                "sell_quantity_not_exceeding_holdings",
                current_quantity,
                quantity,
                "Sell quantity does not exceed current holdings.",
            )

        return self._rejected(
            "sell_quantity_not_exceeding_holdings",
            current_quantity,
            quantity,
            "Sell quantity exceeds current holdings; order is rejected without clipping.",
        )

    def _minimum_cash_reserve_check(self, post_cash, limits):
        limit = self._number(limits["minimum_cash_reserve"])
        if post_cash >= limit:
            return self._approved(
                "minimum_cash_reserve",
                limit,
                post_cash,
                "Post-order cash meets the minimum reserve.",
            )

        return self._rejected(
            "minimum_cash_reserve",
            limit,
            post_cash,
            "Post-order cash would fall below the minimum reserve.",
        )

    def _max_position_size_check(self, symbol, positions, total_value, limits):
        limit = self._number(limits["max_position_size"])
        measured = self._position_value(positions.get(symbol, {})) / total_value
        measured = round(measured, 6)
        if measured <= limit:
            return self._approved(
                "max_position_size",
                limit,
                measured,
                "Post-order position size is within the maximum limit.",
            )

        return self._rejected(
            "max_position_size",
            limit,
            measured,
            "Post-order position size would exceed the maximum position limit.",
        )

    def _max_portfolio_exposure_check(self, positions, total_value, limits):
        limit = self._number(limits["max_portfolio_exposure"])
        measured = round(self._invested_value(positions) / total_value, 6)
        if measured <= limit:
            return self._approved(
                "max_portfolio_exposure",
                limit,
                measured,
                "Post-order portfolio exposure is within the maximum limit.",
            )

        return self._rejected(
            "max_portfolio_exposure",
            limit,
            measured,
            "Post-order portfolio exposure would exceed the maximum limit.",
        )

    def _sector_exposure_check(self, sector, positions, total_value, limits):
        limit = self._number(limits["max_sector_exposure"])
        sector_value = sum(
            self._position_value(position)
            for position in positions.values()
            if (position.get("sector") or "UNKNOWN") == sector
        )
        measured = round(sector_value / total_value, 6)
        if measured <= limit:
            return self._approved(
                "sector_exposure",
                limit,
                measured,
                f"Post-order {sector} sector exposure is within the maximum limit.",
            )

        return self._rejected(
            "sector_exposure",
            limit,
            measured,
            f"Post-order {sector} sector exposure would exceed the maximum limit.",
        )

    def _max_position_count_check(self, positions, limits):
        limit = int(limits["max_position_count"])
        measured = self._position_count(positions)
        if measured <= limit:
            return self._approved(
                "max_position_count",
                limit,
                measured,
                "Post-order position count is within the maximum limit.",
            )

        return self._rejected(
            "max_position_count",
            limit,
            measured,
            "Post-order position count would exceed the maximum limit.",
        )

    def _correlation_check(self, symbol, positions, market_data, limits):
        correlations = market_data.get("correlations")
        if not correlations:
            return {
                "rule": "correlation",
                "status": "NOT_EVALUATED",
                "limit": self._number(limits["max_correlation"]),
                "measured": None,
                "reason": "Correlation data is unavailable; correlation risk was not evaluated.",
            }

        peers = [
            ticker for ticker in positions
            if ticker != symbol and positions[ticker].get("quantity", 0) > 0
        ]
        measured = 0
        for peer in peers:
            measured = max(
                measured,
                self._number(correlations.get(symbol, {}).get(peer, 0)),
                self._number(correlations.get(peer, {}).get(symbol, 0)),
            )
        measured = round(measured, 6)
        limit = self._number(limits["max_correlation"])
        if measured <= limit:
            return self._approved(
                "correlation",
                limit,
                measured,
                "Available correlation data is within the maximum limit.",
            )

        return self._rejected(
            "correlation",
            limit,
            measured,
            "Available correlation data exceeds the maximum limit.",
        )

    def _portfolio_value(self, cash, positions, order_symbol, order_price):
        return max(
            0.000001,
            cash + sum(
                self._position_value(position, order_price if symbol == order_symbol else None)
                for symbol, position in positions.items()
            ),
        )

    def _position_value(self, position, fallback_price=None):
        quantity = self._number(position.get("quantity", 0))
        price = self._number(position.get("price", fallback_price or 0))
        return quantity * price

    def _invested_value(self, positions):
        return sum(self._position_value(position) for position in positions.values())

    def _position_count(self, positions):
        return sum(1 for position in positions.values() if position.get("quantity", 0) > 0)

    def _portfolio_value_from_prices(self, cash, positions, prices):
        return max(
            0.000001,
            cash + sum(
                self._position_value(
                    position,
                    fallback_price=self._number(prices.get(symbol, 0)),
                )
                for symbol, position in positions.items()
            ),
        )

    def _price_for_symbol(self, symbol, recommendation, market_data):
        prices = market_data.get("prices", {})
        return self._number(
            recommendation.get("price", recommendation.get("limit_price", prices.get(symbol, 0)))
        )

    def _target_weight(self, recommendation, sizing_policy):
        value = recommendation.get(
            "base_target_weight",
            sizing_policy.get("base_target_weight"),
        )
        if value is None:
            return None
        return self._number(value)

    def _lookup_metric(self, market_data, metric, symbol):
        candidates = [
            market_data.get(metric),
            market_data.get(f"{metric}s"),
        ]
        for candidate in candidates:
            if isinstance(candidate, dict) and symbol in candidate:
                return candidate[symbol]
        return None

    def _risk_budget_multiplier(self, risk_budget):
        if isinstance(risk_budget, dict):
            value = risk_budget.get("multiplier")
        else:
            value = risk_budget
        if value is None:
            return None
        return self._number(value)

    def _skip_adjustment(self, derivation, adjustment, reason):
        skipped = {
            "adjustment": adjustment,
            "status": "SKIPPED",
            "reason": reason,
        }
        derivation[f"{adjustment}_adjustment"] = skipped
        derivation["skipped_adjustments"].append(skipped)

    def _invalid_sizing_result(self, symbol, sector, derivation, reason):
        return {
            "symbol": symbol,
            "status": "INVALID",
            "order": None,
            "derivation": derivation,
            "error": reason,
            "reason": reason,
            "sector": sector,
        }

    def _approved(self, rule, limit, measured, reason):
        return {
            "rule": rule,
            "status": "APPROVED",
            "limit": limit,
            "measured": measured,
            "reason": reason,
        }

    def _rejected(self, rule, limit, measured, reason):
        return {
            "rule": rule,
            "status": "REJECTED",
            "limit": limit,
            "measured": measured,
            "reason": reason,
        }

    def _number(self, value):
        if value is None:
            return 0
        return float(value)
