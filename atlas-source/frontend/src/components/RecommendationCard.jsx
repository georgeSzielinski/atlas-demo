import ScoreBar from './ScoreBar'

function formatPercent(value) {
  if (value === null || value === undefined || value === '') {
    return 'Unavailable'
  }

  return `${value}%`
}

function formatExpectedChange(value) {
  if (value === null || value === undefined || value === '') {
    return 'Unavailable'
  }

  const numberValue = Number(value)
  const sign = numberValue > 0 ? '+' : ''

  return `${sign}${numberValue.toFixed(1)}%`
}

function formatReturn(value) {
  if (value === null || value === undefined || value === '') {
    return 'Unavailable'
  }

  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return String(value)
  }

  const sign = numberValue > 0 ? '+' : ''

  return `${sign}${numberValue.toFixed(2)}%`
}

function formatValue(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  return String(value)
}

function scoreValue(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 0
  }

  return numberValue
}

function addScoreSignal(score, strength, weakness, strengths, weaknesses) {
  if (score >= 70) {
    strengths.push(strength)
  } else if (score < 50) {
    weaknesses.push(weakness)
  }
}

function buildExplanation(recommendation) {
  if (recommendation.explanation) {
    return recommendation.explanation
  }

  const ticker = recommendation.ticker ?? recommendation.symbol ?? 'This ticker'
  const action = recommendation.action ?? 'HOLD'
  const rating = recommendation.rating || 'Unrated'
  const strengths = []
  const weaknesses = []
  const technicalScore = scoreValue(recommendation.technical_score)
  const fundamentalScore = scoreValue(recommendation.fundamental_score)
  const portfolioScore = scoreValue(recommendation.portfolio_score)
  const riskScore = scoreValue(recommendation.risk_score)
  const forecastScore = scoreValue(recommendation.forecast_score)
  const newsConfidence = scoreValue(recommendation.news_confidence)

  addScoreSignal(
    technicalScore,
    'Technical indicators support the setup.',
    'Technical indicators are not yet supportive.',
    strengths,
    weaknesses,
  )
  addScoreSignal(
    fundamentalScore,
    'Fundamentals support the recommendation.',
    'Fundamentals are a weaker part of the setup.',
    strengths,
    weaknesses,
  )
  addScoreSignal(
    forecastScore,
    `Forecast model points ${recommendation.forecast_direction || 'UNKNOWN'}.`,
    'Forecast score is not strong enough to add conviction.',
    strengths,
    weaknesses,
  )
  addScoreSignal(
    portfolioScore,
    'Portfolio fit is acceptable.',
    'Portfolio fit is limited.',
    strengths,
    weaknesses,
  )
  addScoreSignal(
    riskScore,
    'Risk profile is acceptable.',
    'Risk score is a concern.',
    strengths,
    weaknesses,
  )

  if (newsConfidence > 0) {
    strengths.push(
      `News coverage is ${recommendation.news_sentiment || 'neutral'} with available headlines.`,
    )
  } else {
    weaknesses.push('News signal is limited or unavailable.')
  }

  return {
    summary: `${ticker} is rated ${rating} with a ${action} action based on technical, fundamental, forecast, portfolio, risk, and news signals.`,
    strengths,
    weaknesses,
    why_this_rating: `The rating reflects an overall score of ${recommendation.overall_score ?? 0}, with forecast score ${forecastScore}, technical score ${technicalScore}, fundamental score ${fundamentalScore}, portfolio score ${portfolioScore}, and risk score ${riskScore}.`,
  }
}

function formatList(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean).map((item) => String(item))
  }

  if (typeof value === 'string' && value.trim()) {
    try {
      const parsed = JSON.parse(value)

      if (Array.isArray(parsed)) {
        return parsed.filter(Boolean).map((item) => String(item))
      }
    } catch {
      return [value]
    }

    return [value]
  }

  return []
}

function formatObjectList(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean)
  }

  if (typeof value === 'string' && value.trim()) {
    try {
      const parsed = JSON.parse(value)

      if (Array.isArray(parsed)) {
        return parsed.filter(Boolean)
      }
    } catch {
      return []
    }
  }

  return []
}

function validationSummary(recommendation) {
  const validation = recommendation.validation_result ?? recommendation.validation ?? null

  if (!validation) {
    return {
      status: recommendation.validation_status ?? 'Pending',
      returnValue: 'Awaiting Validation',
      hitMiss: 'Awaiting Validation',
      holdingPeriod: 'Awaiting Validation',
    }
  }

  return {
    status: validation.status ?? recommendation.validation_status ?? 'Pending',
    returnValue: formatReturn(validation.percentage_return),
    hitMiss: validation.success === null || validation.success === undefined
      ? 'Awaiting Validation'
      : validation.success
        ? 'Hit'
        : 'Miss',
    holdingPeriod: formatValue(validation.holding_period, 'Awaiting Validation'),
  }
}

function benchmarkSummary(recommendation) {
  const benchmark =
    recommendation.benchmark_summary ??
    recommendation.benchmark ??
    null

  if (!benchmark) {
    return null
  }

  return [
    ['Benchmark', benchmark.metric ?? benchmark.name],
    ['Value', benchmark.value ?? benchmark.score],
    ['Engine', benchmark.engine_name],
    ['Date', benchmark.benchmark_date],
  ].filter(([, value]) => value !== null && value !== undefined && value !== '')
}

function fusionSummary(recommendation) {
  const fusion = recommendation.fusion ?? {}

  return {
    overallConviction:
      recommendation.overall_conviction ?? fusion.overall_conviction,
    bullCase: formatList(recommendation.bull_case ?? fusion.bull_case),
    bearCase: formatList(recommendation.bear_case ?? fusion.bear_case),
    neutralCase: formatList(recommendation.neutral_case ?? fusion.neutral_case),
    strongestPositive:
      recommendation.strongest_positive_factor ??
      fusion.strongest_positive_factor,
    strongestNegative:
      recommendation.strongest_negative_factor ??
      fusion.strongest_negative_factor,
    conflictingSignals: formatList(
      recommendation.conflicting_signals ?? fusion.conflicting_signals,
    ),
    missingInputs: formatList(
      recommendation.missing_inputs ?? fusion.missing_inputs,
    ),
    summary: recommendation.fusion_summary ?? fusion.fusion_summary ?? '',
  }
}

function committeeSummary(recommendation) {
  const committee = recommendation.investment_committee ?? {}

  return {
    members: formatObjectList(
      recommendation.committee_members ?? committee.members,
    ),
    bullCase: formatList(
      recommendation.committee_bull_case ?? committee.bull_case,
    ),
    bearCase: formatList(
      recommendation.committee_bear_case ?? committee.bear_case,
    ),
    neutralCase: formatList(
      recommendation.committee_neutral_case ?? committee.neutral_case,
    ),
    agreement:
      recommendation.committee_agreement ?? committee.committee_agreement,
    bullishMembers: formatList(
      recommendation.bullish_members ?? committee.bullish_members,
    ),
    bearishMembers: formatList(
      recommendation.bearish_members ?? committee.bearish_members,
    ),
    neutralMembers: formatList(
      recommendation.neutral_members ?? committee.neutral_members,
    ),
    strongestBull:
      recommendation.strongest_bull_argument ??
      committee.strongest_bull_argument ??
      '',
    strongestBear:
      recommendation.strongest_bear_argument ??
      committee.strongest_bear_argument ??
      '',
    mainDisagreement:
      recommendation.main_disagreement ?? committee.main_disagreement ?? '',
    summary:
      recommendation.final_committee_summary ??
      committee.final_committee_summary ??
      '',
  }
}

function formatFactor(value) {
  if (!value) {
    return 'Unavailable'
  }

  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)

      return formatFactor(parsed)
    } catch {
      return value
    }
  }

  if (typeof value === 'object') {
    const name = value.name ?? 'Unknown'
    const score = value.score ?? 'Unavailable'

    return `${name}: ${score}`
  }

  return String(value)
}

function RecommendationCard({ isSelected = false, onSelect, recommendation }) {
  const action = recommendation.action ?? 'HOLD'
  const isClickable = typeof onSelect === 'function'
  const explanation = buildExplanation(recommendation)
  const falsePositiveWarnings = formatList(
    recommendation.false_positive_warnings,
  )
  const evidenceBreakdown = formatObjectList(recommendation.evidence_breakdown)
  const validation = validationSummary(recommendation)
  const benchmark = benchmarkSummary(recommendation)
  const fusion = fusionSummary(recommendation)
  const committee = committeeSummary(recommendation)
  const topPositive = formatList(recommendation.top_positive_factors)
  const topNegative = formatList(recommendation.top_negative_factors)
  const missingEvidence = formatList(recommendation.missing_evidence)
  const followUpResearch = formatList(
    recommendation.suggested_follow_up_research,
  )

  function handleKeyDown(event) {
    if (!isClickable) {
      return
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect(recommendation)
    }
  }

  return (
    <article
      className={[
        'recommendation-card',
        isClickable ? 'recommendation-card--clickable' : '',
        isSelected ? 'is-selected' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      onClick={isClickable ? () => onSelect(recommendation) : undefined}
      onKeyDown={handleKeyDown}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
    >
      <div className="recommendation-card__header">
        <div>
          <p className="recommendation-card__label">Ticker</p>
          <h2>{recommendation.ticker ?? recommendation.symbol ?? 'N/A'}</h2>
        </div>
        <span className={`action-badge action-badge--${action.toLowerCase()}`}>
          {action}
        </span>
      </div>

      <div className="recommendation-card__scores">
        <ScoreBar label="Overall Score" value={recommendation.overall_score} />
        <ScoreBar label="Confidence" suffix="%" value={recommendation.confidence} />
        <ScoreBar label="Forecast Score" value={recommendation.forecast_score} />
      </div>

      <dl className="recommendation-card__metrics">
        <div>
          <dt>Rating</dt>
          <dd>{recommendation.rating || 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{formatPercent(recommendation.confidence)}</dd>
        </div>
        <div>
          <dt>Forecast Direction</dt>
          <dd>{recommendation.forecast_direction || 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Expected Change</dt>
          <dd>{formatExpectedChange(recommendation.expected_change)}</dd>
        </div>
        <div>
          <dt>News Sentiment</dt>
          <dd>{formatValue(recommendation.news_sentiment)}</dd>
        </div>
        <div>
          <dt>News Confidence</dt>
          <dd>{formatPercent(recommendation.news_confidence)}</dd>
        </div>
        <div>
          <dt>Headline Count</dt>
          <dd>{formatValue(recommendation.headline_count)}</dd>
        </div>
        <div>
          <dt>Signal Quality</dt>
          <dd>{formatValue(recommendation.signal_quality_score)}/10</dd>
        </div>
        <div>
          <dt>Signal Label</dt>
          <dd>{formatValue(recommendation.signal_label)}</dd>
        </div>
        <div>
          <dt>Validation Status</dt>
          <dd>{validation.status}</dd>
        </div>
        <div>
          <dt>Stability</dt>
          <dd>
            {formatValue(recommendation.stability_level)} (
            {formatValue(recommendation.stability_score)}/100)
          </dd>
        </div>
        <div>
          <dt>Knowledge</dt>
          <dd>
            {formatValue(recommendation.knowledge_level)} (
            {formatValue(recommendation.knowledge_score)}/100)
          </dd>
        </div>
        <div>
          <dt>Conviction</dt>
          <dd>{formatValue(fusion.overallConviction)}</dd>
        </div>
        <div>
          <dt>Return</dt>
          <dd>{validation.returnValue}</dd>
        </div>
        <div>
          <dt>Hit/Miss</dt>
          <dd>{validation.hitMiss}</dd>
        </div>
        <div>
          <dt>Holding Period</dt>
          <dd>{validation.holdingPeriod}</dd>
        </div>
      </dl>

      <section className="recommendation-card__news">
        <strong>News Summary</strong>
        <p>{formatValue(recommendation.news_summary)}</p>
      </section>

      <section className="recommendation-card__news">
        <strong>Fusion Summary</strong>
        <p>{formatValue(fusion.summary)}</p>
      </section>

      {benchmark ? (
        <section className="recommendation-card__news">
          <strong>Benchmark Summary</strong>
          <ul>
            {benchmark.map(([label, value]) => (
              <li key={label}>
                {label}: {formatValue(value)}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {falsePositiveWarnings.length > 0 ? (
        <section className="recommendation-card__news">
          <strong>False Positive Warnings</strong>
          <ul>
            {falsePositiveWarnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <details className="recommendation-card__explanation">
        <summary>Explanation</summary>
        <p>{explanation.summary}</p>
        <p>{explanation.why_this_rating}</p>
        {explanation.strengths.length > 0 ? (
          <>
            <strong>Strengths</strong>
            <ul>
              {explanation.strengths.map((strength) => (
                <li key={strength}>{strength}</li>
              ))}
            </ul>
          </>
        ) : null}
        {explanation.weaknesses.length > 0 ? (
          <>
            <strong>Weaknesses</strong>
            <ul>
              {explanation.weaknesses.map((weakness) => (
                <li key={weakness}>{weakness}</li>
              ))}
            </ul>
          </>
        ) : null}
        {evidenceBreakdown.length > 0 ? (
          <>
            <strong>Top Evidence</strong>
            <ul>
              {evidenceBreakdown.map((item) => {
                const metadata = item.confidence_metadata ?? {}

                return (
                  <li key={item.name}>
                    {formatValue(item.category ?? item.name)}:{' '}
                    {formatValue(item.score)} | Confidence:{' '}
                    {formatValue(item.confidence)} | Weight:{' '}
                    {formatValue(item.weight)} | {formatValue(item.summary)} |
                    Reliability: {formatValue(metadata.reliability_label)}
                  </li>
                )
              })}
            </ul>
          </>
        ) : null}
        {topPositive.length > 0 ? (
          <>
            <strong>Top Positive Factors</strong>
            <ul>
              {topPositive.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        ) : null}
        {topNegative.length > 0 ? (
          <>
            <strong>Top Negative Factors</strong>
            <ul>
              {topNegative.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        ) : null}
        {missingEvidence.length > 0 ? (
          <>
            <strong>Missing Evidence</strong>
            <ul>
              {missingEvidence.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        ) : null}
        {followUpResearch.length > 0 ? (
          <>
            <strong>Suggested Follow-Up Research</strong>
            <ul>
              {followUpResearch.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        ) : null}
        {recommendation.confidence_explanation ? (
          <>
            <strong>Confidence</strong>
            <p>{recommendation.confidence_explanation}</p>
          </>
        ) : null}
        {recommendation.evidence_summary ? (
          <>
            <strong>Evidence Summary</strong>
            <p>{recommendation.evidence_summary}</p>
          </>
        ) : null}
        {recommendation.stability_level ? (
          <>
            <strong>Recommendation Stability</strong>
            <ul>
              <li>
                Level: {formatValue(recommendation.stability_level)} | Score:{' '}
                {formatValue(recommendation.stability_score)}/100
              </li>
              <li>
                Most sensitive factor:{' '}
                {formatValue(recommendation.most_sensitive_factor)}
              </li>
              <li>{formatValue(recommendation.stability_explanation)}</li>
            </ul>
          </>
        ) : null}
        {recommendation.knowledge_level ? (
          <>
            <strong>Knowledge Score</strong>
            <ul>
              <li>
                Level: {formatValue(recommendation.knowledge_level)} | Score:{' '}
                {formatValue(recommendation.knowledge_score)}/100
              </li>
              <li>{formatValue(recommendation.knowledge_explanation)}</li>
            </ul>
          </>
        ) : null}
        {fusion.summary || fusion.bullCase.length > 0 || fusion.bearCase.length > 0 ? (
          <>
            <strong>Intelligence Fusion</strong>
            <p>{formatValue(fusion.summary)}</p>
            <ul>
              <li>Overall conviction: {formatValue(fusion.overallConviction)}</li>
              <li>
                Strongest positive: {formatFactor(fusion.strongestPositive)}
              </li>
              <li>
                Strongest negative: {formatFactor(fusion.strongestNegative)}
              </li>
            </ul>
            {fusion.bullCase.length > 0 ? (
              <>
                <strong>Bull Case</strong>
                <ul>
                  {fusion.bullCase.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {fusion.bearCase.length > 0 ? (
              <>
                <strong>Bear Case</strong>
                <ul>
                  {fusion.bearCase.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {fusion.neutralCase.length > 0 ? (
              <>
                <strong>Neutral Case</strong>
                <ul>
                  {fusion.neutralCase.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {fusion.conflictingSignals.length > 0 ? (
              <>
                <strong>Conflicting Signals</strong>
                <ul>
                  {fusion.conflictingSignals.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {fusion.missingInputs.length > 0 ? (
              <>
                <strong>Missing Inputs</strong>
                <ul>
                  {fusion.missingInputs.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </>
        ) : null}
        {committee.summary || committee.members.length > 0 ? (
          <>
            <strong>Investment Committee</strong>
            <p>{formatValue(committee.summary)}</p>
            <ul>
              <li>Agreement: {formatValue(committee.agreement)}%</li>
              <li>
                Strongest bull: {formatValue(committee.strongestBull)}
              </li>
              <li>
                Strongest bear: {formatValue(committee.strongestBear)}
              </li>
              <li>
                Main disagreement: {formatValue(committee.mainDisagreement)}
              </li>
            </ul>
            {committee.bullishMembers.length > 0 ? (
              <p>Bullish members: {committee.bullishMembers.join(', ')}</p>
            ) : null}
            {committee.bearishMembers.length > 0 ? (
              <p>Bearish members: {committee.bearishMembers.join(', ')}</p>
            ) : null}
            {committee.neutralMembers.length > 0 ? (
              <p>Neutral or missing members: {committee.neutralMembers.join(', ')}</p>
            ) : null}
            {committee.members.length > 0 ? (
              <>
                <strong>Member Views</strong>
                <ul>
                  {committee.members.map((member) => (
                    <li key={member.member}>
                      {formatValue(member.member)}: {formatValue(member.stance)} | Confidence:{' '}
                      {formatValue(member.confidence)} | {formatValue(member.summary)}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
            {committee.bullCase.length > 0 ? (
              <>
                <strong>Committee Bull Case</strong>
                <ul>
                  {committee.bullCase.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {committee.bearCase.length > 0 ? (
              <>
                <strong>Committee Bear Case</strong>
                <ul>
                  {committee.bearCase.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            ) : null}
            {committee.neutralCase.length > 0 ? (
              <>
                <strong>Committee Neutral Case</strong>
                <ul>
                  {committee.neutralCase.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            ) : null}
          </>
        ) : null}
      </details>
    </article>
  )
}

export default RecommendationCard
