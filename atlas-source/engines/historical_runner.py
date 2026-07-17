import hashlib
import json
import math
from datetime import datetime

from engines.benchmark_engine import BenchmarkEngine
from engines.catalyst_engine import CatalystEngine
from engines.decision_engine import DecisionEngine
from engines.discovery_engine import DiscoveryEngine
from engines.market_regime_engine import MarketRegimeEngine
from engines.performance_observatory import PerformanceObservatory
from engines.probability_engine import ProbabilityEngine
from engines.validation_engine import ValidationEngine
from market.data import get_historical_data_adapter
from models.stock_analysis import StockAnalysis


class HistoricalRunner:
    DEFAULT_COMPARISON_VARIANTS = [
        "Full Atlas",
        "No Forecast",
        "No News",
        "No Fundamentals",
        "No Committee",
        "No Executive Review",
    ]
    DEFAULT_VARIANTS = [
        "Full Atlas",
        "No Forecast",
        "No News",
        "No Fundamentals",
        "No SEC",
        "No Macro",
        "No Catalysts",
        "No Committee",
        "No Executive Review",
        "No Probability",
        "Candidate Model Placeholder",
    ]
    DEFAULT_TOGGLES = {
        "use_technical": True,
        "use_fundamentals": True,
        "use_forecast": True,
        "use_news": True,
        "use_portfolio": True,
        "use_risk": True,
        "use_committee": True,
        "use_executive_review": True,
        "use_hypothesis": True,
        "use_discovery": True,
        "use_sec": True,
        "use_macro": True,
        "use_catalysts": True,
        "use_probability": True,
        "use_candidate_model": False,
    }
    VARIANT_TOGGLES = {
        "Full Atlas": {},
        "No Forecast": {"use_forecast": False},
        "No News": {"use_news": False},
        "No Fundamentals": {"use_fundamentals": False},
        "No Committee": {"use_committee": False},
        "No Executive Review": {"use_executive_review": False},
        "No SEC": {"use_sec": False},
        "No Macro": {"use_macro": False},
        "No Catalysts": {"use_catalysts": False},
        "No Probability": {"use_probability": False},
        "Candidate Model Placeholder": {"use_candidate_model": True},
    }
    MIN_SAMPLE_SIZE = 30

    def __init__(self, historical_data_adapter=None):
        self.decision_engine = DecisionEngine()
        self.validation_engine = ValidationEngine()
        self.benchmark_engine = BenchmarkEngine()
        self.observatory = PerformanceObservatory()
        self.discovery_engine = DiscoveryEngine()
        self.market_regime_engine = MarketRegimeEngine()
        self.catalyst_engine = CatalystEngine()
        self.probability_engine = ProbabilityEngine()
        self.historical_data_adapter = historical_data_adapter

    def create_experiment(self, config):
        normalized = {
            "tickers": sorted(config.get("tickers", [])),
            "start_date": config.get("start_date", ""),
            "end_date": config.get("end_date", ""),
            "forecast_provider": config.get("forecast_provider", "mock"),
            "news_provider": config.get("news_provider", "fake"),
            "fundamental_provider": config.get(
                "fundamental_provider",
                "mock",
            ),
            "historical_data_provider": config.get(
                "historical_data_provider",
                "mock",
            ),
            "committee_enabled": config.get("committee_enabled", True),
            "executive_review_enabled": config.get(
                "executive_review_enabled",
                True,
            ),
            "validation_window": config.get("validation_window", 30),
            "portfolio_configuration": config.get(
                "portfolio_configuration",
                {},
            ),
        }
        normalized.update({
            toggle: config.get(toggle, default)
            for toggle, default in self.DEFAULT_TOGGLES.items()
        })
        seed = json.dumps(normalized, sort_keys=True)
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]

        return {
            "experiment_id": f"hist-{digest}",
            "configuration": normalized,
        }

    def run(
        self,
        config,
        historical_data=None,
        persist=False,
        run_date=None,
    ):
        experiment = self.create_experiment(config)
        rows = self._load_replay_rows(historical_data, experiment["configuration"])
        rows = self._tag_market_regimes(rows)
        recommendations = []
        validations = []

        for index, row in enumerate(rows, start=1):
            recommendation = self._recommendation_from_row(
                row,
                experiment["configuration"],
            )
            recommendation.id = index
            validation = self._validate_row(
                recommendation,
                row,
                experiment["configuration"]["validation_window"],
            )
            recommendation.validation_result = validation
            recommendations.append(recommendation)
            validations.append(validation)

        self._attach_probability_reports(recommendations)

        metrics = self.performance_metrics(validations, recommendations)
        attribution = self.attribution_report(recommendations, validations)
        comparisons = self.compare_variants(
            experiment["configuration"],
            rows,
            self.DEFAULT_COMPARISON_VARIANTS,
        )
        statistics = self.statistical_analysis(validations)
        benchmark_rows = self.benchmark_engine.benchmark_recommendations(
            validations,
            engine_name="historical_validation",
            benchmark_date=run_date or datetime.now().isoformat(),
            notes="Historical validation framework.",
        )
        source_data = {
            "recommendations": [
                self._recommendation_record(item)
                for item in recommendations
            ],
            "benchmark_results": benchmark_rows,
            "provider_results": [],
            "research_experiments": [experiment],
        }
        observatory = self.observatory.generate(
            source_data=source_data,
            discovery_data={
                "recent_discoveries": [],
                "top_discoveries": [],
                "discovery_history": [],
            },
        )
        discoveries = self.discovery_engine.analyze(
            source_data=source_data,
            discovery_date=run_date or datetime.now().isoformat(),
        )
        report = {
            "experiment": experiment,
            "recommendations": [
                self._recommendation_record(item)
                for item in recommendations
            ],
            "validations": validations,
            "metrics": metrics,
            "attribution": attribution,
            "comparisons": comparisons,
            "statistics": statistics,
            "benchmark_rows": benchmark_rows,
            "observatory": observatory,
            "discoveries": discoveries,
        }
        report["markdown_report"] = self.generate_markdown_report(report)

        if persist:
            self.persist_report(report, run_date=run_date)

        return report

    def compare_variants(self, config, historical_data, variants=None):
        table = []
        historical_data = self._tag_market_regimes(historical_data)

        for variant in variants or self.DEFAULT_COMPARISON_VARIANTS:
            variant_config = self._variant_config(config, variant)
            variant_config["variant"] = variant
            validations = []
            recommendations = []

            for index, row in enumerate(historical_data, start=1):
                recommendation = self._recommendation_from_row(
                    row,
                    variant_config,
                )
                recommendation.id = index
                validation = self._validate_row(
                    recommendation,
                    row,
                    variant_config.get("validation_window", 30),
                )
                recommendation.validation_result = validation
                recommendations.append(recommendation)
                validations.append(validation)

            self._attach_probability_reports(recommendations)
            metrics = self.performance_metrics(validations, recommendations)
            statistics = self.statistical_analysis(validations)
            table.append({
                "variant": variant,
                "disabled_subsystems": self._disabled_subsystems(
                    variant_config,
                ),
                "recommendation_count": len(validations),
                "win_rate": metrics["win_rate"],
                "average_return": metrics["average_return"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "maximum_drawdown": metrics["maximum_drawdown"],
                "statistics": statistics,
            })

        return self._comparison_significance(table)

    def replay_configuration(self, config, historical_data=None):
        experiment = self.create_experiment(config)
        rows = self._load_replay_rows(
            historical_data,
            experiment["configuration"],
        )
        rows = self._tag_market_regimes(rows)
        recommendations = []
        validations = []

        for index, row in enumerate(rows, start=1):
            recommendation = self._recommendation_from_row(
                row,
                experiment["configuration"],
            )
            recommendation.id = index
            validation = self._validate_row(
                recommendation,
                row,
                experiment["configuration"]["validation_window"],
            )
            recommendation.validation_result = validation
            recommendations.append(recommendation)
            validations.append(validation)

        if experiment["configuration"].get("use_probability", True):
            self._attach_probability_reports(recommendations)

        return {
            "experiment": experiment,
            "recommendations": [
                self._recommendation_record(item)
                for item in recommendations
            ],
            "validations": validations,
            "metrics": self.performance_metrics(validations, recommendations),
            "market_regimes_tested": sorted({
                row.get("market_regime", "Sideways")
                for row in rows
            }),
            "disabled_subsystems": self._disabled_subsystems(
                experiment["configuration"],
            ),
        }

    def performance_metrics(self, validations, recommendations=None):
        completed = [
            item for item in validations
            if item.get("status") in {"Succeeded", "Failed"}
        ]
        returns = [
            item.get("percentage_return")
            for item in completed
            if item.get("percentage_return") is not None
        ]
        wins = [item for item in completed if item.get("success") is True]
        losses = [item for item in completed if item.get("success") is False]
        gains = [item for item in returns if item > 0]
        drawdowns = self._drawdowns(returns)
        holding_periods = [
            item.get("holding_period")
            for item in completed
            if item.get("holding_period") is not None
        ]

        return {
            "win_rate": self._rate(len(wins), len(completed)),
            "loss_rate": self._rate(len(losses), len(completed)),
            "average_return": self._average(returns),
            "median_return": self._median(returns),
            "average_holding_period": self._average(holding_periods),
            "sharpe_ratio": self._sharpe_ratio(returns),
            "sortino_ratio": self._sortino_ratio(returns),
            "maximum_drawdown": min(drawdowns) if drawdowns else 0,
            "volatility": self._standard_deviation(returns),
            "information_ratio": None,
            "profit_factor": self._profit_factor(returns),
            "expectancy": self._average(returns),
            "risk_reward_ratio": self._risk_reward_ratio(returns),
            "recommendation_accuracy": self._rate(
                len(wins),
                len(completed),
            ),
            "confidence_calibration": self._confidence_calibration(
                completed,
                recommendations or [],
            ),
            "committee_accuracy": self._layer_accuracy(
                recommendations or [],
                "committee_agreement",
            ),
            "executive_accuracy": self._executive_accuracy(
                recommendations or [],
            ),
            "hypothesis_accuracy": self._binary_layer_accuracy(
                recommendations or [],
                "assumptions",
            ),
            "discovery_accuracy": self._binary_layer_accuracy(
                recommendations or [],
                "discoveries",
            ),
        }

    def attribution_report(self, recommendations, validations):
        layers = [
            "Technical",
            "Fundamental",
            "Forecast",
            "News",
            "Portfolio",
            "Risk",
            "Committee",
            "Executive",
            "Discovery",
            "Hypothesis",
        ]

        return [
            {
                "layer": layer,
                "contribution_score": self._layer_contribution(
                    layer,
                    recommendations,
                ),
                "sample_size": len(validations),
                "notes": "Contribution is deterministic from available historical layer scores.",
            }
            for layer in layers
        ]

    def statistical_analysis(self, validations, comparison_delta=0):
        returns = [
            item.get("percentage_return")
            for item in validations
            if item.get("percentage_return") is not None
        ]
        wins = [
            item for item in validations
            if item.get("success") is True
        ]
        sample_size = len(returns)
        mean = self._average(returns)
        standard_deviation = self._standard_deviation(returns)
        standard_error = self._standard_error(standard_deviation, sample_size)
        margin = 1.96 * standard_error if sample_size else 0
        win_rate = self._rate(len(wins), sample_size)
        win_rate_interval = self._win_rate_interval(len(wins), sample_size)

        return {
            "sample_size": sample_size,
            "mean_return": mean,
            "variance": self._variance(returns),
            "standard_deviation": standard_deviation,
            "standard_error": standard_error,
            "confidence_interval_95": [
                round(mean - margin, 2),
                round(mean + margin, 2),
            ],
            "win_rate": win_rate,
            "win_rate_confidence_interval_95": win_rate_interval,
            "comparison_delta": round(comparison_delta, 4),
            "practical_significance_label": self._practical_significance_label(
                sample_size,
                comparison_delta,
                margin,
            ),
            "insufficient_sample_size": sample_size < self.MIN_SAMPLE_SIZE,
        }

    def generate_markdown_report(self, report):
        metrics = report["metrics"]
        config = report["experiment"]["configuration"]

        lines = [
            "# Atlas Historical Validation Report",
            "",
            "## Executive Summary",
            (
                f"{report['experiment']['experiment_id']} replayed "
                f"{len(report['validations'])} recommendations with "
                f"{metrics['win_rate']}% win rate and "
                f"{metrics['average_return']}% average return."
            ),
            "",
            "## Configuration",
            f"- Tickers: {', '.join(config['tickers'])}",
            f"- Date Range: {config['start_date']} to {config['end_date']}",
            f"- Validation Window: {config['validation_window']}",
            f"- Forecast Provider: {config['forecast_provider']}",
            f"- News Provider: {config['news_provider']}",
            f"- Fundamental Provider: {config['fundamental_provider']}",
            "",
            "## Performance",
            f"- Win Rate: {metrics['win_rate']}%",
            f"- Loss Rate: {metrics['loss_rate']}%",
            f"- Average Return: {metrics['average_return']}%",
            f"- Median Return: {metrics['median_return']}%",
            f"- Recommendation Accuracy: {metrics['recommendation_accuracy']}%",
            "",
            "## Risk",
            f"- Sharpe Ratio: {metrics['sharpe_ratio']}",
            f"- Sortino Ratio: {metrics['sortino_ratio']}",
            f"- Maximum Drawdown: {metrics['maximum_drawdown']}%",
            f"- Volatility: {metrics['volatility']}",
            f"- Profit Factor: {metrics['profit_factor']}",
            f"- Expectancy: {metrics['expectancy']}%",
            f"- Risk/Reward Ratio: {metrics['risk_reward_ratio']}",
            "",
            "## Statistical Significance",
            f"- Sample Size: {report['statistics']['sample_size']}",
            f"- Mean Return: {report['statistics']['mean_return']}%",
            f"- Standard Error: {report['statistics']['standard_error']}",
            (
                "- 95% Confidence Interval: "
                f"{report['statistics']['confidence_interval_95']}"
            ),
            (
                "- Win Rate 95% Confidence Interval: "
                f"{report['statistics']['win_rate_confidence_interval_95']}"
            ),
            (
                "- Practical Significance: "
                f"{report['statistics']['practical_significance_label']}"
            ),
            "",
            "## Committee",
            f"- Committee Accuracy: {metrics['committee_accuracy']}%",
            "",
            "## Executive Review",
            f"- Executive Accuracy: {metrics['executive_accuracy']}%",
            "",
            "## Hypothesis Review",
            f"- Hypothesis Accuracy: {metrics['hypothesis_accuracy']}%",
            "",
            "## Discovery Review",
            f"- Discovery Accuracy: {metrics['discovery_accuracy']}%",
            "",
            "## Strengths",
        ]
        lines.extend([
            f"- {item['layer']} contribution: {item['contribution_score']}"
            for item in report["attribution"]
            if item["contribution_score"] >= 60
        ] or ["- No high-contribution layer identified."])
        lines.extend(["", "## Weaknesses"])
        lines.extend([
            f"- {item['layer']} contribution: {item['contribution_score']}"
            for item in report["attribution"]
            if item["contribution_score"] < 50
        ] or ["- No low-contribution layer identified."])
        lines.extend([
            "",
            "## Future Improvements",
            "- Add larger historical datasets.",
            "- Add benchmark distributions for statistical significance.",
            "- Compare provider variants over identical replay windows.",
        ])

        return "\n".join(lines)

    def persist_report(self, report, run_date=None):
        from database.repository import save_historical_validation_run

        save_historical_validation_run({
            "experiment_id": report["experiment"]["experiment_id"],
            "run_date": run_date or datetime.now().isoformat(),
            "configuration": report["experiment"]["configuration"],
            "metrics": report["metrics"],
            "comparison": report["comparisons"],
            "statistics": report["statistics"],
            "report": report["markdown_report"],
        })

    def _filtered_rows(self, rows, config):
        tickers = set(config.get("tickers", []))
        start = config.get("start_date", "")
        end = config.get("end_date", "")

        return [
            row for row in rows
            if (not tickers or row.get("ticker") in tickers)
            and (not start or row.get("date", "") >= start)
            and (not end or row.get("date", "") <= end)
        ]

    def _load_replay_rows(self, historical_data, config):
        if historical_data is not None:
            rows = self._filtered_rows(historical_data, config)
            self._validate_replay_rows(rows, config)

            return rows

        adapter = self.historical_data_adapter or get_historical_data_adapter(
            config.get("historical_data_provider")
        )
        ohlcv_rows = adapter.get_ohlcv(
            config.get("tickers", []),
            config.get("start_date"),
            config.get("end_date"),
        )
        self._validate_ohlcv_rows(ohlcv_rows, config)

        return self._replay_rows_from_ohlcv(
            ohlcv_rows,
            config.get("validation_window", 30),
        )

    def _tag_market_regimes(self, rows):
        tagged = []

        for row in rows:
            regime = self.market_regime_engine.classify_row(row)
            tagged.append({
                **row,
                "market_regime": regime["regime"],
                "market_regime_details": regime,
            })

        return tagged

    def _validate_replay_rows(self, rows, config):
        self._validate_date_range(config)

        if not config.get("tickers"):
            raise ValueError("At least one ticker is required.")

        if not rows:
            raise ValueError("No historical rows available for replay.")

        self._validate_sorted(rows)

    def _validate_ohlcv_rows(self, rows, config):
        self._validate_date_range(config)

        if not config.get("tickers"):
            raise ValueError("At least one ticker is required.")

        if not rows:
            raise ValueError("No OHLCV rows returned by historical adapter.")

        self._validate_sorted(rows)
        required = {"date", "ticker", "open", "high", "low", "close", "volume"}
        missing = [
            sorted(required - set(row.keys()))
            for row in rows
            if required - set(row.keys())
        ]

        if missing:
            raise ValueError("Historical OHLCV rows are missing required fields.")

        tickers = set(config.get("tickers", []))
        returned_tickers = {row["ticker"] for row in rows}
        missing_tickers = tickers - returned_tickers

        if missing_tickers:
            raise ValueError(
                "Historical adapter returned no rows for ticker(s): "
                f"{', '.join(sorted(missing_tickers))}."
            )

        validation_window = config.get("validation_window", 30)
        for ticker in tickers:
            ticker_rows = [
                row for row in rows
                if row["ticker"] == ticker
            ]

            if len(ticker_rows) <= validation_window:
                raise ValueError(
                    f"Insufficient historical rows for {ticker}: "
                    f"need more than validation window {validation_window}, "
                    f"got {len(ticker_rows)}."
                )

    def _validate_date_range(self, config):
        start = config.get("start_date")
        end = config.get("end_date")

        if not start or not end:
            raise ValueError("Historical start_date and end_date are required.")

        if start > end:
            raise ValueError("Historical start_date must be on or before end_date.")

    def _validate_sorted(self, rows):
        keys = [(row.get("date", ""), row.get("ticker", "")) for row in rows]

        if keys != sorted(keys):
            raise ValueError("Historical rows must be sorted by date and ticker.")

    def _replay_rows_from_ohlcv(self, rows, validation_window):
        grouped = {}

        for row in rows:
            grouped.setdefault(row["ticker"], []).append(row)

        replay_rows = []
        for ticker in sorted(grouped):
            ticker_rows = sorted(grouped[ticker], key=lambda row: row["date"])
            closes = [row["close"] for row in ticker_rows]

            for index, row in enumerate(ticker_rows[:-validation_window]):
                future = ticker_rows[index + validation_window]
                replay_rows.append(
                    self._feature_row(row, future, ticker_rows, closes, index)
                )

        return sorted(
            replay_rows,
            key=lambda row: (row["date"], row["ticker"]),
        )

    def _feature_row(self, row, future, ticker_rows, closes, index):
        current_close = row["close"]
        start_20 = max(0, index - 19)
        start_50 = max(0, index - 49)
        ma20 = self._average(closes[start_20:index + 1])
        ma50 = self._average(closes[start_50:index + 1])
        week_start = closes[max(0, index - 5)]
        month_start = closes[max(0, index - 21)]
        previous_close = closes[index - 1] if index > 0 else current_close
        price_change = current_close - previous_close
        macd = round(current_close - ma20, 4)
        macd_signal = round(ma20 - ma50, 4)

        return {
            "date": row["date"],
            "validation_date": future["date"],
            "ticker": row["ticker"],
            "asset_type": "Stock",
            "price": current_close,
            "future_price": future["close"],
            "week_return": self._percentage(current_close, week_start),
            "month_return": self._percentage(current_close, month_start),
            "moving_average_20": ma20,
            "moving_average_50": ma50,
            "price_vs_20ma": self._percentage(current_close, ma20),
            "price_vs_50ma": self._percentage(current_close, ma50),
            "rsi": self._rsi(ticker_rows, index),
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_trend": "Bullish" if macd >= macd_signal else "Bearish",
            "volatility": self._volatility(closes[max(0, index - 9):index + 1]),
            "trend": "Bullish" if price_change >= 0 else "Bearish",
            "score": self._score(current_close, ma20, ma50, price_change),
        }

    def _percentage(self, current, previous):
        if previous == 0:
            return 0

        return round((current - previous) / previous * 100, 4)

    def _rsi(self, rows, index):
        if index == 0:
            return 50

        window = rows[max(1, index - 13):index + 1]
        gains = []
        losses = []

        for offset, row in enumerate(window, start=max(1, index - 13)):
            change = row["close"] - rows[offset - 1]["close"]
            if change >= 0:
                gains.append(change)
            else:
                losses.append(abs(change))

        average_gain = self._average(gains)
        average_loss = self._average(losses)

        if average_loss == 0:
            return 100 if average_gain > 0 else 50

        relative_strength = average_gain / average_loss

        return round(100 - (100 / (1 + relative_strength)), 2)

    def _volatility(self, closes):
        returns = [
            self._percentage(closes[index], closes[index - 1])
            for index in range(1, len(closes))
        ]

        return self._standard_deviation(returns)

    def _score(self, close, ma20, ma50, price_change):
        score = 2

        if close >= ma20:
            score += 1

        if close >= ma50:
            score += 1

        if price_change > 0:
            score += 1

        return max(1, min(5, score))

    def _recommendation_from_row(self, row, config=None):
        config = config or self.DEFAULT_TOGGLES
        recommendation = self.decision_engine.decide(StockAnalysis(
            ticker=row["ticker"],
            asset_type=row.get("asset_type", "Stock"),
            price=row["price"],
            week_return=row.get("week_return", 0),
            month_return=row.get("month_return", 0),
            moving_average_20=row.get("moving_average_20", row["price"]),
            moving_average_50=row.get("moving_average_50", row["price"]),
            price_vs_20ma=row.get("price_vs_20ma", 0),
            price_vs_50ma=row.get("price_vs_50ma", 0),
            rsi=row.get("rsi", 50),
            macd=row.get("macd", 0),
            macd_signal=row.get("macd_signal", 0),
            macd_trend=row.get("macd_trend", "Neutral"),
            volatility=row.get("volatility", 1),
            trend=row.get("trend", "Neutral"),
            score=row.get("score", 0),
        ))
        self._apply_experiment_toggles(recommendation, row, config)
        recommendation.market_regime = row.get("market_regime", "Sideways")
        recommendation.market_regime_details = row.get(
            "market_regime_details",
            {},
        )
        recommendation.catalysts = row.get(
            "catalysts",
            (
                self.catalyst_engine.recommendation_context(
                    row["ticker"],
                    as_of_date=row.get("date"),
                )
                if config.get("use_catalysts", True)
                else []
            ),
        )

        return recommendation

    def _variant_config(self, config, variant):
        variant_config = dict(config)
        variant_config.update(self.VARIANT_TOGGLES.get(variant, {}))

        return variant_config

    def _disabled_subsystems(self, config):
        return [
            toggle.replace("use_", "")
            for toggle, enabled in self._toggles(config).items()
            if not enabled and toggle != "use_candidate_model"
        ]

    def _toggles(self, config):
        return {
            toggle: config.get(toggle, default)
            for toggle, default in self.DEFAULT_TOGGLES.items()
        }

    def _apply_experiment_toggles(self, recommendation, row, config):
        toggles = self._toggles(config)
        scores = {
            "Technical": row.get("score", 0) * 20,
            "Fundamental": row.get("fundamental_score", 60),
            "Forecast": row.get("forecast_score", self._forecast_score(row)),
            "News": row.get("news_confidence", 50),
            "Portfolio": row.get("portfolio_score", 60),
            "Risk": row.get("risk_score", max(0, 100 - row.get("volatility", 0) * 10)),
            "Committee": row.get("committee_agreement", 70),
            "Executive": row.get("executive_confidence", 70),
            "Discovery": row.get("discovery_score", 50),
            "Hypothesis": row.get("hypothesis_score", 50),
        }
        toggle_map = {
            "Technical": "use_technical",
            "Fundamental": "use_fundamentals",
            "Forecast": "use_forecast",
            "News": "use_news",
            "Portfolio": "use_portfolio",
            "Risk": "use_risk",
            "Committee": "use_committee",
            "Executive": "use_executive_review",
            "Discovery": "use_discovery",
            "Hypothesis": "use_hypothesis",
        }

        recommendation.technical_score = self._enabled_score(
            "Technical",
            scores,
            toggle_map,
            toggles,
        )
        recommendation.fundamental_score = self._enabled_score(
            "Fundamental",
            scores,
            toggle_map,
            toggles,
        )
        recommendation.forecast_score = self._enabled_score(
            "Forecast",
            scores,
            toggle_map,
            toggles,
        )
        recommendation.news_confidence = self._enabled_score(
            "News",
            scores,
            toggle_map,
            toggles,
        )
        recommendation.portfolio_score = self._enabled_score(
            "Portfolio",
            scores,
            toggle_map,
            toggles,
        )
        recommendation.risk_score = self._enabled_score(
            "Risk",
            scores,
            toggle_map,
            toggles,
        )
        recommendation.committee_agreement = self._enabled_score(
            "Committee",
            scores,
            toggle_map,
            toggles,
        )
        recommendation.executive_confidence = self._enabled_score(
            "Executive",
            scores,
            toggle_map,
            toggles,
        )
        recommendation.executive_status = (
            "READY" if toggles["use_executive_review"] else "DISABLED"
        )
        recommendation.assumptions = (
            ["Historical hypothesis review enabled."]
            if toggles["use_hypothesis"]
            else []
        )
        recommendation.discoveries = (
            ["Historical discovery review enabled."]
            if toggles["use_discovery"]
            else []
        )
        recommendation.disabled_subsystems = self._disabled_subsystems(config)
        recommendation.evidence_breakdown = [
            self._evidence_item(name, scores[name], toggles[toggle])
            for name, toggle in toggle_map.items()
        ]

    def _enabled_score(self, name, scores, toggle_map, toggles):
        if not toggles[toggle_map[name]]:
            return 0

        return scores[name]

    def _evidence_item(self, name, score, enabled):
        if enabled:
            return {
                "category": name,
                "name": name,
                "score": score,
                "confidence": score,
                "weight": 0.1,
                "enabled": True,
                "disabled": False,
                "summary": f"{name} enabled for historical experiment.",
            }

        return {
            "category": name,
            "name": name,
            "score": 0,
            "confidence": 0,
            "weight": 0,
            "enabled": False,
            "disabled": True,
            "summary": f"{name} disabled by historical experiment toggle.",
        }

    def _forecast_score(self, row):
        return 70 if row.get("future_price", row["price"]) >= row["price"] else 35

    def _validate_row(self, recommendation, row, validation_window):
        return self.validation_engine.evaluate_completed_recommendation(
            recommendation=recommendation,
            starting_price=row["price"],
            ending_price=row.get("future_price", row["price"]),
            holding_period=validation_window,
            recommendation_timestamp=row.get("date", ""),
            evaluation_timestamp=row.get("validation_date", row.get("date", "")),
            notes="Historical replay validation.",
        )

    def _attach_probability_reports(self, recommendations):
        history = [
            self._recommendation_record(item)
            for item in recommendations
            if getattr(item, "validation_result", None) is not None
        ]

        for recommendation in recommendations:
            recommendation.probability_report = self.probability_engine.estimate(
                recommendation,
                history=history,
            )

    def _recommendation_record(self, recommendation):
        validation = getattr(recommendation, "validation_result", None)

        return {
            "ticker": recommendation.ticker,
            "action": recommendation.action,
            "confidence": recommendation.confidence,
            "committee_agreement": getattr(
                recommendation,
                "committee_agreement",
                0,
            ),
            "executive_status": getattr(recommendation, "executive_status", ""),
            "executive_warnings": getattr(
                recommendation,
                "executive_warnings",
                [],
            ),
            "disabled_subsystems": getattr(
                recommendation,
                "disabled_subsystems",
                [],
            ),
            "evidence_breakdown": getattr(
                recommendation,
                "evidence_breakdown",
                [],
            ),
            "validation_result": validation,
            "market_regime": getattr(recommendation, "market_regime", "Sideways"),
            "market_regime_details": getattr(
                recommendation,
                "market_regime_details",
                {},
            ),
            "knowledge_score": getattr(recommendation, "knowledge_score", 0),
            "stability_score": getattr(recommendation, "stability_score", 0),
            "catalysts": getattr(recommendation, "catalysts", []),
            "probability_report": getattr(
                recommendation,
                "probability_report",
                {},
            ),
        }

    def _comparison_significance(self, rows):
        if not rows:
            return []

        baseline = next(
            (row for row in rows if row["variant"] == "Full Atlas"),
            rows[0],
        )
        baseline_return = baseline["average_return"]
        baseline_win_rate = baseline["win_rate"]

        for row in rows:
            return_delta = round(row["average_return"] - baseline_return, 4)
            win_rate_delta = round(row["win_rate"] - baseline_win_rate, 4)
            row["comparison_delta"] = return_delta
            row["win_rate_delta"] = win_rate_delta
            row["practical_significance_label"] = (
                self._practical_significance_label(
                    row["statistics"]["sample_size"],
                    return_delta,
                    self._ci_margin(row["statistics"]),
                )
            )
            row["statistics"] = self.statistical_analysis(
                [
                    {
                        "percentage_return": row["average_return"],
                        "success": row["win_rate"] >= 50,
                    }
                ],
                comparison_delta=return_delta,
            ) | {
                "sample_size": row["statistics"]["sample_size"],
                "mean_return": row["statistics"]["mean_return"],
                "variance": row["statistics"]["variance"],
                "standard_deviation": row["statistics"]["standard_deviation"],
                "standard_error": row["statistics"]["standard_error"],
                "confidence_interval_95": (
                    row["statistics"]["confidence_interval_95"]
                ),
                "win_rate": row["statistics"]["win_rate"],
                "win_rate_confidence_interval_95": (
                    row["statistics"]["win_rate_confidence_interval_95"]
                ),
                "insufficient_sample_size": (
                    row["statistics"]["insufficient_sample_size"]
                ),
                "practical_significance_label": (
                    row["practical_significance_label"]
                ),
            }

        return rows

    def _ci_margin(self, statistics):
        interval = statistics.get("confidence_interval_95", [0, 0])

        if len(interval) != 2:
            return 0

        return abs(interval[1] - interval[0]) / 2

    def _layer_contribution(self, layer, recommendations):
        if layer == "Committee":
            return self._average([
                getattr(item, "committee_agreement", 0)
                for item in recommendations
            ])

        if layer == "Executive":
            return self._average([
                getattr(item, "executive_confidence", 0)
                for item in recommendations
            ])

        score_map = {
            "Technical": "score",
            "Fundamental": "fundamental_score",
            "Forecast": "forecast_score",
            "News": "news_confidence",
            "Portfolio": "portfolio_score",
            "Risk": "risk_score",
        }
        attribute = score_map.get(layer)

        if attribute is None:
            return 0

        return self._average([
            getattr(item, attribute, 0)
            for item in recommendations
        ])

    def _layer_accuracy(self, recommendations, attribute):
        rows = [
            item for item in recommendations
            if getattr(item, "validation_result", None) is not None
        ]

        if not rows:
            return 0

        aligned = [
            item for item in rows
            if (
                getattr(item, attribute, 0) >= 60
                and item.validation_result.get("success") is True
            )
            or (
                getattr(item, attribute, 0) < 60
                and item.validation_result.get("success") is False
            )
        ]

        return self._rate(len(aligned), len(rows))

    def _executive_accuracy(self, recommendations):
        rows = [
            item for item in recommendations
            if getattr(item, "validation_result", None) is not None
            and getattr(item, "executive_status", "")
        ]

        if not rows:
            return 0

        aligned = [
            item for item in rows
            if (
                item.executive_status in {"READY", "CAUTION"}
                and item.validation_result.get("success") is True
            )
            or (
                item.executive_status in {"NEEDS_REVIEW", "INSUFFICIENT_DATA"}
                and item.validation_result.get("success") is False
            )
        ]

        return self._rate(len(aligned), len(rows))

    def _binary_layer_accuracy(self, recommendations, attribute):
        rows = [
            item for item in recommendations
            if getattr(item, "validation_result", None) is not None
            and getattr(item, attribute, None)
        ]

        return self._rate(
            len([
                item for item in rows
                if item.validation_result.get("success") is True
            ]),
            len(rows),
        )

    def _confidence_calibration(self, validations, recommendations):
        if not validations or not recommendations:
            return 0

        errors = []
        for validation, recommendation in zip(validations, recommendations):
            actual = 100 if validation.get("success") else 0
            errors.append(abs(recommendation.confidence - actual))

        return round(max(0, 100 - self._average(errors)), 2)

    def _sharpe_ratio(self, returns):
        volatility = self._standard_deviation(returns)

        if volatility == 0:
            return 0

        return round(self._average(returns) / volatility, 4)

    def _sortino_ratio(self, returns):
        downside = [item for item in returns if item < 0]
        downside_deviation = self._standard_deviation(downside)

        if downside_deviation == 0:
            return 0

        return round(self._average(returns) / downside_deviation, 4)

    def _drawdowns(self, returns):
        equity = 100
        peak = 100
        drawdowns = []

        for value in returns:
            equity *= 1 + (value / 100)
            peak = max(peak, equity)
            drawdowns.append(round((equity - peak) / peak * 100, 2))

        return drawdowns

    def _profit_factor(self, returns):
        gains = sum([item for item in returns if item > 0])
        losses = abs(sum([item for item in returns if item < 0]))

        if losses == 0:
            return None if gains == 0 else round(gains, 2)

        return round(gains / losses, 4)

    def _risk_reward_ratio(self, returns):
        gains = [item for item in returns if item > 0]
        losses = [abs(item) for item in returns if item < 0]

        if not losses:
            return None

        return round(self._average(gains) / self._average(losses), 4)

    def _variance(self, values):
        if not values:
            return 0

        average = self._average(values)

        return round(
            sum([(value - average) ** 2 for value in values]) / len(values),
            4,
        )

    def _standard_deviation(self, values):
        return round(math.sqrt(self._variance(values)), 4)

    def _standard_error(self, standard_deviation, sample_size):
        if sample_size == 0:
            return 0

        return round(standard_deviation / math.sqrt(sample_size), 4)

    def _win_rate_interval(self, wins, sample_size):
        if sample_size == 0:
            return [0, 0]

        proportion = wins / sample_size
        margin = 1.96 * math.sqrt(
            proportion * (1 - proportion) / sample_size
        )

        return [
            round(max(0, (proportion - margin) * 100), 2),
            round(min(100, (proportion + margin) * 100), 2),
        ]

    def _practical_significance_label(self, sample_size, delta, ci_margin):
        absolute_delta = abs(delta)

        if sample_size < self.MIN_SAMPLE_SIZE:
            return "Insufficient Sample"

        if absolute_delta < 1:
            return "Not Meaningful"

        if absolute_delta >= max(3, ci_margin):
            return "Meaningful"

        return "Possibly Meaningful"

    def _average(self, values):
        cleaned = [value for value in values if value is not None]

        if not cleaned:
            return 0

        return round(sum(cleaned) / len(cleaned), 4)

    def _median(self, values):
        cleaned = sorted([value for value in values if value is not None])

        if not cleaned:
            return 0

        midpoint = len(cleaned) // 2
        if len(cleaned) % 2 == 1:
            return cleaned[midpoint]

        return round((cleaned[midpoint - 1] + cleaned[midpoint]) / 2, 4)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)
