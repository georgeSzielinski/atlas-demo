from database.connection import get_connection


def add_column_if_missing(cursor, table_name, column_definition):
    try:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"
        )
    except Exception as error:
        if "duplicate column name" not in str(error).lower():
            raise


def setup_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atlas_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_time TEXT,
            market_status TEXT,
            average_rsi REAL,
            average_volatility REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            ticker TEXT,
            action TEXT,
            confidence INTEGER,
            reasons TEXT,
            risks TEXT,
            score INTEGER,
            technical_score INTEGER,
            fundamental_score INTEGER,
            portfolio_score INTEGER,
            risk_score INTEGER,
            forecast_score INTEGER,
            forecast_direction TEXT,
            forecast_confidence INTEGER,
            expected_change REAL,
            overall_score INTEGER,
            rating TEXT,
            news_sentiment TEXT,
            news_confidence INTEGER,
            headline_count INTEGER,
            news_summary TEXT,
            signal_quality_score INTEGER,
            signal_label TEXT,
            false_positive_warnings TEXT,
            evidence_breakdown TEXT,
            confidence_metadata TEXT,
            validation_status TEXT,
            overall_conviction REAL,
            bull_case TEXT,
            bear_case TEXT,
            neutral_case TEXT,
            strongest_positive_factor TEXT,
            strongest_negative_factor TEXT,
            conflicting_signals TEXT,
            missing_inputs TEXT,
            fusion_summary TEXT,
            committee_members TEXT,
            committee_bull_case TEXT,
            committee_bear_case TEXT,
            committee_neutral_case TEXT,
            committee_agreement REAL,
            bullish_members TEXT,
            bearish_members TEXT,
            neutral_members TEXT,
            strongest_bull_argument TEXT,
            strongest_bear_argument TEXT,
            main_disagreement TEXT,
            final_committee_summary TEXT,
            top_positive_factors TEXT,
            top_negative_factors TEXT,
            missing_evidence TEXT,
            suggested_follow_up_research TEXT,
            confidence_explanation TEXT,
            evidence_summary TEXT,
            assumptions TEXT,
            strongest_assumption TEXT,
            weakest_assumption TEXT,
            counterfactuals TEXT,
            recommendation_flip_conditions TEXT,
            confidence_drivers TEXT,
            executive_review TEXT,
            executive_status TEXT,
            executive_confidence INTEGER,
            executive_summary TEXT,
            executive_warnings TEXT,
            executive_strengths TEXT,
            executive_weaknesses TEXT,
            required_follow_up_research TEXT,
            stability_score INTEGER,
            stability_level TEXT,
            most_sensitive_factor TEXT,
            stability_explanation TEXT,
            knowledge_score INTEGER,
            knowledge_level TEXT,
            knowledge_explanation TEXT,
            research_memory_report TEXT
        )
    """)

    recommendation_columns = [
        "technical_score INTEGER",
        "fundamental_score INTEGER",
        "portfolio_score INTEGER",
        "risk_score INTEGER",
        "forecast_score INTEGER",
        "forecast_direction TEXT",
        "forecast_confidence INTEGER",
        "expected_change REAL",
        "overall_score INTEGER",
        "rating TEXT",
        "news_sentiment TEXT",
        "news_confidence INTEGER",
        "headline_count INTEGER",
        "news_summary TEXT",
        "signal_quality_score INTEGER",
        "signal_label TEXT",
        "false_positive_warnings TEXT",
        "evidence_breakdown TEXT",
        "confidence_metadata TEXT",
        "validation_status TEXT",
        "overall_conviction REAL",
        "bull_case TEXT",
        "bear_case TEXT",
        "neutral_case TEXT",
        "strongest_positive_factor TEXT",
        "strongest_negative_factor TEXT",
        "conflicting_signals TEXT",
        "missing_inputs TEXT",
        "fusion_summary TEXT",
        "committee_members TEXT",
        "committee_bull_case TEXT",
        "committee_bear_case TEXT",
        "committee_neutral_case TEXT",
        "committee_agreement REAL",
        "bullish_members TEXT",
        "bearish_members TEXT",
        "neutral_members TEXT",
        "strongest_bull_argument TEXT",
        "strongest_bear_argument TEXT",
        "main_disagreement TEXT",
        "final_committee_summary TEXT",
        "top_positive_factors TEXT",
        "top_negative_factors TEXT",
        "missing_evidence TEXT",
        "suggested_follow_up_research TEXT",
        "confidence_explanation TEXT",
        "evidence_summary TEXT",
        "assumptions TEXT",
        "strongest_assumption TEXT",
        "weakest_assumption TEXT",
        "counterfactuals TEXT",
        "recommendation_flip_conditions TEXT",
        "confidence_drivers TEXT",
        "executive_review TEXT",
        "executive_status TEXT",
        "executive_confidence INTEGER",
        "executive_summary TEXT",
        "executive_warnings TEXT",
        "executive_strengths TEXT",
        "executive_weaknesses TEXT",
        "required_follow_up_research TEXT",
        "stability_score INTEGER",
        "stability_level TEXT",
        "most_sensitive_factor TEXT",
        "stability_explanation TEXT",
        "knowledge_score INTEGER",
        "knowledge_level TEXT",
        "knowledge_explanation TEXT",
        "research_memory_report TEXT",
    ]

    for column_definition in recommendation_columns:
        add_column_if_missing(
            cursor,
            "recommendations",
            column_definition
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            cash REAL,
            portfolio_value REAL,
            position_count INTEGER,
            risk_level TEXT,
            cash_percentage REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_validations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id INTEGER,
            ticker TEXT,
            recommendation TEXT,
            recommendation_timestamp TEXT,
            evaluation_timestamp TEXT,
            holding_period INTEGER,
            starting_price REAL,
            ending_price REAL,
            percentage_return REAL,
            predicted_direction TEXT,
            actual_direction TEXT,
            success INTEGER,
            status TEXT,
            notes TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            engine_name TEXT,
            version TEXT,
            benchmark_date TEXT,
            metric TEXT,
            value REAL,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence_benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT,
            effectiveness_score REAL,
            sample_count INTEGER,
            last_benchmark_date TEXT,
            engine_name TEXT,
            version TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT UNIQUE,
            title TEXT,
            description TEXT,
            experiment_date TEXT,
            dataset TEXT,
            tickers TEXT,
            provider_configuration TEXT,
            forecast_provider TEXT,
            news_provider TEXT,
            fundamental_provider TEXT,
            validation_window INTEGER,
            benchmark_snapshot TEXT,
            related_discoveries TEXT,
            status TEXT,
            notes TEXT
        )
    """)

    research_experiment_columns = [
        "related_discoveries TEXT",
    ]

    for column_definition in research_experiment_columns:
        add_column_if_missing(
            cursor,
            "research_experiments",
            column_definition,
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_strategy_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT,
            strategy_name TEXT,
            components TEXT,
            recommendation_count INTEGER,
            hit_rate REAL,
            average_return REAL,
            average_gain REAL,
            average_loss REAL,
            confidence REAL,
            runtime REAL,
            missing_data TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_provider_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT,
            provider_type TEXT,
            provider_name TEXT,
            status TEXT,
            score REAL,
            rank INTEGER,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_attributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT,
            ticker TEXT,
            action TEXT,
            strongest_engine TEXT,
            confidence_drag_engine TEXT,
            changed_evidence TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS discoveries (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            supporting_data TEXT,
            sample_size INTEGER,
            confidence REAL,
            importance REAL,
            discovery_date TEXT,
            related_engines TEXT,
            related_providers TEXT,
            status TEXT,
            support_level TEXT,
            warnings TEXT,
            suggestions TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_validation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT,
            run_date TEXT,
            configuration TEXT,
            metrics TEXT,
            comparison TEXT,
            statistics TEXT,
            report TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT,
            model_type TEXT,
            provider TEXT,
            dataset TEXT,
            date_range TEXT,
            validation_window INTEGER,
            sample_size INTEGER,
            accuracy REAL,
            win_rate REAL,
            average_return REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            runtime_placeholder REAL,
            memory_placeholder REAL,
            cost_placeholder REAL,
            integration_difficulty TEXT,
            recommendation TEXT,
            overall_score REAL,
            evaluation_date TEXT,
            status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_studies (
            case_id TEXT PRIMARY KEY,
            ticker TEXT,
            recommendation TEXT,
            market_regime TEXT,
            evidence TEXT,
            committee TEXT,
            executive_review TEXT,
            knowledge_score REAL,
            stability_score REAL,
            outcome TEXT,
            return_value REAL,
            holding_period INTEGER,
            validation TEXT,
            benchmark TEXT,
            hypotheses TEXT,
            counterfactuals TEXT,
            lessons_learned TEXT,
            catalysts TEXT,
            probability_report TEXT,
            case_date TEXT
        )
    """)

    for column_definition in [
        "catalysts TEXT",
        "probability_report TEXT",
    ]:
        add_column_if_missing(
            cursor,
            "case_studies",
            column_definition,
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS probability_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id TEXT,
            ticker TEXT,
            recommendation TEXT,
            probabilities TEXT,
            expected_outcome TEXT,
            confidence_quality TEXT,
            similar_historical_cases TEXT,
            explanation TEXT,
            report_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scientific_validation_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT UNIQUE,
            report_date TEXT,
            feature_tested TEXT,
            baseline TEXT,
            candidate TEXT,
            sample_size INTEGER,
            metric_comparison TEXT,
            cross_regime_validation TEXT,
            generalization_tests TEXT,
            scientific_result TEXT,
            adoption_decision TEXT,
            adoption_explanation TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_arena_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arena_id TEXT UNIQUE,
            run_date TEXT,
            dataset TEXT,
            tickers TEXT,
            date_range TEXT,
            validation_window INTEGER,
            strategy_configs TEXT,
            market_regimes_tested TEXT,
            results TEXT,
            comparison TEXT,
            scientific_validation TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT,
            cash REAL,
            positions TEXT,
            current_value REAL,
            realized_pl REAL,
            unrealized_pl REAL,
            portfolio_value REAL,
            daily_return REAL,
            total_return REAL,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_trades (
            trade_id TEXT PRIMARY KEY,
            ticker TEXT,
            action TEXT,
            entry_date TEXT,
            entry_price REAL,
            exit_date TEXT,
            exit_price REAL,
            holding_period INTEGER,
            quantity INTEGER,
            profit_loss REAL,
            reason TEXT,
            recommendation_snapshot TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_performance_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT,
            performance TEXT,
            research TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_cycle_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT UNIQUE,
            cycle_date TEXT,
            phase TEXT,
            status TEXT,
            recommendations_count INTEGER,
            paper_portfolio_value REAL,
            daily_return REAL,
            alpha_vs_sp500 REAL,
            warnings TEXT,
            summary TEXT,
            details TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_journals (
            journal_id TEXT PRIMARY KEY,
            journal_date TEXT,
            market_regime TEXT,
            runtime_state TEXT,
            paper_portfolio_summary TEXT,
            benchmark_comparison TEXT,
            provider_health TEXT,
            macro_summary TEXT,
            catalyst_summary TEXT,
            recommendation_summary TEXT,
            performance_summary TEXT,
            lessons_learned TEXT,
            research_tasks TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_construction_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT,
            recommended_allocations TEXT,
            portfolio_actions TEXT,
            risk_summary TEXT,
            risk_budget TEXT,
            diversification TEXT,
            constraints_json TEXT,
            scenario_analysis TEXT,
            scientific_validation TEXT,
            operations_summary TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runtime_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            runtime_id TEXT UNIQUE,
            current_state TEXT,
            market_date TEXT,
            market_phase TEXT,
            last_cycle_time TEXT,
            next_cycle TEXT,
            provider_health TEXT,
            paper_portfolio_value REAL,
            active_watchlist_size INTEGER,
            open_positions INTEGER,
            recommendations_today INTEGER,
            alerts TEXT,
            tasks TEXT,
            operations_summary TEXT,
            health TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_data_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT,
            provider TEXT,
            requested_provider TEXT,
            fallback_used INTEGER,
            validated INTEGER,
            ticker_count INTEGER,
            prices TEXT,
            market_status TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_reports (
            month TEXT PRIMARY KEY,
            report_date TEXT,
            performance TEXT,
            major_lessons TEXT,
            best_decisions TEXT,
            largest_mistakes TEXT,
            research_progress TEXT,
            validation_summary TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_fund_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            updated_at TEXT,
            fund_status TEXT,
            watchlist TEXT,
            starting_cash REAL,
            cash REAL,
            positions TEXT,
            realized_pl REAL,
            interval_minutes INTEGER,
            last_update TEXT,
            next_update TEXT,
            last_error TEXT,
            price_provider TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_fund_orders (
            order_id TEXT PRIMARY KEY,
            cycle_id TEXT,
            ticker TEXT,
            side TEXT,
            quantity INTEGER,
            status TEXT,
            created_at TEXT,
            filled_at TEXT,
            fill_price REAL,
            price_source TEXT,
            validated INTEGER,
            simulated INTEGER,
            reason TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_fund_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            as_of TEXT,
            cycle_id TEXT,
            cash REAL,
            positions TEXT,
            current_value REAL,
            realized_pl REAL,
            unrealized_pl REAL,
            portfolio_value REAL,
            daily_return REAL,
            total_return REAL,
            price_source TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_fund_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT,
            cycle_id TEXT,
            activity_type TEXT,
            message TEXT,
            details TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_fund_learning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT,
            cycle_id TEXT,
            lesson TEXT,
            details TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_experiment_registry (
            experiment_id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            status TEXT,
            created_date TEXT,
            author TEXT,
            feature_being_tested TEXT,
            baseline_strategy TEXT,
            candidate_strategy TEXT,
            validation_state TEXT,
            priority TEXT,
            notes TEXT,
            adoption_decision TEXT,
            arena_metrics TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT,
            status TEXT,
            reason TEXT,
            stages TEXT,
            duration_seconds REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_cycle_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            generated_at TEXT,
            status TEXT,
            reason TEXT,
            stages TEXT,
            fund_cycle_id TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS committee_cycle_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            run_id INTEGER,
            evaluated_at TEXT,
            evaluations TEXT,
            duration_seconds REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cycle_performance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            as_of TEXT,
            report TEXT,
            policy TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS self_improvement_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT,
            generated_at TEXT,
            status TEXT,
            headline TEXT,
            findings TEXT,
            opportunities TEXT,
            not_evaluated TEXT,
            source_counts TEXT,
            policy TEXT
        )
    """)

    # Outcome-tracking foundation (migration 005): additive nullable columns +
    # indexes. Reuse the migration's single source of truth so a fresh
    # setup_database() build and a fully migrated database converge to the exact
    # same schema (verified by test_migrations' legacy-vs-migrated comparison).
    from database.migrations.migration_005_outcome_tracking import (
        OUTCOME_COLUMNS,
        OUTCOME_INDEXES,
    )

    for table, definitions in OUTCOME_COLUMNS.items():
        for definition in definitions:
            add_column_if_missing(cursor, table, definition)
    for _index_name, index_sql in OUTCOME_INDEXES:
        cursor.execute(index_sql)

    connection.commit()
    connection.close()
