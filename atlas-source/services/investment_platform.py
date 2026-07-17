from database.setup import setup_database
from database.repository import (
    save_dashboard_run,
    save_portfolio_snapshot,
    save_recommendations,
)
from engines.market_engine import MarketEngine
from engines.markdown_report_engine import MarkdownReportEngine
from engines.recommendation_engine import RecommendationEngine
from engines.dashboard_engine import DashboardEngine
from engines.logging_engine import LoggingEngine
from engines.portfolio_engine import PortfolioEngine
from engines.risk_engine import RiskEngine


class IntelligencePipeline:
    execution_order = [
        "Fetch market data",
        "Technical analysis",
        "Fundamental analysis",
        "News analysis",
        "Forecast provider",
        "Portfolio analysis",
        "Risk analysis",
        "Evidence Engine",
        "Confidence Engine",
        "Signal Quality",
        "Recommendation Engine",
        "Validation",
        "Benchmark logging",
        "Persist results",
        "Return final recommendation",
    ]

    def __init__(self):
        self.logger = LoggingEngine()
        self.market_engine = MarketEngine()
        self.recommendation_engine = RecommendationEngine()
        self.dashboard_engine = DashboardEngine()
        self.markdown_report_engine = MarkdownReportEngine()

    def execute(self, tickers):
        self.logger.info("Atlas IntelligencePipeline started.")
        setup_database()

        portfolio, risk_engine = self._portfolio_context()
        stocks = self._market_and_technical_analysis(tickers)
        recommendations = self._intelligence_recommendations(stocks)

        dashboard = self.dashboard_engine.build_dashboard(
            stocks=stocks,
            recommendations=recommendations
        )

        run_id = self._persist_results(dashboard, recommendations, portfolio, risk_engine)
        self._export_report(run_id)
        self._return_final_recommendation(recommendations)

        dashboard.display()

        self.logger.info("Atlas IntelligencePipeline complete.")

        return dashboard

    def _portfolio_context(self):
        self._log_stage("Portfolio analysis")
        self._log_stage("Risk analysis")

        portfolio = PortfolioEngine()
        risk_engine = RiskEngine()

        portfolio.set_cash(1000)
        portfolio.add_position("VOO", 2, 500)
        portfolio.add_position("AAPL", 3, 200)

        return portfolio, risk_engine

    def _market_and_technical_analysis(self, tickers):
        self._log_stage("Fetch market data")
        self._log_stage("Technical analysis")

        stocks = self.market_engine.analyze_market(tickers)

        self.logger.info("Market data and technical analysis complete.")

        return stocks

    def _intelligence_recommendations(self, stocks):
        for stage in [
            "Fundamental analysis",
            "News analysis",
            "Forecast provider",
            "Evidence Engine",
            "Confidence Engine",
            "Signal Quality",
            "Recommendation Engine",
        ]:
            self._log_stage(stage)

        recommendations = self.recommendation_engine.build_recommendations(stocks)

        self._log_stage("Validation")
        self.logger.info("Validation status initialized on recommendations.")

        self._log_stage("Benchmark logging")
        self.logger.info("Benchmark logging available for completed validations.")
        self.logger.info("Recommendations created.")

        return recommendations

    def _persist_results(self, dashboard, recommendations, portfolio, risk_engine):
        self._log_stage("Persist results")

        run_id = save_dashboard_run(dashboard)
        self.logger.info("Dashboard run saved to database.")

        save_recommendations(run_id, recommendations)
        self.logger.info("Recommendations saved to database.")

        save_portfolio_snapshot(
            run_id,
            portfolio,
            risk_engine
        )
        self.logger.info("Portfolio snapshot saved to database.")

        return run_id

    def _export_report(self, run_id):
        report_path = self.markdown_report_engine.export_report_for_run(run_id)
        self.logger.info(f"Markdown report saved to {report_path}.")
        self.logger.info("Dashboard built.")

    def _return_final_recommendation(self, recommendations):
        self._log_stage("Return final recommendation")

        if not recommendations:
            self.logger.info("No final recommendation available.")
            return None

        final_recommendation = recommendations[0]
        self.logger.info(
            "Final recommendation: "
            f"{final_recommendation.ticker} {final_recommendation.action}"
        )

        return final_recommendation

    def _log_stage(self, stage):
        self.logger.info(f"Pipeline stage: {stage}.")


class InvestmentPlatform:

    def __init__(self):
        self.pipeline = IntelligencePipeline()

    def run(self, tickers):
        return self.pipeline.execute(tickers)
