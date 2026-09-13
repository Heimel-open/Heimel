import { describe, expect, it } from 'vitest'

import {
  buildFrozenStressGrid,
  evaluateRoiScenario,
  namedFalsificationScenarios,
  referenceRoiScenario,
  summarizeStressGrid,
} from './capabilityRoiStress'

describe('capability-on-demand ROI falsification', () => {
  it('keeps the reference economics explicit rather than hiding assumptions', () => {
    const result = evaluateRoiScenario(referenceRoiScenario())

    expect(result.viable).toBe(true)
    expect(result.fixedAnnualCost).toBe(24_000_000)
    expect(result.elasticAnnualCost).toBe(16_500_000)
    expect(result.permanentCostAvoided).toBe(10_000_000)
    expect(result.externalSpend).toBe(2_500_000)
    expect(result.savings).toBe(7_500_000)
    expect(result.savingsRate).toBeCloseTo(0.3125)
    expect(result.roiOnExternalSpend).toBeCloseTo(3)
    expect(result.purchasedExpertHours).toBe(1000)
    expect(result.breakEvenExpertHourlyRate).toBe(10_000)
    expect(result.breakEvenExternalCases).toBe(1000)
  })

  it('falsifies the thesis when external economics exceed permanent capability cost', () => {
    const scenario = namedFalsificationScenarios().find((item) => item.id === 'economic-break')!
    const result = evaluateRoiScenario(scenario)

    expect(result.viable).toBe(false)
    expect(result.savings).toBeLessThanOrEqual(0)
    expect(result.falsificationReasons).toContain('NO_COST_ADVANTAGE')
  })

  it('falsifies the thesis when capability availability and freshness collapse', () => {
    const scenario = namedFalsificationScenarios().find((item) => item.id === 'capability-break')!
    const result = evaluateRoiScenario(scenario)

    expect(result.viable).toBe(false)
    expect(result.externalCapabilityCoverage).toBeCloseTo(0.72)
    expect(result.falsificationReasons).toContain('UNRESOLVED_CAPABILITY')
    expect(result.falsificationReasons).toContain('CAPABILITY_COVERAGE')
  })

  it('falsifies the thesis when routing error is too high even if economics remain attractive', () => {
    const scenario = namedFalsificationScenarios().find((item) => item.id === 'routing-break')!
    const result = evaluateRoiScenario(scenario)

    expect(result.savings).toBeGreaterThan(0)
    expect(result.viable).toBe(false)
    expect(result.falsificationReasons).toContain('WRONG_EXPERT_ROUTING')
  })

  it('falsifies the thesis when sourcing arrives after the decision window', () => {
    const scenario = namedFalsificationScenarios().find((item) => item.id === 'latency-break')!
    const result = evaluateRoiScenario(scenario)

    expect(result.deadlineMissRate).toBe(1)
    expect(result.viable).toBe(false)
    expect(result.falsificationReasons).toContain('SOURCING_LATENCY')
  })

  it('falsifies the scaling claim when fresh principal judgement remains the dominant bottleneck', () => {
    const scenario = namedFalsificationScenarios().find((item) => item.id === 'principal-break')!
    const result = evaluateRoiScenario(scenario)

    expect(result.principalCases).toBe(500)
    expect(result.viable).toBe(false)
    expect(result.falsificationReasons).toContain('PRINCIPAL_BOTTLENECK')
  })

  it('runs a broad frozen grid that contains far more failures than successes', () => {
    const grid = buildFrozenStressGrid()
    const report = summarizeStressGrid(grid)

    expect(grid).toHaveLength(5832)
    expect(report.scenarios).toBe(5832)
    expect(report.viable).toBe(464)
    expect(report.falsified).toBe(5368)
    expect(report.survivalRate).toBeCloseTo(0.0795610425)
    expect(report.reasonCounts).toEqual({
      UNRESOLVED_CAPABILITY: 3888,
      WRONG_EXPERT_ROUTING: 1944,
      SOURCING_LATENCY: 1944,
      CAPABILITY_COVERAGE: 1944,
      PRINCIPAL_BOTTLENECK: 1458,
      NO_COST_ADVANTAGE: 1431,
    })
  })

  it('does not expose execution or authorization primitives', async () => {
    const module = await import('./capabilityRoiStress')
    expect('execute' in module).toBe(false)
    expect('authorize' in module).toBe(false)
  })
})
