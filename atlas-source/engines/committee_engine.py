from engines.committee_member import CommitteeMember
from engines.strategy_registry_engine import StrategyRegistryEngine


class CommitteeEngine:
    """Deterministic research-only investment committee over registry strategies.

    Convenes one CommitteeMember per built-in registry strategy and combines
    their votes on a single stock record into one explainable committee
    recommendation: consensus action, agreement %, coverage-weighted
    confidence, majority and minority reports, an aggregate driver summary,
    and an overall strength grade.

    Deterministic rules (documented, no LLM, no randomness):
    - Consensus is the modal action among voting members; ties break toward
      the most conservative action (AVOID > HOLD > BUY).
    - Weighted confidence = sum(confidence x coverage) / sum(coverage) across
      voting members, so a member voting on partial data moves the committee
      less than one voting on full data.
    - Quorum: at least half the committee (rounded up) must vote; below
      quorum the committee output is NOT_EVALUATED and abstentions are
      reported with their reasons — nothing is guessed.
    - Strength: STRONG (agreement >= 75 and confidence >= 65), MODERATE
      (agreement >= 60 and confidence >= 50), SPLIT (agreement < 50),
      otherwise WEAK.

    Research-only: this engine never touches the live paper fund, portfolio
    construction, risk management, or any execution path.
    """

    VERSION = "committee-v1"

    # Registry strategies convened as the built-in committee, in fixed order.
    BUILT_IN_COMMITTEE = [
        "atlas-baseline-v1",
        "momentum-trend-v1",
        "quality-compounder-v1",
        "growth-horizon-v1",
        "value-discipline-v1",
        "defensive-ballast-v1",
    ]

    # Tie-break priority: most conservative action wins a tied vote.
    ACTION_PRIORITY = {"AVOID": 2, "HOLD": 1, "BUY": 0}

    STRENGTH_LEVELS = ["STRONG", "MODERATE", "WEAK", "SPLIT", "NOT_EVALUATED"]

    def __init__(self, registry=None, member_ids=None):
        self.registry = registry or StrategyRegistryEngine()
        ids = list(member_ids or self.BUILT_IN_COMMITTEE)
        self.members = []
        for strategy_id in ids:
            spec = self.registry.get_strategy(strategy_id)
            if spec is None:
                raise ValueError(
                    f"Committee member strategy not found in registry: "
                    f"{strategy_id}"
                )
            self.members.append(CommitteeMember(spec, registry=self.registry))

    @property
    def quorum(self):
        return (len(self.members) + 1) // 2

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def evaluate(self, stock):
        ticker = self._ticker(stock)
        votes = []
        for member in self.members:
            vote = member.evaluate(stock)
            votes.append({
                "member_id": member.strategy_id,
                "member_name": member.name,
                "expected_holding_period": member.spec["expected_holding_period"],
                **vote,
            })

        voting = [vote for vote in votes if vote["status"] != "NOT_EVALUATED"]
        abstaining = [vote for vote in votes if vote["status"] == "NOT_EVALUATED"]

        if len(voting) < self.quorum:
            return self._below_quorum(ticker, votes, voting, abstaining)

        consensus = self._consensus_action(voting)
        majority = [vote for vote in voting if vote["action"] == consensus]
        minority = [vote for vote in voting if vote["action"] != consensus]
        agreement = round(len(majority) / len(voting) * 100, 2)
        confidence = self._weighted_confidence(voting)
        strength = self._strength(agreement, confidence)
        drivers = self._driver_summary(voting)

        status = "EVALUATED" if not abstaining and all(
            vote["status"] == "EVALUATED" for vote in voting
        ) else "PARTIAL"

        return {
            "version": self.VERSION,
            "ticker": ticker,
            "status": status,
            "committee_recommendation": {
                "action": consensus,
                "strength": strength,
                "confidence": confidence,
                "agreement_pct": agreement,
                "explanation": (
                    f"{len(majority)} of {len(voting)} voting members "
                    f"({agreement}%) reached {consensus} with weighted "
                    f"confidence {confidence}; strength {strength}."
                    + (
                        f" {len(abstaining)} member(s) abstained on missing data."
                        if abstaining else ""
                    )
                ),
            },
            "votes": votes,
            "agreement": {
                "agreement_pct": agreement,
                "voting_members": len(voting),
                "abstaining_members": len(abstaining),
                "quorum": self.quorum,
                "tally": self._tally(voting),
            },
            "confidence": confidence,
            "majority_report": self._majority_report(consensus, majority),
            "minority_report": self._minority_report(minority),
            "driver_summary": drivers,
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Consensus mechanics
    # ------------------------------------------------------------------
    def _consensus_action(self, voting):
        tally = self._tally(voting)
        best_count = max(tally.values())
        tied = [action for action, count in tally.items() if count == best_count]
        # Deterministic tie-break: the most conservative action wins.
        return max(tied, key=lambda action: self.ACTION_PRIORITY[action])

    def _tally(self, voting):
        tally = {}
        for vote in voting:
            tally[vote["action"]] = tally.get(vote["action"], 0) + 1
        return dict(sorted(tally.items()))

    def _weighted_confidence(self, voting):
        total_coverage = sum(vote["coverage_pct"] for vote in voting)
        if not total_coverage:
            return 0
        weighted = sum(
            vote["confidence"] * vote["coverage_pct"] for vote in voting
        )
        return round(weighted / total_coverage, 2)

    def _strength(self, agreement, confidence):
        if agreement >= 75 and confidence >= 65:
            return "STRONG"
        if agreement >= 60 and confidence >= 50:
            return "MODERATE"
        if agreement < 50:
            return "SPLIT"
        return "WEAK"

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    def _majority_report(self, consensus, majority):
        shared = self._shared_drivers(majority)
        return {
            "action": consensus,
            "members": [vote["member_name"] for vote in majority],
            "shared_drivers": shared,
            "summary": (
                f"{', '.join(vote['member_name'] for vote in majority)} "
                f"support {consensus}"
                + (
                    f", most commonly driven by "
                    f"{', '.join(item['signal'] for item in shared[:3])}."
                    if shared else "."
                )
            ),
        }

    def _minority_report(self, minority):
        if not minority:
            return {
                "dissenters": [],
                "summary": "No dissent: every voting member reached the consensus action.",
            }
        dissenters = [
            {
                "member_id": vote["member_id"],
                "member_name": vote["member_name"],
                "action": vote["action"],
                "confidence": vote["confidence"],
                "score": vote["score"],
                "top_driver": (
                    vote["drivers"][0]["signal"] if vote["drivers"] else None
                ),
                "explanation": vote["explanation"],
            }
            for vote in minority
        ]
        return {
            "dissenters": dissenters,
            "summary": (
                "; ".join(
                    f"{item['member_name']} dissents with {item['action']} "
                    f"(confidence {item['confidence']})"
                    for item in dissenters
                )
                + "."
            ),
        }

    def _shared_drivers(self, votes):
        counts = {}
        for vote in votes:
            for driver in vote["drivers"][:3]:
                entry = counts.setdefault(
                    driver["signal"], {"signal": driver["signal"], "members": 0}
                )
                entry["members"] += 1
        shared = [item for item in counts.values() if item["members"] >= 2]
        return sorted(shared, key=lambda item: (-item["members"], item["signal"]))

    def _driver_summary(self, voting):
        totals = {}
        for vote in voting:
            for driver in vote["drivers"]:
                entry = totals.setdefault(
                    driver["signal"],
                    {"signal": driver["signal"], "total_contribution": 0.0,
                     "members": 0},
                )
                entry["total_contribution"] += driver["contribution"]
                entry["members"] += 1
        summary = [
            {
                "signal": entry["signal"],
                "total_contribution": round(entry["total_contribution"], 2),
                "members": entry["members"],
            }
            for entry in totals.values()
        ]
        return sorted(
            summary,
            key=lambda item: (-item["total_contribution"], item["signal"]),
        )[:5]

    # ------------------------------------------------------------------
    # NOT_EVALUATED propagation
    # ------------------------------------------------------------------
    def unavailable(self, ticker, reason):
        """NOT_EVALUATED committee output when no stock record exists.

        Same shape as a below-quorum result so API consumers handle one
        contract; used instead of fabricating stock inputs.
        """
        symbol = str(ticker or "").strip().upper() or None
        return {
            "version": self.VERSION,
            "ticker": symbol,
            "status": "NOT_EVALUATED",
            "reason": reason,
            "committee_recommendation": {
                "action": None,
                "strength": "NOT_EVALUATED",
                "confidence": None,
                "agreement_pct": None,
                "explanation": reason,
            },
            "votes": [],
            "agreement": {
                "agreement_pct": None,
                "voting_members": 0,
                "abstaining_members": len(self.members),
                "quorum": self.quorum,
                "tally": {},
            },
            "confidence": None,
            "majority_report": {"action": None, "members": [],
                                "shared_drivers": [], "summary": reason},
            "minority_report": {"dissenters": [], "summary": reason},
            "driver_summary": [],
            "policy": self.policy(),
        }

    def _below_quorum(self, ticker, votes, voting, abstaining):
        reason = (
            f"Only {len(voting)} of {len(self.members)} members could vote; "
            f"quorum is {self.quorum}. Missing inputs: "
            + (
                "; ".join(
                    f"{vote['member_name']}: {', '.join(vote['missing_inputs'])}"
                    for vote in abstaining
                )
                or "none recorded"
            )
            + "."
        )
        return {
            "version": self.VERSION,
            "ticker": ticker,
            "status": "NOT_EVALUATED",
            "reason": reason,
            "committee_recommendation": {
                "action": None,
                "strength": "NOT_EVALUATED",
                "confidence": None,
                "agreement_pct": None,
                "explanation": reason,
            },
            "votes": votes,
            "agreement": {
                "agreement_pct": None,
                "voting_members": len(voting),
                "abstaining_members": len(abstaining),
                "quorum": self.quorum,
                "tally": self._tally(voting),
            },
            "confidence": None,
            "majority_report": {"action": None, "members": [], "shared_drivers": [],
                                "summary": "No quorum."},
            "minority_report": {"dissenters": [], "summary": "No quorum."},
            "driver_summary": [],
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Utilities & policy
    # ------------------------------------------------------------------
    def _ticker(self, stock):
        if isinstance(stock, dict):
            value = stock.get("ticker") or stock.get("symbol")
        else:
            value = getattr(stock, "ticker", None) or getattr(stock, "symbol", None)
        return str(value).strip().upper() if value else None

    def policy(self):
        return {
            "research_only": True,
            "read_only": True,
            "deterministic": True,
            "llm_decisions": False,
            "randomness": False,
            "broker_integration": False,
            "real_money": False,
            "creates_orders": False,
            "modifies_live_paper_fund": False,
            "modifies_portfolio_construction": False,
            "modifies_risk_management": False,
            "modifies_trading_execution": False,
        }
