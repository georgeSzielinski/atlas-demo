import { describe, it, expect } from 'vitest'
import { buildReportModel, voteTone } from '../institutionalReport'
import { institutionalReportPayload, reportCard } from './fixtures'

describe('institutionalReport — buildReportModel (populated)', () => {
  const model = buildReportModel(institutionalReportPayload(), reportCard())

  it('builds the header from the clicked card, enriched by the report', () => {
    expect(model.ticker).toBe('AAPL')
    expect(model.hasRecommendation).toBe(true)
    expect(model.header).toMatchObject({ ticker: 'AAPL', action: 'BUY', confidence: 0.88, agreementPct: 90, strength: 'Strong' })
    expect(model.header.generatedAt).toBe('2026-07-14T09:05:00')
  })

  it('maps executive summary and investment thesis', () => {
    expect(model.executiveSummary).toEqual({ summary: 'AAPL shows durable momentum.', secFilings: 3 })
    expect(model.thesis).toMatchObject({ rating: 'Strong Buy', overallScore: 82, validationStatus: 'VALIDATED', signalLabel: 'STRONG', signalQuality: 74 })
    expect(model.thesis.evidence).toEqual(['Technical: 40%', 'Fundamental: 35%'])
  })

  it('maps bull/bear/catalyst/risk sections', () => {
    expect(model.bullCase).toEqual(['Services margin expansion', 'Buybacks'])
    expect(model.bearCase).toEqual(['Hardware cyclicality'])
    expect(model.catalysts).toEqual([{ title: 'Earnings', date: '2026-07-31' }])
    expect(model.risks).toEqual({ score: 35, items: ['Valuation stretched'], falsePositives: [] })
  })

  it('maps technical and fundamental evidence', () => {
    expect(model.technical).toEqual({ technicalScore: 70, score: 66, forecastDirection: 'UP', forecastConfidence: 60, expectedChange: 4.2 })
    expect(model.fundamental).toMatchObject({ fundamentalScore: 71, filingCount: 3, secProvider: 'edgar', sectionCoverage: ['MD&A', 'Risk Factors'] })
  })

  it('maps committee member votes', () => {
    expect(model.committee.agreement).toBe(90)
    expect(model.committee.members).toEqual([
      { name: 'Growth Analyst', vote: 'Bullish' },
      { name: 'Momentum Analyst', vote: 'Bullish' },
      { name: 'Value Analyst', vote: 'Bearish' },
    ])
  })

  it('exposes audit provenance without fabricating it', () => {
    expect(model.audit).toMatchObject({
      generatedAt: '2026-07-14T09:05:00',
      reportVersion: 'ir-v1',
      dataSources: ['market', 'sec', 'committee'],
      activeProviders: ['yahoo', 'edgar'],
      secProvider: 'edgar',
    })
    expect(model.audit.policy).toEqual({ deterministic: true, uses_llm: false, read_only: true })
  })
})

describe('institutionalReport — honest not-evaluated states', () => {
  it("folds engine defaults ('', 0, 'Unavailable') into null, not fake values", () => {
    const model = buildReportModel(institutionalReportPayload(), reportCard())
    // Portfolio Impact section was left at engine defaults (0 / 'Unavailable').
    expect(model.construction.portfolioScore).toBeNull()
    expect(model.construction.overallConviction).toBeNull()
    expect(model.construction.summary).toBeNull()
  })

  it('degrades a fully missing report (no card) to an empty, honest model', () => {
    const model = buildReportModel(null, null)
    expect(model.ticker).toBeNull()
    expect(model.hasRecommendation).toBe(false)
    expect(model.header.action).toBeNull()
    expect(model.executiveSummary.summary).toBeNull()
    expect(model.bullCase).toEqual([])
    expect(model.committee.members).toEqual([])
  })

  it('carries an exact card recommendation id only when one is provided', () => {
    const model = buildReportModel(institutionalReportPayload(), reportCard())
    expect(model.recommendationId).toBeNull()
    expect(buildReportModel(institutionalReportPayload(), {
      ...reportCard(),
      recommendationId: 42,
    }).recommendationId).toBe(42)
    expect('execution' in model).toBe(false)
    expect('positionSizing' in model).toBe(false)
    // construction carries only real, gated scores — nothing invented.
    expect(Object.keys(model.construction).sort()).toEqual(['overallConviction', 'portfolioScore', 'summary'])
  })
})

describe('institutionalReport — voteTone', () => {
  it('maps committee votes to tones', () => {
    expect(voteTone('Bullish')).toBe('positive')
    expect(voteTone('Bearish')).toBe('negative')
    expect(voteTone('Neutral')).toBe('neutral')
    expect(voteTone(null)).toBe('neutral')
  })
})
