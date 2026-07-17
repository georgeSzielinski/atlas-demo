import { describe, it, expect } from 'vitest'
import { greetingFor, executiveBriefing } from '../executiveBriefing'
import { dashboardV2 } from './fixtures'

// Fixed reference time (morning of 2026-07-14) so date-relative fields are
// deterministic. cycleCountdown uses the real clock, so countdown VALUES are
// never asserted — only presence/absence, which is what the design promises.
const MORNING = new Date(2026, 6, 14, 9, 0, 0)

describe('executiveBriefing — greetingFor', () => {
  it('greets by time of day', () => {
    expect(greetingFor(new Date(2026, 6, 14, 9))).toBe('Good morning')
    expect(greetingFor(new Date(2026, 6, 14, 14))).toBe('Good afternoon')
    expect(greetingFor(new Date(2026, 6, 14, 20))).toBe('Good evening')
  })
})

describe('executiveBriefing — header & portfolio', () => {
  const briefing = executiveBriefing(dashboardV2(), MORNING)

  it('builds a paper-only header', () => {
    expect(briefing.header.greeting).toBe('Good morning')
    expect(briefing.header.mode).toBe('AUTONOMOUS_PAPER')
    expect(briefing.header.paperOnly).toBe(true)
    expect(briefing.header.lastRefresh).toBe('2026-07-14T15:30:05')
  })

  it('summarizes a populated portfolio and marks it updated today', () => {
    expect(briefing.portfolio.available).toBe(true)
    expect(briefing.portfolio.portfolioValue).toBe(20000)
    expect(briefing.portfolio.realizedPl).toBe(250)
    expect(briefing.portfolio.unrealizedPl).toBe(800)
    expect(briefing.portfolio.dailyReturn).toBe(1.2)
    expect(briefing.portfolio.openPositions).toBe(2)
    expect(briefing.portfolio.updatedToday).toBe(true)
  })

  it('handles an empty portfolio honestly', () => {
    const briefing = executiveBriefing({ operations: {} }, MORNING)
    expect(briefing.portfolio.available).toBe(false)
    expect(briefing.portfolio.portfolioValue).toBeNull()
  })
})

describe('executiveBriefing — market & research', () => {
  it('reports market open and BUY/HOLD/AVOID counts', () => {
    const briefing = executiveBriefing(dashboardV2(), MORNING)
    expect(briefing.market.marketOpen).toBe(true)
    expect(briefing.market.session).toBe('Open')
    expect(briefing.research.buy).toBe(1)
    expect(briefing.research.hold).toBe(1)
    expect(briefing.research.avoid).toBe(1)
    expect(briefing.research.recommendationCount).toBe(3)
  })

  it('reports market closed / unavailable honestly', () => {
    const closed = dashboardV2()
    closed.market.market_is_open = false
    expect(executiveBriefing(closed, MORNING).market.marketOpen).toBe(false)
    const noStatus = dashboardV2()
    noStatus.market.status = 'Unavailable'
    expect(executiveBriefing(noStatus, MORNING).market.marketOpen).toBeNull()
  })

  it('surfaces a countdown only when a parseable next-cycle timestamp exists', () => {
    const withCycle = executiveBriefing(dashboardV2(), MORNING)
    expect(typeof withCycle.market.countdownLabel).toBe('string')

    const noCycle = dashboardV2()
    noCycle.paper_fund.next_update = null
    expect(executiveBriefing(noCycle, MORNING).market.countdownLabel).toBeNull()

    const badCycle = dashboardV2()
    badCycle.paper_fund.next_update = 'not-a-timestamp'
    expect(executiveBriefing(badCycle, MORNING).market.countdownLabel).toBeNull()
  })
})

describe('executiveBriefing — learning & reliability', () => {
  it('reads reliability grade and limited confidence history', () => {
    const limited = dashboardV2()
    limited.reliability.confidence.history_available = false
    const briefing = executiveBriefing(limited, MORNING)
    expect(briefing.learning.reliabilityGrade).toBe('A')
    expect(briefing.learning.reliabilityScore).toBe(92)
    expect(briefing.learning.historyAvailable).toBe(false)
    expect(briefing.learning.warningCount).toBe(1)
    expect(briefing.learning.errorCount).toBe(0)
  })
})

describe('executiveBriefing — important events', () => {
  it('orders events by priority and shows the paper fill first here', () => {
    const events = executiveBriefing(dashboardV2(), MORNING).events
    const priorities = events.map((e) => e.priority)
    expect([...priorities]).toEqual([...priorities].sort((a, b) => a - b))
    expect(events[0].priority).toBe(3)
    expect(events[0].title).toBe('Paper BUY 10 AAPL')
  })

  it('ranks a critical error first and de-duplicates repeated keys', () => {
    const data = dashboardV2()
    data.operations.recent_errors = ['Disk full', 'Disk full'] // same key → dedup
    data.scheduler = { status: 'EVALUATED', running: false, enabled: true, error_count: 2, last_error_at: '2026-07-14T14:00:00', last_reason: 'provider timeout' }
    const events = executiveBriefing(data, MORNING).events
    expect(events[0]).toMatchObject({ priority: 1, title: 'Critical error' })
    expect(events.filter((e) => e.title === 'Critical error')).toHaveLength(1)
    expect(events.some((e) => e.title === 'Scheduler error')).toBe(true)
  })

  it('flags an unhealthy provider and a fallback separately', () => {
    const down = dashboardV2()
    down.market = { status: 'EVALUATED', healthy: false, active_provider: 'yahoo', last_error: '429 rate limited' }
    expect(executiveBriefing(down, MORNING).events.some((e) => e.title === 'Market provider unhealthy')).toBe(true)

    const fell = dashboardV2()
    fell.market = { status: 'EVALUATED', healthy: true, fallback_used: true, active_provider: 'stooq' }
    expect(executiveBriefing(fell, MORNING).events.some((e) => e.title === 'Market provider fell back')).toBe(true)
  })

  it('does not treat a routine market-closed skip as an event', () => {
    const data = {
      operations: {},
      paper_fund: {
        activity_log: [{ activity_type: 'ANALYTICS_UPDATED', message: 'Market is closed, skipping cycle', at: '2026-07-14T02:00:00' }],
      },
    }
    expect(executiveBriefing(data, MORNING).events).toEqual([])
  })
})

describe('executiveBriefing — null/partial payloads', () => {
  it('never throws and degrades to unavailable', () => {
    expect(() => executiveBriefing(null, MORNING)).not.toThrow()
    const briefing = executiveBriefing(null, MORNING)
    expect(briefing.header.greeting).toBe('Good morning')
    expect(briefing.portfolio.available).toBe(false)
    expect(briefing.events).toEqual([])
  })
})
