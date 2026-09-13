import { describe, expect, it } from 'vitest'
import {
  buildReferenceAttentionScenario,
  compareAttentionModes,
  simulateAttentionRouted,
  simulateStaticHumanInLoop,
  type WorkItem,
} from './humanAttentionSimulation'

describe('human attention simulation', () => {
  it('compares static human-in-the-loop with direct attention routing', () => {
    const items = buildReferenceAttentionScenario()
    const staticMode = simulateStaticHumanInLoop(items)
    const routedMode = simulateAttentionRouted(items)
    const comparison = compareAttentionModes(staticMode, routedMode)

    expect(items).toHaveLength(10_000)

    expect(staticMode.humanTouches).toBe(11_000)
    expect(staticMode.humanMinutes).toBe(39_600)
    expect(staticMode.unnecessaryHumanTouches).toBe(9_000)

    expect(routedMode.humanTouches).toBe(1_000)
    expect(routedMode.humanMinutes).toBe(9_600)
    expect(routedMode.autonomousCompletions).toBe(9_000)
    expect(routedMode.unnecessaryHumanTouches).toBe(0)
    expect(routedMode.missedRequiredAttention).toBe(0)
    expect(routedMode.wrongRoleRoutes).toBe(0)
    expect(routedMode.principalInterruptions).toBe(200)

    expect(comparison.humanMinutesSaved).toBe(30_000)
    expect(comparison.humanTouchesAvoided).toBe(10_000)
    expect(comparison.attentionAmplification).toBe(4.125)
    expect(comparison.touchReductionFactor).toBe(11)
    expect(comparison.humanMinuteReductionRate).toBeCloseTo(0.7575757576)
    expect(comparison.humanTouchReductionRate).toBeCloseTo(0.9090909091)
  })

  it('routes uncertainty to a human even when the classifier says autonomous', () => {
    const uncertain = buildReferenceAttentionScenario().find((item) => item.id === 'uncertain-0')
    expect(uncertain).toBeDefined()

    const result = simulateAttentionRouted(uncertain ? [uncertain] : [])

    expect(result.humanTouches).toBe(1)
    expect(result.autonomousCompletions).toBe(0)
    expect(result.missedRequiredAttention).toBe(0)
  })

  it('exposes a missed-attention failure when confidence is wrong and no guard fires', () => {
    const falseAutonomy: WorkItem = {
      id: 'false-autonomy',
      truth: { class: 'HUMAN_REQUIRED', role: 'DOMAIN_EXPERT' },
      signal: {
        class: 'AUTONOMOUS',
        role: 'NONE',
        confidence: 0.99,
        novelty: false,
        continuityUncertain: false,
        authorityUncertain: false,
      },
      triageMinutes: 3,
      decisionMinutes: 8,
    }

    const result = simulateAttentionRouted([falseAutonomy])

    expect(result.autonomousCompletions).toBe(1)
    expect(result.missedRequiredAttention).toBe(1)
  })

  it('detects routing to the wrong human role', () => {
    const wrongRole: WorkItem = {
      id: 'wrong-role',
      truth: { class: 'PRINCIPAL_REQUIRED', role: 'PRINCIPAL' },
      signal: {
        class: 'HUMAN_REQUIRED',
        role: 'DOMAIN_EXPERT',
        confidence: 0.98,
        novelty: true,
        continuityUncertain: false,
        authorityUncertain: true,
      },
      triageMinutes: 3,
      decisionMinutes: 15,
    }

    const result = simulateAttentionRouted([wrongRole])

    expect(result.humanTouches).toBe(1)
    expect(result.wrongRoleRoutes).toBe(1)
    expect(result.principalInterruptions).toBe(0)
  })
})
