from pathlib import Path

from engines.history_engine import HistoryEngine


class MarkdownReportEngine:

    def __init__(self):
        self.history = HistoryEngine()

    def export_latest_report(self):
        runs = self.history.recent_runs(limit=1)

        if not runs:
            raise ValueError("No saved Atlas runs found.")

        run = runs[0]
        return self.export_report_for_run(run["id"])

    def export_report_for_run(self, run_id):
        run = self._get_run(run_id)
        recommendations = self.history.recommendations_for_run(run_id)
        snapshot = self.history.portfolio_snapshot(run_id)

        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        report_path = reports_dir / f"atlas_report_{run_id}.md"
        report_path.write_text(
            self._build_markdown(run, recommendations, snapshot),
            encoding="utf-8"
        )

        return report_path

    def institutional_markdown(self, report):
        return report.get("markdown", "")

    def _get_run(self, run_id):
        runs = self.history.recent_runs(limit=100)

        for run in runs:
            if run["id"] == run_id:
                return run

        raise ValueError(f"No saved Atlas run found for run id {run_id}.")

    def _build_markdown(self, run, recommendations, snapshot):
        run_id = run["id"]
        lines = [
            "# Atlas Report",
            "",
            f"Run ID: {run['id']}",
            f"Run Time: {run['run_time']}",
            f"Market Status: {run['market_status']}",
            f"Average RSI: {run['average_rsi']:.1f}",
            f"Average Volatility: {run['average_volatility']:.2f}%",
            "",
            "## Recommendations",
            "",
        ]

        if not recommendations:
            lines.append("No recommendations saved for this run.")

        else:
            for recommendation in recommendations:
                lines.extend([
                    f"### {recommendation['ticker']}",
                    "",
                    f"- Action: {recommendation['action']}",
                    f"- Confidence: {recommendation['confidence']}%",
                    f"- Score: {recommendation['score']}",
                    f"- Technical Score: {recommendation['technical_score']}",
                    f"- Fundamental Score: {recommendation['fundamental_score']}",
                    f"- Portfolio Score: {recommendation['portfolio_score']}",
                    f"- Risk Score: {recommendation['risk_score']}",
                    f"- Overall Score: {recommendation['overall_score']}",
                    f"- Rating: {recommendation['rating']}",
                    self._format_list("Reasons", recommendation["reasons"]),
                    self._format_list("Risks", recommendation["risks"]),
                    "",
                ])

        lines.extend([
            "",
            "## Portfolio Snapshot",
            "",
        ])

        if snapshot is None:
            lines.append("No portfolio snapshot saved for this run.")

        else:
            lines.extend([
                f"- Cash: ${snapshot['cash']:.2f}",
                f"- Portfolio Value: ${snapshot['portfolio_value']:.2f}",
                f"- Positions: {snapshot['position_count']}",
                f"- Risk: {snapshot['risk_level']}",
                f"- Cash %: {snapshot['cash_percentage']:.2f}%",
            ])

        lines.append("")

        return "\n".join(lines)

    def _format_list(self, label, values):
        if not values:
            return f"- {label}: None"

        return f"- {label}: {', '.join(values)}"
