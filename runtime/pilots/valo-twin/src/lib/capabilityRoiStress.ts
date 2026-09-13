export type RoiStressScenario = {
  id: string
  annualCases: number
  fixedHeadcount: number
  coreHeadcount: number
  employeeAnnualCost: number
  expertHourlyRate: number
  externalCaseShare: number
  principalCaseShare: number
  expertHoursPerExternalCase: number
  discoveryHoursPerExternalCase: number
  expertAvailability: number
  staleCapabilityRate: number
  wrongRouteRate: number
  reworkHoursPerWrongRoute: number
  sourcingLatencyHours: number
  caseSlackHours: number
}

export type RoiFalsificationThresholds = {
  maxUnresolvedExternalRate: number
  maxWrongRouteRate: number
  maxDeadlineMissRate: number
  minExternalCapabilityCoverage: number
  maxPrincipalCaseShare: number
}

export type RoiStressResult = {
  scenarioId: string
  fixedAnnualCost: number
  elasticAnnualCost: number
  permanentCostAvoided: number
  externalSpend: number
  savings: number
  savingsRate: number
  roiOnExternalSpend: number
  breakEvenExpertHourlyRate: number
  breakEvenExternalCases: number
  externalCases: number
  resolvedExternalCases: number
  unresolvedExternalCases: number
  unresolvedExternalRate: number
  wrongRouteCases: number
  wrongRouteRate: number
  deadlineMissCases: number
  deadlineMissRate: number
  externalCapabilityCoverage: number
  purchasedExpertHours: number
  principalCases: number
  viable: boolean
  falsificationReasons: readonly string[]
}

export type StressGridReport = {
  scenarios: number
  viable: number
  falsified: number
  survivalRate: number
  reasonCounts: Readonly<Record<string, number>>
}

export const DEFAULT_ROI_THRESHOLDS: RoiFalsificationThresholds = {
  maxUnresolvedExternalRate: 0.02,
  maxWrongRouteRate: 0.02,
  maxDeadlineMissRate: 0.05,
  minExternalCapabilityCoverage: 0.95,
  maxPrincipalCaseShare: 0.25,
}

const clampRate = (value: number): number => Math.max(0, Math.min(1, value))

export function evaluateRoiScenario(
  scenario: RoiStressScenario,
  thresholds: RoiFalsificationThresholds = DEFAULT_ROI_THRESHOLDS,
): RoiStressResult {
  if (scenario.fixedHeadcount < scenario.coreHeadcount) throw new Error('core_exceeds_fixed_headcount')
  if (scenario.annualCases <= 0) throw new Error('annual_cases_must_be_positive')
  if (scenario.employeeAnnualCost < 0 || scenario.expertHourlyRate < 0) throw new Error('negative_cost')
  if (scenario.caseSlackHours < 0 || scenario.sourcingLatencyHours < 0) throw new Error('negative_time')

  const externalShare = clampRate(scenario.externalCaseShare)
  const principalShare = clampRate(scenario.principalCaseShare)
  if (externalShare + principalShare > 1) throw new Error('case_shares_exceed_one')

  const availability = clampRate(scenario.expertAvailability)
  const staleRate = clampRate(scenario.staleCapabilityRate)
  const usableExternalRate = availability * (1 - staleRate)

  const externalCases = scenario.annualCases * externalShare
  const principalCases = scenario.annualCases * principalShare
  const resolvedExternalCases = externalCases * usableExternalRate
  const unresolvedExternalCases = externalCases - resolvedExternalCases
  const unresolvedExternalRate = externalCases === 0 ? 0 : unresolvedExternalCases / externalCases
  const externalCapabilityCoverage = externalCases === 0 ? 1 : resolvedExternalCases / externalCases

  const wrongRouteRate = clampRate(scenario.wrongRouteRate)
  const wrongRouteCases = resolvedExternalCases * wrongRouteRate

  const deadlineMissRate =
    externalCases === 0 || scenario.sourcingLatencyHours <= scenario.caseSlackHours ? 0 : 1
  const deadlineMissCases = resolvedExternalCases * deadlineMissRate

  const baseExpertHours =
    resolvedExternalCases *
    Math.max(0, scenario.expertHoursPerExternalCase + scenario.discoveryHoursPerExternalCase)
  const reworkHours = wrongRouteCases * Math.max(0, scenario.reworkHoursPerWrongRoute)
  const purchasedExpertHours = baseExpertHours + reworkHours

  const fixedAnnualCost = scenario.fixedHeadcount * scenario.employeeAnnualCost
  const coreAnnualCost = scenario.coreHeadcount * scenario.employeeAnnualCost
  const permanentCostAvoided = fixedAnnualCost - coreAnnualCost
  const externalSpend = purchasedExpertHours * scenario.expertHourlyRate
  const elasticAnnualCost = coreAnnualCost + externalSpend
  const savings = fixedAnnualCost - elasticAnnualCost
  const savingsRate = fixedAnnualCost === 0 ? 0 : savings / fixedAnnualCost
  const roiOnExternalSpend = externalSpend === 0 ? Number.POSITIVE_INFINITY : savings / externalSpend
  const breakEvenExpertHourlyRate =
    purchasedExpertHours === 0 ? Number.POSITIVE_INFINITY : permanentCostAvoided / purchasedExpertHours

  const expectedHoursPerExternalCase =
    usableExternalRate *
    (Math.max(0, scenario.expertHoursPerExternalCase + scenario.discoveryHoursPerExternalCase) +
      wrongRouteRate * Math.max(0, scenario.reworkHoursPerWrongRoute))
  const breakEvenExternalCases =
    expectedHoursPerExternalCase === 0 || scenario.expertHourlyRate === 0
      ? Number.POSITIVE_INFINITY
      : permanentCostAvoided / (expectedHoursPerExternalCase * scenario.expertHourlyRate)

  const falsificationReasons: string[] = []
  if (savings <= 0) falsificationReasons.push('NO_COST_ADVANTAGE')
  if (unresolvedExternalRate > thresholds.maxUnresolvedExternalRate) {
    falsificationReasons.push('UNRESOLVED_CAPABILITY')
  }
  if (wrongRouteRate > thresholds.maxWrongRouteRate) {
    falsificationReasons.push('WRONG_EXPERT_ROUTING')
  }
  if (deadlineMissRate > thresholds.maxDeadlineMissRate) {
    falsificationReasons.push('SOURCING_LATENCY')
  }
  if (externalCapabilityCoverage < thresholds.minExternalCapabilityCoverage) {
    falsificationReasons.push('CAPABILITY_COVERAGE')
  }
  if (principalShare > thresholds.maxPrincipalCaseShare) {
    falsificationReasons.push('PRINCIPAL_BOTTLENECK')
  }

  return {
    scenarioId: scenario.id,
    fixedAnnualCost,
    elasticAnnualCost,
    permanentCostAvoided,
    externalSpend,
    savings,
    savingsRate,
    roiOnExternalSpend,
    breakEvenExpertHourlyRate,
    breakEvenExternalCases,
    externalCases,
    resolvedExternalCases,
    unresolvedExternalCases,
    unresolvedExternalRate,
    wrongRouteCases,
    wrongRouteRate,
    deadlineMissCases,
    deadlineMissRate,
    externalCapabilityCoverage,
    purchasedExpertHours,
    principalCases,
    viable: falsificationReasons.length === 0,
    falsificationReasons,
  }
}

export function referenceRoiScenario(): RoiStressScenario {
  return {
    id: 'reference',
    annualCases: 1000,
    fixedHeadcount: 12,
    coreHeadcount: 7,
    employeeAnnualCost: 2_000_000,
    expertHourlyRate: 2500,
    externalCaseShare: 0.25,
    principalCaseShare: 0.05,
    expertHoursPerExternalCase: 3,
    discoveryHoursPerExternalCase: 1,
    expertAvailability: 1,
    staleCapabilityRate: 0,
    wrongRouteRate: 0,
    reworkHoursPerWrongRoute: 3,
    sourcingLatencyHours: 2,
    caseSlackHours: 24,
  }
}

export function namedFalsificationScenarios(): readonly RoiStressScenario[] {
  const base = referenceRoiScenario()
  return [
    base,
    {
      ...base,
      id: 'economic-break',
      employeeAnnualCost: 1_000_000,
      expertHourlyRate: 8000,
      externalCaseShare: 0.6,
      discoveryHoursPerExternalCase: 8,
    },
    {
      ...base,
      id: 'capability-break',
      expertAvailability: 0.8,
      staleCapabilityRate: 0.1,
    },
    {
      ...base,
      id: 'routing-break',
      wrongRouteRate: 0.1,
    },
    {
      ...base,
      id: 'latency-break',
      sourcingLatencyHours: 36,
      caseSlackHours: 24,
    },
    {
      ...base,
      id: 'principal-break',
      principalCaseShare: 0.5,
      externalCaseShare: 0.2,
    },
  ]
}

export function buildFrozenStressGrid(): readonly RoiStressScenario[] {
  const scenarios: RoiStressScenario[] = []
  const employeeCosts = [1_000_000, 2_000_000, 3_000_000]
  const expertRates = [1000, 3000, 8000]
  const externalShares = [0.1, 0.3, 0.6]
  const discoveryHours = [0.5, 2, 8]
  const availabilities = [0.99, 0.95, 0.8]
  const wrongRouteRates = [0.005, 0.02, 0.1]
  const sourcingLatencies = [2, 12, 36]
  const principalShares = [0.05, 0.2, 0.5]

  let index = 0
  for (const employeeAnnualCost of employeeCosts) {
    for (const expertHourlyRate of expertRates) {
      for (const externalCaseShare of externalShares) {
        for (const discoveryHoursPerExternalCase of discoveryHours) {
          for (const expertAvailability of availabilities) {
            for (const wrongRouteRate of wrongRouteRates) {
              for (const sourcingLatencyHours of sourcingLatencies) {
                for (const principalCaseShare of principalShares) {
                  if (externalCaseShare + principalCaseShare > 1) continue
                  scenarios.push({
                    id: `grid-${index++}`,
                    annualCases: 1000,
                    fixedHeadcount: 12,
                    coreHeadcount: 7,
                    employeeAnnualCost,
                    expertHourlyRate,
                    externalCaseShare,
                    principalCaseShare,
                    expertHoursPerExternalCase: 3,
                    discoveryHoursPerExternalCase,
                    expertAvailability,
                    staleCapabilityRate: 0,
                    wrongRouteRate,
                    reworkHoursPerWrongRoute: 3,
                    sourcingLatencyHours,
                    caseSlackHours: 24,
                  })
                }
              }
            }
          }
        }
      }
    }
  }

  return scenarios
}

export function summarizeStressGrid(
  scenarios: readonly RoiStressScenario[] = buildFrozenStressGrid(),
): StressGridReport {
  const reasonCounts: Record<string, number> = {}
  let viable = 0

  for (const scenario of scenarios) {
    const result = evaluateRoiScenario(scenario)
    if (result.viable) viable += 1
    for (const reason of result.falsificationReasons) {
      reasonCounts[reason] = (reasonCounts[reason] ?? 0) + 1
    }
  }

  return {
    scenarios: scenarios.length,
    viable,
    falsified: scenarios.length - viable,
    survivalRate: scenarios.length === 0 ? 0 : viable / scenarios.length,
    reasonCounts,
  }
}
