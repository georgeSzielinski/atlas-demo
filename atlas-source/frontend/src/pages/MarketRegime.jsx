import { useEffect, useState } from 'react'
import Panel from '../components/ui/Panel'
import StatTile from '../components/ui/StatTile'
import StatusPill from '../components/ui/StatusPill'
import { LoadingState, ErrorState, EmptyState } from '../components/ui/States'
import { getMarketRegime } from '../services/api'
import { asArray, formatNumber, sectionReason } from '../services/formatters'

function num(value, suffix = '') {
  const formatted = formatNumber(value, { fallback: '—' })
  return formatted === '—' ? formatted : `${formatted}${suffix}`
}

function RegimeAxis({ eyebrow, section }) {
  const evaluated = section?.status === 'EVALUATED'
  return (
    <div className="mr-axis">
      <p className="dv2-heading__eyebrow">{eyebrow}</p>
      <div className="mr-axis__label">{evaluated ? section.label : 'NOT_EVALUATED'}</div>
      <p className="mr-axis__reason">{section?.reason ?? sectionReason(section)}</p>
    </div>
  )
}

function MarketRegime() {
  const [report, setReport] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrent = true
    async function load() {
      setIsLoading(true)
      try {
        const data = await getMarketRegime()
        if (!isCurrent) return
        setReport(data)
        setError('')
      } catch (requestError) {
        if (!isCurrent) return
        setError(requestError.message)
        setReport(null)
      } finally {
        if (isCurrent) setIsLoading(false)
      }
    }
    load()
    return () => {
      isCurrent = false
    }
  }, [])

  if (isLoading && !report) {
    return <LoadingState label="Loading market regime…" />
  }
  if (error && !report) {
    return <ErrorState message={error} />
  }

  const spy = report?.metrics?.spy ?? {}
  const vix = report?.metrics?.vix ?? {}
  const signals = asArray(report?.signals)
  const notEvaluated = report?.status !== 'EVALUATED'

  return (
    <div className="dv2-page pl-page">
      <section className="pl-hero">
        <div>
          <p className="dv2-heading__eyebrow">Market Regime</p>
          <h2>{report?.headline ?? 'NOT_EVALUATED'}</h2>
          <p className="pl-hero__sub">
            Deterministic, read-only classification of the current market environment from SPY, QQQ,
            and VIX. Descriptive only — it does not change trading, recommendation, or paper-fund
            behavior.
          </p>
        </div>
        <div className="pl-hero__badges">
          <StatusPill status={report?.status ?? 'NOT_EVALUATED'} />
          <StatusPill status="EVALUATED" label="READ-ONLY" />
          <StatusPill status="EVALUATED" label="DETERMINISTIC" />
        </div>
      </section>

      {notEvaluated ? (
        <Panel eyebrow="Regime" title="Current Regime">
          <EmptyState title="Not evaluated" message={sectionReason(report)} />
        </Panel>
      ) : (
        <Panel eyebrow="Regime" title="Current Regime" action={<StatusPill status="EVALUATED" />}>
          <div className="dv2-row dv2-row--3">
            <RegimeAxis eyebrow="Trend" section={report?.trend_regime} />
            <RegimeAxis eyebrow="Volatility" section={report?.volatility_regime} />
            <RegimeAxis eyebrow="Risk Posture" section={report?.risk_posture} />
          </div>
        </Panel>
      )}

      <Panel eyebrow="SPY" title="Supporting Metrics" action={<StatusPill status={spy.status ?? 'NOT_EVALUATED'} />}>
        <div className="pl-stats pl-stats--wide">
          <StatTile label="SPY Close" value={num(spy.close)} hint={spy.as_of ?? undefined} />
          <StatTile label="50-day MA" value={num(spy.ma_50)} />
          <StatTile label="200-day MA" value={num(spy.ma_200)} />
          <StatTile
            label="Price vs 200MA"
            value={num(spy.price_vs_200ma_pct, '%')}
            deltaTone={Number(spy.price_vs_200ma_pct) >= 0 ? 'positive' : 'negative'}
          />
          <StatTile label="1-Month Return" value={num(spy.return_1m_pct, '%')} />
          <StatTile label="3-Month Return" value={num(spy.return_3m_pct, '%')} />
          <StatTile label="Realized Vol (ann.)" value={num(spy.realized_vol_annualized_pct, '%')} />
          <StatTile
            label="VIX"
            value={vix.status === 'EVALUATED' ? num(vix.level) : 'N/E'}
            badge={<StatusPill status={vix.status === 'EVALUATED' ? 'EVALUATED' : 'NOT_EVALUATED'} label={vix.status === 'EVALUATED' ? 'live' : 'N/A'} />}
          />
        </div>
      </Panel>

      {signals.length > 0 ? (
        <Panel eyebrow="Signals" title="Risk-On / Risk-Off Signals">
          <div className="dv2-table-wrap">
            <table className="dv2-table">
              <thead>
                <tr>
                  <th>Signal</th>
                  <th>Value</th>
                  <th>Interpretation</th>
                </tr>
              </thead>
              <tbody>
                {signals.map((row) => (
                  <tr key={row.signal}>
                    <td>{row.signal}</td>
                    <td>{String(row.value)}</td>
                    <td>{row.interpretation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}
    </div>
  )
}

export default MarketRegime
