class RuntimeScheduler:
    TASKS = [
        {
            "state": "INITIALIZING",
            "task": "Initialize beta runtime",
            "next_state": "PRE_MARKET",
        },
        {
            "state": "PRE_MARKET",
            "task": "Provider, macro, catalyst, and watchlist update",
            "next_state": "MARKET_OPEN",
        },
        {
            "state": "MARKET_OPEN",
            "task": "Monitor paper-only recommendation state",
            "next_state": "MARKET_CLOSE",
        },
        {
            "state": "MARKET_CLOSE",
            "task": "Update paper portfolio and benchmarks",
            "next_state": "POST_MARKET",
        },
        {
            "state": "POST_MARKET",
            "task": "Refresh observatory, validation, and operations summary",
            "next_state": "IDLE",
        },
        {
            "state": "IDLE",
            "task": "Wait for next market-day paper cycle",
            "next_state": "PRE_MARKET",
        },
        {
            "state": "ERROR",
            "task": "Hold runtime for human review",
            "next_state": "IDLE",
        },
    ]

    def timeline(self, current_state, last_successful_cycle=None, uptime="0 days"):
        index = self._index(current_state)
        current = self.TASKS[index]
        previous = self.TASKS[index - 1] if index > 0 else self.TASKS[-1]
        next_task = self._task(current["next_state"])

        return {
            "last_completed_task": previous["task"],
            "current_task": current["task"],
            "next_scheduled_task": next_task["task"],
            "last_successful_cycle": last_successful_cycle,
            "runtime_uptime": uptime,
        }

    def next_cycle(self, current_state):
        current = self._task(current_state)

        return {
            "next_state": current["next_state"],
            "next_task": self._task(current["next_state"])["task"],
        }

    def _task(self, state):
        return next(
            item for item in self.TASKS
            if item["state"] == state
        )

    def _index(self, state):
        for index, task in enumerate(self.TASKS):
            if task["state"] == state:
                return index

        return 0
