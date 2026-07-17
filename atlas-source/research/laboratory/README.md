# Atlas Research Laboratory

The Atlas Research Laboratory evaluates Atlas itself. It is not a recommendation
engine and it does not change production recommendation behavior.

## Purpose

ARL helps answer:

- Which engines improve recommendation quality?
- Which providers perform best?
- Which evidence combinations work best?
- Which assumptions fail most often?
- Which assumptions produce the highest accuracy?
- Which counterfactual scenarios appear most frequently?
- Which engines and providers are improving or degrading over time?
- Which executive warnings predict misses or unnecessary caution?
- Which historical replay variants outperform Atlas over fixed windows?
- Which configurations should be tested next?

## Experiment Lifecycle

1. Define an experiment title, description, dataset, ticker list, provider
   configuration, selected forecast/news/fundamental providers, validation
   window, benchmark snapshot, related discovery IDs, status, and notes.
2. Generate a deterministic experiment ID from the title, date, dataset, and
   ticker list.
3. Compare strategy combinations such as Technical only, Technical + Forecast,
   Technical + Forecast + Fundamentals, and Everything.
4. Compare providers side by side by provider family.
5. Attribute recommendations to the strongest contributor, confidence drag, and
   evidence that materially changed the recommendation.
6. Analyze hypothesis fields for failed assumptions, high-accuracy assumptions,
   and frequent counterfactuals.
7. Store normalized results in research tables.
8. Generate a Markdown report for review.
9. Feed findings into benchmark planning and future experiments.

## Engine Evaluation Philosophy

Atlas should promote intelligence components only when measured evidence shows
that they help recommendation quality. Each candidate engine or provider should
be evaluated for:

- Recommendation count.
- Hit rate.
- Average return.
- Average gain.
- Average loss.
- Confidence.
- Runtime.
- Missing data.
- Failure behavior.

Provider comparisons should cover forecast, news, fundamentals, and future
provider families. Current defaults remain mock/fake/offline so tests are
deterministic and Atlas remains usable without paid APIs.

Hypothesis analysis is read-only. It studies persisted assumptions and
counterfactuals after recommendations have been generated, then reports
patterns for human review. It cannot change action thresholds, engine weights,
providers, or Atlas configuration.

Performance Observatory analysis is also read-only. ARL can use observatory
report cards to design experiments around low-accuracy engines, weak providers,
committee disagreement, confidence calibration, or validation drift. Those
findings remain advisory until a human explicitly approves implementation.

Executive review analysis studies common warnings, missing evidence, false
positives, and false negatives. A false positive means executive review allowed
or cautioned a recommendation that later failed validation. A false negative
means executive review required review or flagged insufficient data for a
recommendation that later succeeded. These labels guide experiments; they do
not alter review thresholds automatically.

Historical validation experiments replay deterministic historical rows across
date ranges and validation windows. ARL can compare Atlas against variants
without forecast, news, fundamentals, committee, or executive review. These
comparisons produce research evidence only and do not change production
behavior.

## AI-Assisted Portfolio Adjustment Research Note

Stanford GSB's AI analyst research suggests that AI-assisted investing should
be studied as a disciplined research workflow, not treated as a live trading
shortcut. For Atlas, the relevant experiment design is historical portfolio
adjustment using public information only.

ARL should test whether Atlas can propose risk-controlled portfolio adjustments
from information that would have been available at the time, then compare the
AI-adjusted portfolio against the original portfolio over quarterly evaluation
windows. The comparison should measure return improvement, risk change,
turnover, concentration, drawdown, and whether the proposed changes stayed
within approved risk limits.

Future experiment idea: `Atlas vs Original Portfolio`.

Future benchmark: AI-adjusted return improvement over baseline portfolio.

This research is not live trading, does not imply guaranteed returns, and must
not execute orders automatically. Any portfolio change requires validation,
human approval, and a separate implementation decision before it can affect
real allocations.

Historical replay data is loaded through a historical data adapter. The default
adapter is mock, offline, deterministic, and returns OHLCV rows for approved
tickers. Adapter output must pass date-range, ticker, row-count, and timestamp
ordering validation before replay.

Historical and research experiments support subsystem toggles for technical,
fundamentals, forecast, news, portfolio, risk, committee, executive review,
hypothesis, and discovery. Comparison mode creates Full Atlas, No Forecast, No
News, No Fundamentals, No Committee, and No Executive Review rows. Disabled
subsystems are recorded as disabled evidence for auditability and do not affect
normal Atlas recommendation behavior outside experiments.

Historical comparison rows include statistical context: sample size, mean
return, standard deviation, standard error, 95% confidence intervals, win rate
confidence intervals, comparison deltas, and practical significance labels.
Small samples are explicitly labeled `Insufficient Sample`; larger experiments
can be labeled `Not Meaningful`, `Possibly Meaningful`, or `Meaningful`.

The Knowledge Graph lets ARL query related institutional memory before forming
new experiments. It can retrieve similar recommendations, provider history,
committee and executive review history, historical analogs, common failures,
and successful assumptions. These graph results are context for research design
only and do not modify Atlas automatically.

## Controlled Learning

Atlas does not self-modify. ARL can suggest better strategies, promising
providers, or follow-up experiments, but it cannot change recommendation logic,
provider selection, or engine weights.

Any adjustment must be reviewed, approved, implemented, and tested by a human
before it affects Atlas behavior.

## Discovery Integration

The Discovery Engine produces evidence-backed observations from historical
recommendations, validations, benchmarks, committee outputs, and prior research
experiments. ARL experiments can reference discovery IDs so observations become
testable hypotheses.

Example workflow:

1. Discovery observes that a specific evidence combination has a higher hit
   rate.
2. The discovery is flagged with sample size, confidence, support level, and
   warnings.
3. ARL creates an experiment that references the discovery ID.
4. The experiment tests the hypothesis against a controlled dataset.
5. Results are reviewed by a human before any Atlas behavior changes.

Tiny-sample discoveries are research leads only. They should not be treated as
proof, and Atlas must not automatically adjust weights, providers, or
recommendation actions from discovery output.

## Reports

Research reports include:

- Executive summary.
- Experiment configuration.
- Strategy results.
- Provider comparison.
- Hypothesis analysis.
- Executive review analysis.
- Recommendations.
- Next experiments.
- Future work.

Reports are generated as Markdown strings by the research engine. Runtime report
files should not be committed.

## Research Laboratory Engine (Beta Sprint 2)

`engines/research_lab_engine.py` implements the Research Laboratory as the home
for every experimental feature before it can reach production. It is a
deterministic, read-only orchestration layer that reuses the Simulation Arena
for metrics and the Scientific Validation Framework for adoption decisions
rather than duplicating that logic.

### Experiment states

PROPOSED, IMPLEMENTING, READY_FOR_TEST, RUNNING, VALIDATING, ADOPTED, REJECTED,
ARCHIVED.

### Stored experiment fields

Experiment id, title, description, status, created date, author, feature being
tested, baseline strategy, candidate strategy, validation state, notes, and
priority.

### Metrics stored per executed experiment

Sharpe, Sortino, win rate, average return, drawdown, trade frequency, holding
period, alpha, probability calibration, knowledge score, and stability score,
for both baseline and candidate.

### Validation outcomes

Scientific result of Improved, Neutral, Regression, or Not Enough Evidence, with
an adoption decision of ADOPT, RETEST, or REJECT. No experiment may modify Atlas
automatically. Human approval is always required, and evidence always wins.

### Surfaces

- API: `/research-lab`, `/experiments`, `/experiments/history`,
  `/experiments/active`, `/validation/latest`.
- Frontend: the React Research Laboratory page with experiment queue,
  comparison, validation results, arena comparison, roadmap, timeline, and
  searchable history, plus an Operations Center research summary.
- Tests: `backend/test_research_lab.py`.
