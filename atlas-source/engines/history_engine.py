from database.repository import (
    get_portfolio_snapshot,
    get_recent_runs,
    get_recommendations_for_run,
)


class HistoryEngine:

    def recent_runs(self, limit=5):
        return get_recent_runs(limit)

    def recommendations_for_run(self, run_id):
        return get_recommendations_for_run(run_id)

    def portfolio_snapshot(self, run_id):
        return get_portfolio_snapshot(run_id)
