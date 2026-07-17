from database.setup import setup_database
from database.repository import (
    get_latest_benchmark_results,
    get_latest_evidence_benchmarks,
)
from engines.change_engine import ChangeEngine
from engines.explainability_engine import ExplainabilityEngine
from engines.history_engine import HistoryEngine
from engines.portfolio_health_engine import PortfolioHealthEngine
from engines.validation_engine import ValidationEngine


explainability_engine = ExplainabilityEngine()
validation_engine = ValidationEngine()


def print_recommendation(recommendation):
    explanation = explainability_engine.generate(recommendation)

    print(
        f"    {recommendation['ticker']} | "
        f"{recommendation['action']} | "
        f"{recommendation['confidence']}% Confidence | "
        f"Score: {recommendation['score']}"
    )
    print(f"      Technical Score: {recommendation['technical_score']}")
    print(f"      Fundamental Score: {recommendation['fundamental_score']}")
    print(f"      Portfolio Score: {recommendation['portfolio_score']}")
    print(f"      Risk Score: {recommendation['risk_score']}")
    print(f"      Forecast Direction: {recommendation['forecast_direction']}")
    print(f"      Forecast Confidence: {recommendation['forecast_confidence']}")
    print(f"      Expected Change: {recommendation['expected_change']:.2f}%")
    print(f"      Forecast Score: {recommendation['forecast_score']}")
    print(f"      Overall Score: {recommendation['overall_score']}")
    print(f"      Rating: {recommendation['rating']}")
    print(f"      News Sentiment: {recommendation['news_sentiment']}")
    print(f"      News Confidence: {recommendation['news_confidence']}")
    print(f"      Headline Count: {recommendation['headline_count']}")
    print(f"      News Summary: {recommendation['news_summary']}")
    print(f"      Signal Quality: {recommendation['signal_quality_score']}/10")
    print(f"      Signal Label: {recommendation['signal_label']}")
    print(f"      Overall Conviction: {recommendation['overall_conviction']}")
    print(f"      Fusion Summary: {recommendation['fusion_summary']}")
    print(f"      Explanation: {explanation['summary']}")
    print(f"      Why This Rating: {explanation['why_this_rating']}")

    if explanation["strengths"]:
        print(f"      Strengths: {', '.join(explanation['strengths'])}")

    if explanation["weaknesses"]:
        print(f"      Weaknesses: {', '.join(explanation['weaknesses'])}")

    if recommendation["reasons"]:
        print(f"      Reasons: {', '.join(recommendation['reasons'])}")

    if recommendation["risks"]:
        print(f"      Risks: {', '.join(recommendation['risks'])}")

    if recommendation["false_positive_warnings"]:
        warnings = ", ".join(recommendation["false_positive_warnings"])
        print(f"      False Positive Warnings: {warnings}")

    if recommendation["bull_case"]:
        print(f"      Bull Case: {', '.join(recommendation['bull_case'])}")

    if recommendation["bear_case"]:
        print(f"      Bear Case: {', '.join(recommendation['bear_case'])}")

    if recommendation["neutral_case"]:
        print(f"      Neutral Case: {', '.join(recommendation['neutral_case'])}")

    if recommendation["conflicting_signals"]:
        conflicts = ", ".join(recommendation["conflicting_signals"])
        print(f"      Conflicting Signals: {conflicts}")

    if recommendation["missing_inputs"]:
        missing_inputs = ", ".join(recommendation["missing_inputs"])
        print(f"      Missing Fusion Inputs: {missing_inputs}")

    if recommendation.get("final_committee_summary"):
        print("      Investment Committee:")
        print(
            "        Agreement: "
            f"{recommendation.get('committee_agreement', 0)}%"
        )
        print(
            "        Summary: "
            f"{recommendation['final_committee_summary']}"
        )

        if recommendation.get("bullish_members"):
            bullish = ", ".join(recommendation["bullish_members"])
            print(f"        Bullish Members: {bullish}")

        if recommendation.get("bearish_members"):
            bearish = ", ".join(recommendation["bearish_members"])
            print(f"        Bearish Members: {bearish}")

        if recommendation.get("main_disagreement"):
            print(
                "        Main Disagreement: "
                f"{recommendation['main_disagreement']}"
            )

    if recommendation["evidence_breakdown"]:
        print("      Evidence Breakdown:")
        for item in recommendation["evidence_breakdown"]:
            metadata = item.get("confidence_metadata", {})
            print(
                "        "
                f"{item['name']}: "
                f"{item['score']} | "
                f"Weight: {item['weight']} | "
                f"{item['label']} | "
                f"Reliability: {metadata.get('reliability_label', 'N/A')}"
            )

    if recommendation.get("strongest_assumption"):
        print(
            "      Strongest Assumption: "
            f"{recommendation['strongest_assumption']}"
        )

    if recommendation.get("weakest_assumption"):
        print(
            "      Weakest Assumption: "
            f"{recommendation['weakest_assumption']}"
        )

    if recommendation.get("recommendation_flip_conditions"):
        conditions = ", ".join(
            recommendation["recommendation_flip_conditions"]
        )
        print(f"      Flip Conditions: {conditions}")

    if recommendation.get("stability_level"):
        print("      Recommendation Stability:")
        print(
            "        Score: "
            f"{recommendation.get('stability_score', 0)}/100"
        )
        print(f"        Level: {recommendation['stability_level']}")
        print(
            "        Most Sensitive Factor: "
            f"{recommendation.get('most_sensitive_factor', '')}"
        )
        print(
            "        Explanation: "
            f"{recommendation.get('stability_explanation', '')}"
        )

    if recommendation.get("knowledge_level"):
        print("      Knowledge Score:")
        print(
            "        Score: "
            f"{recommendation.get('knowledge_score', 0)}/100"
        )
        print(f"        Level: {recommendation['knowledge_level']}")
        print(
            "        Explanation: "
            f"{recommendation.get('knowledge_explanation', '')}"
        )

    if recommendation.get("executive_status"):
        print("      Executive Review:")
        print(f"        Status: {recommendation['executive_status']}")
        print(
            "        Confidence: "
            f"{recommendation.get('executive_confidence', 0)}%"
        )
        print(
            "        Summary: "
            f"{recommendation.get('executive_summary', '')}"
        )

        if recommendation.get("executive_warnings"):
            warnings = ", ".join(recommendation["executive_warnings"])
            print(f"        Warnings: {warnings}")


def print_validation_result(recommendation):
    validation = recommendation.get("validation_result")

    print("      Validation Result")

    if validation is None:
        print("        Status: Awaiting Validation")
        return

    outcome = "Hit" if validation["success"] else "Miss"
    print(f"        Status: {validation['status']}")
    print(f"        Return: {validation['percentage_return']}%")
    print(f"        Hit/Miss: {outcome}")
    print(f"        Holding Period: {validation['holding_period']}")
    print(f"        Evaluation Time: {validation['evaluation_timestamp']}")

    if validation["notes"]:
        print(f"        Notes: {validation['notes']}")


def print_performance_metrics(recommendations):
    validation_results = [
        recommendation["validation_result"]
        for recommendation in recommendations
        if recommendation.get("validation_result") is not None
    ]
    metrics = validation_engine.performance_metrics(validation_results)

    print("Performance")
    print(f"    Overall Hit Rate: {metrics['overall_hit_rate']}%")
    print(f"    BUY Hit Rate: {metrics['buy_hit_rate']}%")
    print(f"    HOLD Hit Rate: {metrics['hold_hit_rate']}%")
    print(f"    AVOID Hit Rate: {metrics['avoid_hit_rate']}%")
    print(f"    Average Return: {metrics['average_return']}%")
    print(f"    Average Gain: {metrics['average_gain']}%")
    print(f"    Average Loss: {metrics['average_loss']}%")
    print(f"    Largest Gain: {metrics['largest_gain']}%")
    print(f"    Largest Loss: {metrics['largest_loss']}%")
    print(f"    Win/Loss Ratio: {metrics['win_loss_ratio']}")
    print(f"    Max Drawdown: {metrics['max_drawdown']}")
    print(f"    Sharpe Ratio: {metrics['sharpe_ratio']}")


def print_benchmark_summaries():
    benchmark_results = get_latest_benchmark_results(limit=10)
    evidence_results = get_latest_evidence_benchmarks(limit=10)

    print("Benchmark Summary")

    if not benchmark_results and not evidence_results:
        print("    No benchmark results saved.")
        return

    for result in benchmark_results:
        print(
            "    "
            f"{result['engine_name']} | "
            f"{result['metric']}: "
            f"{result['value']} | "
            f"{result['benchmark_date']}"
        )

    for result in evidence_results:
        print(
            "    "
            f"{result['source_name']} evidence | "
            f"Effectiveness: {result['effectiveness_score']} | "
            f"Samples: {result['sample_count']} | "
            f"{result['last_benchmark_date']}"
        )


def print_portfolio_snapshot(snapshot):
    print("Portfolio Snapshot")

    if snapshot is None:
        print("    No portfolio snapshot saved.")
        return

    print(f"    Cash: ${snapshot['cash']:.2f}")
    print(f"    Portfolio Value: ${snapshot['portfolio_value']:.2f}")
    print(f"    Positions: {snapshot['position_count']}")
    print(f"    Risk: {snapshot['risk_level']}")
    print(f"    Cash %: {snapshot['cash_percentage']:.2f}%")


def print_portfolio_health(health):
    print("Portfolio Health")
    print(f"    Health Score: {health['health_score']}/100")
    print(f"    Diversification: {health['diversification_rating']}")
    print(f"    Cash Rating: {health['cash_rating']}")
    print(f"    Risk Rating: {health['risk_rating']}")
    print(f"    Summary: {health['summary']}")


def print_run_changes(changes):
    print()
    print("What Changed Since Last Run")
    print(f"Market Status: {changes['market_status_change']}")
    print(f"Average RSI Change: {changes['average_rsi_change']:.1f}")
    print(
        "Average Volatility Change: "
        f"{changes['average_volatility_change']:.2f}%"
    )
    print(f"Summary: {changes['summary']}")


def print_recommendation_changes(changes):
    print("Recommendation Changes")

    visible_changes = [
        change for change in changes
        if (
            change["previous_action"] != change["current_action"]
            or change["confidence_change"] != 0
        )
    ]

    if not visible_changes:
        print("    No recommendation changes found.")
        return

    for change in visible_changes:
        confidence_change = change["confidence_change"]
        print(
            f"    {change['ticker']}: "
            f"{change['previous_action']} → {change['current_action']} | "
            f"Confidence change: {confidence_change:+d}"
        )


def print_portfolio_health_change(change):
    print("Portfolio Health Change")

    if change is None:
        print("    No portfolio health comparison available.")
        return

    print(
        "    Health Score: "
        f"{change['previous_health_score']} → "
        f"{change['current_health_score']}"
    )
    print(f"    Change: {change['health_score_change']:+d}")
    print(
        "    Risk: "
        f"{change['previous_risk_rating']} → "
        f"{change['current_risk_rating']}"
    )
    print(
        "    Cash: "
        f"{change['previous_cash_rating']} → "
        f"{change['current_cash_rating']}"
    )
    print(
        "    Diversification: "
        f"{change['previous_diversification_rating']} → "
        f"{change['current_diversification_rating']}"
    )
    print(f"    Summary: {change['summary']}")


def main():
    setup_database()

    change_engine = ChangeEngine()
    history = HistoryEngine()
    portfolio_health = PortfolioHealthEngine()
    runs = history.recent_runs(limit=5)

    print("=" * 60)
    print("ATLAS RUN HISTORY")
    print("=" * 60)

    if not runs:
        print("No saved Atlas runs found.")
        return

    if len(runs) >= 2:
        changes = change_engine.compare_runs(runs[0], runs[1])
        print_run_changes(changes)
        current_recommendations = history.recommendations_for_run(runs[0]["id"])
        previous_recommendations = history.recommendations_for_run(runs[1]["id"])
        recommendation_changes = change_engine.compare_recommendations(
            current_recommendations,
            previous_recommendations
        )
        print_recommendation_changes(recommendation_changes)
        current_snapshot = history.portfolio_snapshot(runs[0]["id"])
        previous_snapshot = history.portfolio_snapshot(runs[1]["id"])
        portfolio_health_change = change_engine.compare_portfolio_health(
            current_snapshot,
            previous_snapshot,
            portfolio_health
        )
        print_portfolio_health_change(portfolio_health_change)

    print()
    print_benchmark_summaries()

    for run in runs:
        print()
        print(f"Run ID: {run['id']}")
        print(f"Run Time: {run['run_time']}")
        print(f"Market Status: {run['market_status']}")
        print(f"Average RSI: {run['average_rsi']:.1f}")
        print(f"Average Volatility: {run['average_volatility']:.2f}%")

        recommendations = history.recommendations_for_run(run["id"])

        print("Recommendations:")

        if not recommendations:
            print("    No recommendations saved for this run.")
        else:
            for recommendation in recommendations:
                print_recommendation(recommendation)
                print_validation_result(recommendation)

        print_performance_metrics(recommendations)

        snapshot = history.portfolio_snapshot(run["id"])
        print_portfolio_snapshot(snapshot)

        if snapshot is not None:
            health = portfolio_health.calculate_health(snapshot)
            print_portfolio_health(health)


if __name__ == "__main__":
    main()
