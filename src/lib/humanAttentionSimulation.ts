export type AttentionClass = 'AUTONOMOUS' | 'HUMAN_REQUIRED' | 'PRINCIPAL_REQUIRED'

export type AttentionRole = 'NONE' | 'REVIEWER' | 'DOMAIN_EXPERT' | 'PRINCIPAL'

export type AttentionSignal = {
  class: AttentionClass
  role: AttentionRole
  confidence: number
  novelty: boolean
  continuityUncertain: boolean
  authorityUncertain: boolean
}

export type WorkItem = {
  id: string
  truth: {
    class: AttentionClass
    role: AttentionRole
  }
  signal: AttentionSignal
  triageMinutes: number
  decisionMinutes: number
}

export type SimulationMetrics = {
  mode: 'STATIC_HITL' | 'ATTENTION_ROUTED'
  items: number
  humanTouches: number
  humanMinutes: number
  unnecessaryHumanTouches: number
  missedRequiredAttention: number
  wrongRoleRoutes: number
  principalInterruptions: number
  autonomousCompletions: number
  directHumanRoutes: number
}

export type SimulationComparison = {
  humanMinutesSaved: number
  humanTouchesAvoided: number
  humanMinuteReductionRate: number
  humanTouchReductionRate: number
  attentionAmplification: number
  touchReductionFactor: number
}

const isHumanRequired = (attentionClass: AttentionClass) => attentionClass !== 'AUTONOMOUS'

const routedRole = (signal: AttentionSignal): AttentionRole => {
  if (signal.role !== 'NONE') return signal.role
  return 'REVIEWER'
}

export function simulateStaticHumanInLoop(items: readonly WorkItem[]): SimulationMetrics {
  let humanTouches = 0
  let humanMinutes = 0
  let unnecessaryHumanTouches = 0
  let principalInterruptions = 0
  let directHumanRoutes = 0

  for (const item of items) {
    humanTouches += 1
    humanMinutes += item.triageMinutes

    if (!isHumanRequired(item.truth.class)) {
      unnecessaryHumanTouches += 1
      continue
    }

    humanTouches += 1
    humanMinutes += item.decisionMinutes
    directHumanRoutes += 1
    if (item.truth.role === 'PRINCIPAL') principalInterruptions += 1
  }

  return {
    mode: 'STATIC_HITL',
    items: items.length,
    humanTouches,
    humanMinutes,
    unnecessaryHumanTouches,
    missedRequiredAttention: 0,
    wrongRoleRoutes: 0,
    principalInterruptions,
    autonomousCompletions: 0,
    directHumanRoutes,
  }
}

export function simulateAttentionRouted(
  items: readonly WorkItem[],
  autonomousConfidenceThreshold = 0.95,
): SimulationMetrics {
  let humanTouches = 0
  let humanMinutes = 0
  let unnecessaryHumanTouches = 0
  let missedRequiredAttention = 0
  let wrongRoleRoutes = 0
  let principalInterruptions = 0
  let autonomousCompletions = 0
  let directHumanRoutes = 0

  for (const item of items) {
    const signal = item.signal
    const mustRoute =
      signal.class !== 'AUTONOMOUS' ||
      signal.confidence < autonomousConfidenceThreshold ||
      signal.novelty ||
      signal.continuityUncertain ||
      signal.authorityUncertain

    if (!mustRoute) {
      autonomousCompletions += 1
      if (isHumanRequired(item.truth.class)) missedRequiredAttention += 1
      continue
    }

    humanTouches += 1
    humanMinutes += item.decisionMinutes
    directHumanRoutes += 1

    const role = routedRole(signal)
    if (!isHumanRequired(item.truth.class)) {
      unnecessaryHumanTouches += 1
      continue
    }

    if (role !== item.truth.role) wrongRoleRoutes += 1
    if (role === 'PRINCIPAL') principalInterruptions += 1
  }

  return {
    mode: 'ATTENTION_ROUTED',
    items: items.length,
    humanTouches,
    humanMinutes,
    unnecessaryHumanTouches,
    missedRequiredAttention,
    wrongRoleRoutes,
    principalInterruptions,
    autonomousCompletions,
    directHumanRoutes,
  }
}

export function compareAttentionModes(
  staticMode: SimulationMetrics,
  routedMode: SimulationMetrics,
): SimulationComparison {
  const humanMinutesSaved = staticMode.humanMinutes - routedMode.humanMinutes
  const humanTouchesAvoided = staticMode.humanTouches - routedMode.humanTouches

  return {
    humanMinutesSaved,
    humanTouchesAvoided,
    humanMinuteReductionRate:
      staticMode.humanMinutes === 0 ? 0 : humanMinutesSaved / staticMode.humanMinutes,
    humanTouchReductionRate:
      staticMode.humanTouches === 0 ? 0 : humanTouchesAvoided / staticMode.humanTouches,
    attentionAmplification:
      routedMode.humanMinutes === 0 ? Number.POSITIVE_INFINITY : staticMode.humanMinutes / routedMode.humanMinutes,
    touchReductionFactor:
      routedMode.humanTouches === 0 ? Number.POSITIVE_INFINITY : staticMode.humanTouches / routedMode.humanTouches,
  }
}

export function buildReferenceAttentionScenario(): readonly WorkItem[] {
  const items: WorkItem[] = []

  for (let index = 0; index < 9000; index += 1) {
    items.push({
      id: `auto-${index}`,
      truth: { class: 'AUTONOMOUS', role: 'NONE' },
      signal: {
        class: 'AUTONOMOUS',
        role: 'NONE',
        confidence: 0.99,
        novelty: false,
        continuityUncertain: false,
        authorityUncertain: false,
      },
      triageMinutes: 3,
      decisionMinutes: 3,
    })
  }

  for (let index = 0; index < 700; index += 1) {
    items.push({
      id: `domain-${index}`,
      truth: { class: 'HUMAN_REQUIRED', role: 'DOMAIN_EXPERT' },
      signal: {
        class: 'HUMAN_REQUIRED',
        role: 'DOMAIN_EXPERT',
        confidence: 0.92,
        novelty: false,
        continuityUncertain: false,
        authorityUncertain: false,
      },
      triageMinutes: 3,
      decisionMinutes: 8,
    })
  }

  for (let index = 0; index < 200; index += 1) {
    items.push({
      id: `principal-${index}`,
      truth: { class: 'PRINCIPAL_REQUIRED', role: 'PRINCIPAL' },
      signal: {
        class: 'PRINCIPAL_REQUIRED',
        role: 'PRINCIPAL',
        confidence: 0.9,
        novelty: true,
        continuityUncertain: false,
        authorityUncertain: true,
      },
      triageMinutes: 3,
      decisionMinutes: 15,
    })
  }

  for (let index = 0; index < 100; index += 1) {
    items.push({
      id: `uncertain-${index}`,
      truth: { class: 'HUMAN_REQUIRED', role: 'REVIEWER' },
      signal: {
        class: 'AUTONOMOUS',
        role: 'REVIEWER',
        confidence: 0.7,
        novelty: true,
        continuityUncertain: true,
        authorityUncertain: false,
      },
      triageMinutes: 3,
      decisionMinutes: 10,
    })
  }

  return items
}
