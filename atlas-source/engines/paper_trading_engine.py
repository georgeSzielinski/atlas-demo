import hashlib
import json
import math
from datetime import datetime


class PaperTradingEngine:
    INITIAL_CASH = 100000
    POSITION_SIZE = 0.1
    BENCHMARKS = ["S&P 500", "NASDAQ-100", "Equal Weight Placeholder"]
    DEMO_DATE = "2026-06-30"
    HISTORICAL_PRICE_REPLAY = "historical_price_replay"
    HISTORICAL_PRICE_SIMULATION = HISTORICAL_PRICE_REPLAY
    BROKER_PAPER_PENDING = "broker_paper_pending"

    def run(
        self,
        recommendations,
        market_prices,
        as_of_date=None,
        portfolio=None,
        benchmark_returns=None,
        simulation_metadata=None,
        persist=False,
    ):
        metadata = self._simulation_metadata(simulation_metadata)
        date = as_of_date or metadata.get("simulated_at") or datetime.now().isoformat()
        metadata["simulated_at"] = date
        state = self._portfolio_state(portfolio)
        trades = []

        for recommendation in recommendations:
            trade = self.virtual_execute(
                recommendation,
                market_prices,
                state,
                date,
            )
            if trade is not None:
                trades.append(trade)

        snapshot = self.portfolio_snapshot(state, market_prices, date)
        snapshot["metadata"] = metadata
        history = (portfolio or {}).get("history", []) + [snapshot]
        performance = self.performance_report(
            history,
            trades + (portfolio or {}).get("trades", []),
            benchmark_returns or {},
        )
        performance["metadata"] = metadata
        research = self.research_report(trades + (portfolio or {}).get("trades", []))
        for trade in trades:
            trade["metadata"] = metadata
        report = {
            "portfolio": snapshot,
            "positions": state["positions"],
            "trades": trades,
            "performance": performance,
            "research": research,
            "metadata": metadata,
            "policy": self.policy() | metadata,
        }
        report["portfolio_construction"] = self.portfolio_construction_guidance(
            recommendations,
            snapshot,
            performance,
        )

        if persist:
            self.persist_report(report)

        return report

    def virtual_execute(self, recommendation, market_prices, state, date):
        ticker = recommendation.get("ticker", "").upper()
        action = recommendation.get("action", "HOLD").upper()
        price = market_prices.get(ticker)

        if not ticker or price is None or price <= 0:
            return None

        if action == "BUY":
            return self._buy(ticker, price, recommendation, state, date)

        if action == "SELL":
            return self._sell(ticker, price, recommendation, state, date)

        return None

    def run_historical_price_simulation(
        self,
        recommendations,
        historical_rows=None,
        tickers=None,
        start_date=None,
        end_date=None,
        historical_adapter=None,
        portfolio=None,
        simulation_metadata=None,
        persist=False,
    ):
        rows, source = self._historical_rows(
            recommendations=recommendations,
            historical_rows=historical_rows,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            historical_adapter=historical_adapter,
        )
        grouped = self._historical_rows_by_ticker(rows)
        if not grouped:
            raise ValueError("Historical price simulation requires two prices for at least one ticker.")
        entry_prices = {}
        current_prices = {}

        for ticker, ticker_rows in grouped.items():
            entry_prices[ticker] = ticker_rows[0]["close"]
            current_prices[ticker] = ticker_rows[-1]["close"]

        metadata = self._simulation_metadata(
            {
                **(simulation_metadata or {}),
                "mode": self.HISTORICAL_PRICE_SIMULATION,
                "data_source": source["data_source"],
                "fallback_used": source["fallback_used"],
                "price_backed": True,
                "last_price_date": source["last_price_date"],
            }
        )
        report = self.run(
            recommendations=recommendations,
            market_prices=entry_prices,
            as_of_date=source["entry_price_date"],
            portfolio=portfolio,
            benchmark_returns={},
            simulation_metadata=metadata,
            persist=False,
        )
        update_report = self.update_prices(
            market_prices=current_prices,
            as_of_date=source["last_price_date"],
            portfolio={
                "cash": report["portfolio"]["cash"],
                "positions": report["positions"],
                "realized_pl": report["portfolio"]["realized_pl"],
                "history": [report["portfolio"]],
                "trades": report["trades"],
            },
            benchmark_returns={},
            simulation_metadata=metadata,
            persist=False,
        )
        update_report["trades"] = report["trades"]
        update_report["research"] = self.research_report(report["trades"])
        update_report["metadata"] = metadata
        update_report["policy"] = self.policy() | metadata
        update_report["price_source"] = source
        update_report["portfolio_construction"] = self.portfolio_construction_guidance(
            recommendations,
            update_report["portfolio"],
            update_report["performance"],
        )

        if persist:
            self.persist_report(update_report)

        return update_report

    def run_historical_price_replay(
        self,
        recommendations,
        historical_rows=None,
        tickers=None,
        start_date=None,
        end_date=None,
        starting_cash=None,
        historical_adapter=None,
        simulation_metadata=None,
        persist=False,
    ):
        requested_tickers = sorted({
            item.get("ticker", "").upper()
            for item in recommendations
            if item.get("ticker")
        } | {str(ticker).upper() for ticker in (tickers or [])})
        replay_id = (simulation_metadata or {}).get("run_id") or "paper-replay"

        # Historical replay must use price-backed rows or fail loudly. It must
        # NEVER silently fall back to demo/mock rows.
        rows, source, failure_reason = self._replay_price_rows(
            recommendations=recommendations,
            historical_rows=historical_rows,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            historical_adapter=historical_adapter,
        )

        by_date = {}
        if not failure_reason:
            by_date = self._historical_rows_by_date(rows)
            missing = self._missing_price_dates(by_date, requested_tickers)
            if missing:
                failure_reason = "Historical prices unavailable"
                source = {**source, "missing_prices": missing}

        price_backed = failure_reason is None
        metadata = self._simulation_metadata(
            {
                **(simulation_metadata or {}),
                "mode": self.HISTORICAL_PRICE_REPLAY,
                "data_source": source.get("data_source", "unavailable"),
                "fallback_used": bool(source.get("fallback_used", False)) or not price_backed,
                "price_backed": price_backed,
                "last_price_date": source.get("last_price_date"),
            }
        )

        if failure_reason:
            audit = self._replay_audit(
                replay_id=replay_id,
                mode=self.HISTORICAL_PRICE_REPLAY,
                requested_tickers=requested_tickers,
                start_date=start_date,
                end_date=end_date,
                rows=rows,
                source=source,
                price_backed=False,
                failure_reason=failure_reason,
                trades_generated=0,
                portfolio_points_generated=0,
            )
            return self._failed_replay_report(metadata, source, audit, failure_reason)

        state = self._portfolio_state({
            "cash": starting_cash or self.INITIAL_CASH,
            "positions": {},
            "realized_pl": 0,
            "history": [],
        })
        replay_history = []
        trades = []
        active_tickers = set()

        for index, date in enumerate(sorted(by_date)):
            prices = {
                ticker: by_date[date][ticker]["close"]
                for ticker in requested_tickers
            }
            day_recommendations = self._replay_recommendations(
                recommendations,
                date,
                active_tickers,
            )

            for recommendation in day_recommendations:
                trade = self.virtual_execute(recommendation, prices, state, date)
                if trade is not None:
                    trade["metadata"] = metadata
                    trades.append(trade)
                    if trade["action"] == "BUY":
                        active_tickers.add(trade["ticker"])
                    elif trade["action"] == "SELL":
                        active_tickers.discard(trade["ticker"])

            snapshot = self.portfolio_snapshot(state, prices, date)
            snapshot["metadata"] = metadata
            snapshot["replay_day"] = index + 1
            state["history"] = replay_history + [snapshot]
            replay_history.append(snapshot)

        performance = self.performance_report(replay_history, trades, {})
        performance["metadata"] = metadata
        audit = self._replay_audit(
            replay_id=replay_id,
            mode=self.HISTORICAL_PRICE_REPLAY,
            requested_tickers=requested_tickers,
            start_date=start_date,
            end_date=end_date,
            rows=rows,
            source=source,
            price_backed=True,
            failure_reason=None,
            trades_generated=len(trades),
            portfolio_points_generated=len(replay_history),
        )
        performance["replay_audit"] = audit
        report = {
            "portfolio": replay_history[-1],
            "positions": state["positions"],
            "trades": trades,
            "performance": performance,
            "research": self.research_report(trades),
            "metadata": metadata,
            "policy": self.policy() | metadata,
            "portfolio_construction": {},
            "price_source": source,
            "replay_history": replay_history,
            "replay_status": "COMPLETED",
            "price_backed": True,
            "error": None,
            "audit": audit,
            "dates_tested": sorted(by_date),
        }

        if persist:
            self.persist_report(report)

        return report

    def update_prices(
        self,
        market_prices,
        as_of_date=None,
        portfolio=None,
        benchmark_returns=None,
        simulation_metadata=None,
        persist=False,
    ):
        return self.run(
            recommendations=[],
            market_prices=market_prices,
            as_of_date=as_of_date,
            portfolio=portfolio,
            benchmark_returns=benchmark_returns,
            simulation_metadata=simulation_metadata,
            persist=persist,
        )

    def portfolio_snapshot(self, state, market_prices, date):
        current_value = 0
        unrealized = 0

        for ticker, position in state["positions"].items():
            price = market_prices.get(ticker, position["cost_basis"])
            value = round(position["quantity"] * price, 2)
            basis = round(position["quantity"] * position["cost_basis"], 2)
            position["current_price"] = price
            position["current_value"] = value
            position["unrealized_pl"] = round(value - basis, 2)
            current_value += value
            unrealized += value - basis

        portfolio_value = round(state["cash"] + current_value, 2)
        previous = state["history"][-1]["portfolio_value"] if state["history"] else self.INITIAL_CASH
        daily_return = self._percentage(portfolio_value, previous)
        total_return = self._percentage(portfolio_value, self.INITIAL_CASH)

        return {
            "date": date,
            "cash": round(state["cash"], 2),
            "positions": state["positions"],
            "current_value": round(current_value, 2),
            "realized_pl": round(state["realized_pl"], 2),
            "unrealized_pl": round(unrealized, 2),
            "portfolio_value": portfolio_value,
            "daily_return": daily_return,
            "total_return": total_return,
        }

    def performance_report(self, history, trades, benchmark_returns):
        daily_returns = [
            item.get("daily_return", 0)
            for item in history
        ]
        closed = [
            trade for trade in trades
            if trade.get("exit_price") is not None
        ]
        wins = [
            trade for trade in closed
            if trade.get("profit_loss", 0) > 0
        ]
        total_return = history[-1]["total_return"] if history else 0
        sp_return = benchmark_returns.get("S&P 500", 0)

        return {
            "daily_return": daily_returns[-1] if daily_returns else 0,
            "total_return": total_return,
            "win_rate": self._rate(len(wins), len(closed)),
            "sharpe": self._sharpe(daily_returns),
            "sortino": self._sortino(daily_returns),
            "max_drawdown": self._max_drawdown([
                item.get("portfolio_value", self.INITIAL_CASH)
                for item in history
            ]),
            "alpha_vs_sp": round(total_return - sp_return, 4),
            "beta_placeholder": 0,
            "volatility": self._standard_deviation(daily_returns),
            "benchmark_comparison": self.benchmark_comparison(
                total_return,
                benchmark_returns,
            ),
            "paper_validation_source": True,
        }

    def benchmark_comparison(self, total_return, benchmark_returns):
        return [
            {
                "benchmark": benchmark,
                "benchmark_return": benchmark_returns.get(benchmark, 0),
                "paper_return": total_return,
                "alpha": round(
                    total_return - benchmark_returns.get(benchmark, 0),
                    4,
                ),
            }
            for benchmark in self.BENCHMARKS
        ]

    def research_report(self, trades):
        closed = [
            trade for trade in trades
            if trade.get("exit_price") is not None
        ]

        return {
            "best_trades": self._ranked_trades(closed, reverse=True)[:5],
            "worst_trades": self._ranked_trades(closed, reverse=False)[:5],
            "biggest_winners": self._ranked_trades(closed, reverse=True)[:5],
            "biggest_mistakes": self._ranked_trades(closed, reverse=False)[:5],
            "longest_holds": sorted(
                closed,
                key=lambda trade: (
                    trade.get("holding_period") or 0,
                    trade.get("ticker", ""),
                ),
                reverse=True,
            )[:5],
            "most_profitable_sectors": self._sector_profitability(closed),
            "policy": (
                "Paper trading research is simulated only and does not "
                "execute broker orders."
            ),
        }

    def persist_report(self, report):
        from database.repository import save_paper_trading_report

        save_paper_trading_report(report)

    def portfolio_construction_guidance(
        self,
        recommendations,
        portfolio,
        performance,
    ):
        from engines.portfolio_construction_engine import PortfolioConstructionEngine

        return PortfolioConstructionEngine().build(
            recommendations=recommendations,
            paper_portfolio=portfolio,
            risk_metrics={
                "volatility": performance.get("volatility", 0),
                "max_drawdown": performance.get("max_drawdown", 0),
            },
        )

    def policy(self):
        return {
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "automatic_execution": False,
            "changes_recommendation_behavior": False,
            "broker_paper_pending": False,
        }

    def _simulation_metadata(self, metadata=None):
        source = metadata or {}
        run_number = source.get("run_number", 0)
        run_id = source.get("run_id") or (
            f"paper-sim-{run_number:04d}" if run_number else "paper-sim"
        )

        return {
            "run_id": run_id,
            "run_number": run_number,
            "simulated_at": source.get("simulated_at"),
            "mode": source.get("mode", "simulated_paper"),
            "data_source": source.get("data_source", "deterministic_simulation"),
            "fallback_used": bool(source.get("fallback_used", False)),
            "price_backed": bool(source.get("price_backed", False)),
            "last_price_date": source.get("last_price_date"),
        }

    def demo_report(self):
        """DEPRECATED compatibility fixture.

        Demo paper trading was removed from the product. This report must
        never be returned by Paper Trading API endpoints or shown in the
        Paper Trading UI; it remains only for legacy dashboard fallbacks
        outside Paper Trading until those are migrated.
        """
        return json.loads(json.dumps({
            "portfolio": {
                "id": "SIMULATED-DEMO",
                "date": self.DEMO_DATE,
                "cash": 76250,
                "positions": {
                    "AAPL": {
                        "ticker": "AAPL",
                        "quantity": 40,
                        "cost_basis": 185,
                        "entry_date": "2026-06-24",
                        "current_price": 192.5,
                        "current_value": 7700,
                        "unrealized_pl": 300,
                        "status": "SIMULATED",
                    },
                    "MSFT": {
                        "ticker": "MSFT",
                        "quantity": 22,
                        "cost_basis": 425,
                        "entry_date": "2026-06-25",
                        "current_price": 418,
                        "current_value": 9196,
                        "unrealized_pl": -154,
                        "status": "SIMULATED",
                    },
                    "NVDA": {
                        "ticker": "NVDA",
                        "quantity": 60,
                        "cost_basis": 118,
                        "entry_date": "2026-06-26",
                        "current_price": 124.1,
                        "current_value": 7446,
                        "unrealized_pl": 366,
                        "status": "SIMULATED",
                    },
                },
                "current_value": 24342,
                "realized_pl": 980,
                "unrealized_pl": 512,
                "portfolio_value": 100592,
                "daily_return": 0.41,
                "total_return": 0.592,
                "status": "SIMULATED",
                "simulated": True,
                "data_source": "SIMULATED demo paper portfolio",
            },
            "trades": [
                {
                    "trade_id": "SIMULATED-DEMO-AAPL-BUY",
                    "ticker": "AAPL",
                    "action": "BUY",
                    "entry_date": "2026-06-24",
                    "entry_price": 185,
                    "exit_date": None,
                    "exit_price": None,
                    "holding_period": None,
                    "quantity": 40,
                    "profit_loss": 0,
                    "reason": "SIMULATED demo paper entry.",
                    "recommendation_snapshot": {
                        "ticker": "AAPL",
                        "action": "BUY",
                        "sector": "Technology",
                        "status": "SIMULATED",
                    },
                    "status": "SIMULATED",
                    "simulated": True,
                },
                {
                    "trade_id": "SIMULATED-DEMO-GOOGL-SELL",
                    "ticker": "GOOGL",
                    "action": "SELL",
                    "entry_date": "2026-06-20",
                    "entry_price": 170,
                    "exit_date": self.DEMO_DATE,
                    "exit_price": 177,
                    "holding_period": 10,
                    "quantity": 50,
                    "profit_loss": 350,
                    "reason": "SIMULATED demo profit-taking exit.",
                    "recommendation_snapshot": {
                        "ticker": "GOOGL",
                        "action": "SELL",
                        "sector": "Communication Services",
                        "status": "SIMULATED",
                    },
                    "status": "SIMULATED",
                    "simulated": True,
                },
                {
                    "trade_id": "SIMULATED-DEMO-AMD-SELL",
                    "ticker": "AMD",
                    "action": "SELL",
                    "entry_date": "2026-06-21",
                    "entry_price": 155,
                    "exit_date": self.DEMO_DATE,
                    "exit_price": 142.5,
                    "holding_period": 9,
                    "quantity": 28,
                    "profit_loss": -350,
                    "reason": "SIMULATED demo risk-control exit.",
                    "recommendation_snapshot": {
                        "ticker": "AMD",
                        "action": "SELL",
                        "sector": "Semiconductors",
                        "status": "SIMULATED",
                    },
                    "status": "SIMULATED",
                    "simulated": True,
                },
            ],
            "performance": {
                "daily_return": 0.41,
                "total_return": 0.592,
                "win_rate": 50,
                "sharpe": 0.82,
                "sortino": 1.1,
                "max_drawdown": -0.74,
                "alpha_vs_sp": 0.192,
                "beta_placeholder": 0,
                "volatility": 0.36,
                "benchmark_comparison": [
                    {
                        "benchmark": "S&P 500",
                        "benchmark_return": 0.4,
                        "paper_return": 0.592,
                        "alpha": 0.192,
                    },
                    {
                        "benchmark": "NASDAQ-100",
                        "benchmark_return": 0.55,
                        "paper_return": 0.592,
                        "alpha": 0.042,
                    },
                    {
                        "benchmark": "Equal Weight Placeholder",
                        "benchmark_return": 0.25,
                        "paper_return": 0.592,
                        "alpha": 0.342,
                    },
                ],
                "paper_validation_source": True,
                "status": "SIMULATED",
                "simulated": True,
            },
            "research": {
                "best_trades": [],
                "worst_trades": [],
                "biggest_winners": [],
                "biggest_mistakes": [],
                "longest_holds": [],
                "most_profitable_sectors": [
                    {
                        "sector": "Communication Services",
                        "profit_loss": 350,
                    },
                    {
                        "sector": "Semiconductors",
                        "profit_loss": -350,
                    },
                ],
                "policy": (
                    "SIMULATED paper trading research only; no broker orders "
                    "or real money."
                ),
                "status": "SIMULATED",
                "simulated": True,
            },
            "policy": self.policy() | {
                "status": "SIMULATED",
                "simulated": True,
                "demo_data": True,
                "data_source": "SIMULATED demo paper portfolio",
            },
        }))

    def demo_recommendations(self):
        """DEPRECATED compatibility fixture; never shown in Paper Trading UI."""
        return [
            {
                "ticker": "AAPL",
                "action": "BUY",
                "confidence": 88,
                "reason": "SIMULATED paper test allocation.",
                "sector": "Technology",
                "status": "SIMULATED",
            },
            {
                "ticker": "MSFT",
                "action": "BUY",
                "confidence": 82,
                "reason": "SIMULATED paper diversification entry.",
                "sector": "Technology",
                "status": "SIMULATED",
            },
            {
                "ticker": "NVDA",
                "action": "HOLD",
                "confidence": 76,
                "reason": "SIMULATED watchlist hold.",
                "sector": "Semiconductors",
                "status": "SIMULATED",
            },
        ]

    def market_prices(self, tickers, manager=None, use_cache=True):
        """Validated latest prices from the Market Data Manager.

        Paper trading consumes validated market prices sourced through the
        Market Data Manager (mock/deterministic by default, with graceful
        fallback). This changes no execution behavior: prices are still
        simulated, no broker is connected, and no real orders are placed.
        """
        if manager is None:
            from market.market_data_manager import MarketDataManager

            manager = MarketDataManager()

        result = manager.latest_prices(tickers, use_cache=use_cache)

        return {
            "prices": result["prices"],
            "provider": result["requested_provider"],
            "fallback_used": result["fallback_used"],
            "validated": result["validated"],
            "as_of": result["as_of"],
            "policy": self.policy() | {"data_source": "MarketDataManager"},
        }

    def demo_market_prices(self, step=0):
        """DEPRECATED compatibility fixture; never shown in Paper Trading UI."""
        return {
            "AAPL": round(185 + step * 3, 2),
            "MSFT": round(420 + step * 4, 2),
            "NVDA": round(122 + step * 2, 2),
        }

    def demo_benchmark_returns(self, step=0):
        """DEPRECATED compatibility fixture; never shown in Paper Trading UI."""
        return {
            "S&P 500": round(0.25 + step * 0.08, 4),
            "NASDAQ-100": round(0.35 + step * 0.1, 4),
            "Equal Weight Placeholder": round(0.18 + step * 0.05, 4),
        }

    def _buy(self, ticker, price, recommendation, state, date):
        transaction_cost = 0
        slippage = 0
        budget = state["cash"] * self._position_size(recommendation)
        fill_price = round(price + slippage, 4)
        quantity = math.floor(max(0, budget - transaction_cost) / fill_price)

        if quantity <= 0:
            return None

        cost = round(quantity * fill_price + transaction_cost, 2)
        state["cash"] = round(state["cash"] - cost, 2)
        existing = state["positions"].get(ticker)

        if existing:
            total_quantity = existing["quantity"] + quantity
            total_cost = existing["quantity"] * existing["cost_basis"] + cost
            existing["quantity"] = total_quantity
            existing["cost_basis"] = round(total_cost / total_quantity, 4)
        else:
            state["positions"][ticker] = {
                "ticker": ticker,
                "quantity": quantity,
                "cost_basis": fill_price,
                "entry_date": date,
                "transaction_cost": transaction_cost,
                "slippage": slippage,
            }

        return {
            "trade_id": self._trade_id(ticker, "BUY", date, fill_price),
            "ticker": ticker,
            "action": "BUY",
            "entry_date": date,
            "entry_price": fill_price,
            "exit_date": None,
            "exit_price": None,
            "holding_period": None,
            "quantity": quantity,
            "profit_loss": 0,
            "transaction_cost": transaction_cost,
            "slippage": slippage,
            "reason": recommendation.get("reason", "Paper BUY simulation."),
            "recommendation_snapshot": recommendation,
        }

    def _sell(self, ticker, price, recommendation, state, date):
        position = state["positions"].get(ticker)
        transaction_cost = 0
        slippage = 0
        fill_price = round(price - slippage, 4)

        if not position:
            return None

        quantity = position["quantity"]
        proceeds = round(quantity * fill_price - transaction_cost, 2)
        basis = round(quantity * position["cost_basis"], 2)
        profit_loss = round(proceeds - basis, 2)
        state["cash"] = round(state["cash"] + proceeds, 2)
        state["realized_pl"] = round(state["realized_pl"] + profit_loss, 2)
        del state["positions"][ticker]

        return {
            "trade_id": self._trade_id(ticker, "SELL", date, fill_price),
            "ticker": ticker,
            "action": "SELL",
            "entry_date": position.get("entry_date"),
            "entry_price": position.get("cost_basis"),
            "exit_date": date,
            "exit_price": fill_price,
            "holding_period": self._holding_period(
                position.get("entry_date"),
                date,
            ),
            "quantity": quantity,
            "profit_loss": profit_loss,
            "transaction_cost": transaction_cost,
            "slippage": slippage,
            "reason": recommendation.get("reason", "Paper SELL simulation."),
            "recommendation_snapshot": recommendation,
        }

    def _portfolio_state(self, portfolio):
        source = portfolio or {}

        return {
            "cash": source.get("cash", self.INITIAL_CASH),
            "positions": json.loads(json.dumps(source.get("positions", {}))),
            "realized_pl": source.get("realized_pl", 0),
            "history": source.get("history", []),
        }

    def _position_size(self, recommendation):
        raw = (
            recommendation.get("suggested_allocation")
            or recommendation.get("allocation")
            or recommendation.get("target_weight")
        )
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return self.POSITION_SIZE

        if value > 1:
            value = value / 100

        return max(0, min(1, value))

    def _historical_rows(
        self,
        recommendations,
        historical_rows,
        tickers,
        start_date,
        end_date,
        historical_adapter,
    ):
        requested_tickers = sorted({
            item.get("ticker", "").upper()
            for item in recommendations
            if item.get("ticker")
        } | set(tickers or []))
        if historical_rows is not None:
            rows = [
                {**row, "ticker": row.get("ticker", "").upper()}
                for row in historical_rows
                if not requested_tickers or row.get("ticker", "").upper() in requested_tickers
            ]
            rows = self._validated_historical_rows(rows)
            return rows, {
                "data_source": "mocked_historical_prices",
                "fallback_used": False,
                "entry_price_date": rows[0]["date"],
                "last_price_date": rows[-1]["date"],
            }

        adapter = historical_adapter
        if adapter is None:
            from market.yahoo_historical_data_adapter import YahooHistoricalDataAdapter

            adapter = YahooHistoricalDataAdapter()

        rows = adapter.get_ohlcv(
            requested_tickers,
            start_date or "2024-01-01",
            end_date or "2024-02-15",
        )
        rows = self._validated_historical_rows(rows)
        fallback_used = bool(getattr(adapter, "fallback_used", False))

        return rows, {
            "data_source": "historical Yahoo data" if not fallback_used else "historical fallback data",
            "fallback_used": fallback_used,
            "entry_price_date": rows[0]["date"],
            "last_price_date": rows[-1]["date"],
        }

    def _validated_historical_rows(self, rows):
        clean = [
            row for row in rows
            if row.get("ticker") and row.get("date") and row.get("close") is not None
        ]
        if len(clean) < 2:
            raise ValueError("Historical price simulation requires at least two OHLCV rows.")

        return sorted(clean, key=lambda row: (row["date"], row["ticker"]))

    def _historical_rows_by_ticker(self, rows):
        grouped = {}
        for row in rows:
            grouped.setdefault(row["ticker"].upper(), []).append(row)

        return {
            ticker: sorted(ticker_rows, key=lambda row: row["date"])
            for ticker, ticker_rows in grouped.items()
            if len(ticker_rows) >= 2
        }

    def _historical_rows_by_date(self, rows):
        grouped = {}
        for row in rows:
            grouped.setdefault(row["date"], {})[row["ticker"].upper()] = row

        return grouped

    def _missing_price_dates(self, rows_by_date, tickers):
        missing = []
        for date, rows in rows_by_date.items():
            missing_tickers = [
                ticker for ticker in tickers
                if ticker not in rows
            ]
            if missing_tickers:
                missing.append({
                    "date": date,
                    "missing_tickers": missing_tickers,
                })

        return missing

    def _replay_recommendations(self, recommendations, date, active_tickers):
        replay = []
        for recommendation in recommendations:
            ticker = recommendation.get("ticker", "").upper()
            if not ticker:
                continue
            action = "HOLD" if ticker in active_tickers else recommendation.get("action", "BUY")
            replay.append({
                **recommendation,
                "ticker": ticker,
                "action": action,
                "replay_date": date,
                "status": "REPLAY_SNAPSHOT",
            })

        return replay

    def _replay_price_rows(
        self,
        recommendations,
        historical_rows,
        tickers,
        start_date,
        end_date,
        historical_adapter,
    ):
        """Return (rows, source, failure_reason) for historical replay.

        Never raises and never returns demo/mock fallback rows. If price rows
        are unavailable, or the adapter fell back, the caller must fail loudly.
        """
        try:
            rows, source = self._historical_rows(
                recommendations=recommendations,
                historical_rows=historical_rows,
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                historical_adapter=historical_adapter,
            )
        except ValueError:
            return [], {
                "data_source": "unavailable",
                "fallback_used": True,
                "entry_price_date": None,
                "last_price_date": None,
            }, "Historical prices unavailable"

        if source.get("fallback_used"):
            # Replay must never use demo/adapter fallback rows.
            return [], {
                **source,
                "data_source": "unavailable",
                "fallback_used": True,
            }, "Historical prices unavailable"

        if not rows:
            return [], source, "Historical prices unavailable"

        return rows, source, None

    def _replay_audit(
        self,
        replay_id,
        mode,
        requested_tickers,
        start_date,
        end_date,
        rows,
        source,
        price_backed,
        failure_reason,
        trades_generated,
        portfolio_points_generated,
    ):
        ordered = sorted(
            rows or [],
            key=lambda row: (row.get("date", ""), row.get("ticker", "")),
        )
        price_rows_used = [
            {
                "date": row.get("date"),
                "ticker": row.get("ticker"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("volume"),
            }
            for row in ordered[:5]
        ]

        return {
            "replay_id": replay_id,
            "mode": mode,
            "requested_tickers": requested_tickers,
            "start_date": start_date,
            "end_date": end_date,
            "price_source": source.get("data_source", "unavailable"),
            "fallback_used": bool(source.get("fallback_used", False)) or not price_backed,
            "price_backed": bool(price_backed),
            "rows_used_count": len(ordered),
            "first_price_date": ordered[0].get("date") if ordered else None,
            "last_price_date": ordered[-1].get("date") if ordered else None,
            "price_rows_used": price_rows_used,
            "trades_generated": trades_generated,
            "portfolio_points_generated": portfolio_points_generated,
            "failure_reason": failure_reason,
        }

    def _failed_replay_report(self, metadata, source, audit, failure_reason):
        metadata = {**metadata, "price_backed": False, "fallback_used": True}
        policy = self.policy() | metadata
        return {
            "portfolio": {
                "date": None,
                "cash": None,
                "positions": {},
                "current_value": None,
                "realized_pl": None,
                "unrealized_pl": None,
                "portfolio_value": None,
                "daily_return": None,
                "total_return": None,
                "price_backed": False,
                "status": "FAILED",
                "metadata": metadata,
            },
            "positions": {},
            "trades": [],
            "performance": {
                "price_backed": False,
                "paper_validation_source": False,
                "metadata": metadata,
                "replay_audit": audit,
            },
            "research": self.research_report([]),
            "metadata": metadata,
            "policy": policy,
            "price_source": source,
            "replay_history": [],
            "replay_status": "FAILED",
            "price_backed": False,
            "error": failure_reason or "Historical prices unavailable",
            "audit": audit,
            "missing_prices": source.get("missing_prices", []),
            "dates_tested": [],
        }

    def _trade_id(self, ticker, action, date, price):
        seed = f"{ticker}|{action}|{date}|{price}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]

        return f"paper-{digest}"

    def _holding_period(self, entry_date, exit_date):
        if not entry_date or not exit_date:
            return 0

        try:
            entry = datetime.fromisoformat(entry_date[:10])
            exit_ = datetime.fromisoformat(exit_date[:10])
            return max(0, (exit_ - entry).days)
        except ValueError:
            return 0

    def _ranked_trades(self, trades, reverse):
        return sorted(
            trades,
            key=lambda trade: (
                trade.get("profit_loss", 0),
                trade.get("ticker", ""),
            ),
            reverse=reverse,
        )

    def _sector_profitability(self, trades):
        totals = {}

        for trade in trades:
            sector = (
                trade.get("recommendation_snapshot", {}).get("sector")
                or "Unknown"
            )
            totals[sector] = round(
                totals.get(sector, 0) + trade.get("profit_loss", 0),
                2,
            )

        return [
            {"sector": sector, "profit_loss": value}
            for sector, value in sorted(
                totals.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    def _percentage(self, current, previous):
        if not previous:
            return 0

        return round((current - previous) / previous * 100, 4)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)

    def _sharpe(self, returns):
        volatility = self._standard_deviation(returns)

        if volatility == 0:
            return 0

        return round(self._average(returns) / volatility, 4)

    def _sortino(self, returns):
        downside = [value for value in returns if value < 0]
        downside_deviation = self._standard_deviation(downside)

        if downside_deviation == 0:
            return 0

        return round(self._average(returns) / downside_deviation, 4)

    def _max_drawdown(self, values):
        if not values:
            return 0

        peak = values[0]
        drawdowns = []

        for value in values:
            peak = max(peak, value)
            drawdowns.append(self._percentage(value, peak))

        return min(drawdowns)

    def _average(self, values):
        clean = [value for value in values if value is not None]

        if not clean:
            return 0

        return round(sum(clean) / len(clean), 4)

    def _standard_deviation(self, values):
        clean = [value for value in values if value is not None]

        if len(clean) < 2:
            return 0

        average = self._average(clean)
        variance = sum((value - average) ** 2 for value in clean) / len(clean)

        return round(math.sqrt(variance), 4)
