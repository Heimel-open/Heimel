export type CapabilityRequirement = {
  capability: string
  minProficiency: number
  maxAgeDays: number
}

export type CapabilityState = {
  capability: string
  proficiency: number
  lastVerifiedAt: string
  available: boolean
}

export type InternalMember = {
  id: string
  capabilities: readonly CapabilityState[]
}

export type ExpertCandidate = {
  id: string
  capabilities: readonly CapabilityState[]
  rating: number
  evidenceScore: number
  available: boolean
  hourlyRate: number
}

export type DecisionCase = {
  id: string
  scope: string
  requiredCapabilities: readonly CapabilityRequirement[]
  principalRequired: boolean
  estimatedHours: number
  dueAt: string
}

export type CapabilityGap = {
  capability: string
  minProficiency: number
  maxAgeDays: number
}

export type CaseAssessment = {
  route: 'INTERNAL' | 'EXTERNAL_REQUIRED' | 'PRINCIPAL_REQUIRED'
  gaps: readonly CapabilityGap[]
  internalOwners: Readonly<Record<string, string>>
}

export type RankedExpert = {
  expert: ExpertCandidate
  score: number
  coveredCapabilities: readonly string[]
}

export type EngagementProposal = {
  caseId: string
  expertId: string
  scope: string
  capabilities: readonly string[]
  startsAt: string
  expiresAt: string
  maxHours: number
  allowedOutputs: readonly ['ADVICE', 'ANALYSIS']
  workspace: 'BOUNDED_PROJECTION'
  authority: 'NONE'
}

export type EngagementValidation = {
  valid: boolean
  reasons: readonly string[]
}

export type CapabilitySimulation = {
  mode: 'FIXED_STAFF' | 'CAPABILITY_ON_DEMAND'
  cases: number
  permanentHeadcount: number
  internalCases: number
  externalCases: number
  principalCases: number
  unresolvedCases: number
  wrongExpertRoutes: number
  purchasedExpertHours: number
  effectiveCapabilityDomains: number
}

const DAY_MS = 24 * 60 * 60 * 1000

const asTime = (value: string): number => {
  const parsed = Date.parse(value)
  if (!Number.isFinite(parsed)) throw new Error(`invalid_timestamp:${value}`)
  return parsed
}

export function capabilityIsFresh(
  capability: CapabilityState,
  requirement: CapabilityRequirement,
  at: string,
): boolean {
  if (capability.capability !== requirement.capability) return false
  if (!capability.available) return false
  if (capability.proficiency < requirement.minProficiency) return false

  const ageDays = (asTime(at) - asTime(capability.lastVerifiedAt)) / DAY_MS
  return ageDays >= 0 && ageDays <= requirement.maxAgeDays
}

const bestInternalOwner = (
  requirement: CapabilityRequirement,
  members: readonly InternalMember[],
  at: string,
): InternalMember | undefined =>
  members
    .filter((member) =>
      member.capabilities.some((capability) => capabilityIsFresh(capability, requirement, at)),
    )
    .sort((left, right) => {
      const leftCapability = left.capabilities.find((item) => item.capability === requirement.capability)
      const rightCapability = right.capabilities.find((item) => item.capability === requirement.capability)
      return (rightCapability?.proficiency ?? 0) - (leftCapability?.proficiency ?? 0)
    })[0]

export function assessDecisionCase(
  decisionCase: DecisionCase,
  members: readonly InternalMember[],
  at: string,
): CaseAssessment {
  if (decisionCase.principalRequired) {
    return { route: 'PRINCIPAL_REQUIRED', gaps: [], internalOwners: {} }
  }

  const internalOwners: Record<string, string> = {}
  const gaps: CapabilityGap[] = []

  for (const requirement of decisionCase.requiredCapabilities) {
    const owner = bestInternalOwner(requirement, members, at)
    if (owner) {
      internalOwners[requirement.capability] = owner.id
    } else {
      gaps.push({ ...requirement })
    }
  }

  return {
    route: gaps.length === 0 ? 'INTERNAL' : 'EXTERNAL_REQUIRED',
    gaps,
    internalOwners,
  }
}

const expertCoverage = (
  expert: ExpertCandidate,
  gaps: readonly CapabilityGap[],
  at: string,
): readonly string[] =>
  gaps
    .filter((gap) =>
      expert.capabilities.some((capability) => capabilityIsFresh(capability, gap, at)),
    )
    .map((gap) => gap.capability)

export function rankExternalExperts(
  gaps: readonly CapabilityGap[],
  experts: readonly ExpertCandidate[],
  at: string,
): readonly RankedExpert[] {
  if (gaps.length === 0) return []

  return experts
    .filter((expert) => expert.available)
    .map((expert) => {
      const coveredCapabilities = expertCoverage(expert, gaps, at)
      const coverageRatio = coveredCapabilities.length / gaps.length

      // Capability fit dominates reputation. Rating can never compensate for a missing specialty.
      const score =
        coverageRatio * 0.7 +
        Math.max(0, Math.min(1, expert.evidenceScore)) * 0.2 +
        Math.max(0, Math.min(1, expert.rating / 5)) * 0.1

      return { expert, score, coveredCapabilities }
    })
    .filter((ranked) => ranked.coveredCapabilities.length === gaps.length)
    .sort((left, right) => right.score - left.score || left.expert.hourlyRate - right.expert.hourlyRate)
}

export function proposeBoundedEngagement(
  decisionCase: DecisionCase,
  gaps: readonly CapabilityGap[],
  expert: ExpertCandidate,
  startsAt: string,
): EngagementProposal {
  if (decisionCase.principalRequired) throw new Error('principal_required')
  if (gaps.length === 0) throw new Error('no_external_gap')

  const covered = expertCoverage(expert, gaps, startsAt)
  if (covered.length !== gaps.length) throw new Error('expert_does_not_cover_gap')

  const start = asTime(startsAt)
  const due = asTime(decisionCase.dueAt)
  if (start > due) throw new Error('case_already_due')

  const requestedEnd = start + Math.max(1, decisionCase.estimatedHours) * 60 * 60 * 1000
  const expiry = Math.min(requestedEnd, due)

  return {
    caseId: decisionCase.id,
    expertId: expert.id,
    scope: decisionCase.scope,
    capabilities: [...covered].sort(),
    startsAt: new Date(start).toISOString(),
    expiresAt: new Date(expiry).toISOString(),
    maxHours: decisionCase.estimatedHours,
    allowedOutputs: ['ADVICE', 'ANALYSIS'],
    workspace: 'BOUNDED_PROJECTION',
    authority: 'NONE',
  }
}

export function validateEngagement(
  proposal: EngagementProposal,
  decisionCase: DecisionCase,
  now: string,
): EngagementValidation {
  const reasons: string[] = []

  if (proposal.caseId !== decisionCase.id) reasons.push('case_mismatch')
  if (proposal.scope !== decisionCase.scope) reasons.push('scope_mismatch')
  if (proposal.workspace !== 'BOUNDED_PROJECTION') reasons.push('workspace_not_bounded')
  if (proposal.authority !== 'NONE') reasons.push('authority_inherited')
  if (proposal.maxHours > decisionCase.estimatedHours) reasons.push('hours_exceed_case')
  if (asTime(now) < asTime(proposal.startsAt)) reasons.push('not_started')
  if (asTime(now) >= asTime(proposal.expiresAt)) reasons.push('expired')

  return { valid: reasons.length === 0, reasons }
}

export function buildCapabilityOnDemandReferenceScenario() {
  const now = '2026-08-17T08:00:00.000Z'
  const fresh = '2026-08-10T08:00:00.000Z'

  const coreCapabilities = [
    'product',
    'architecture',
    'engineering',
    'operations',
    'commercial',
    'finance',
    'governance',
  ] as const

  const nicheCapabilities = [
    'competition_law',
    'medical_regulation',
    'power_market',
    'patent_law',
    'industrial_safety',
  ] as const

  const coreMembers: InternalMember[] = coreCapabilities.map((capability, index) => ({
    id: `core-${index + 1}`,
    capabilities: [
      { capability, proficiency: 0.92, lastVerifiedAt: fresh, available: true },
    ],
  }))

  const experts: ExpertCandidate[] = nicheCapabilities.map((capability, index) => ({
    id: `expert-${index + 1}`,
    capabilities: [
      { capability, proficiency: 0.96, lastVerifiedAt: fresh, available: true },
    ],
    rating: 4.7,
    evidenceScore: 0.95,
    available: true,
    hourlyRate: 250 + index * 25,
  }))

  const cases: DecisionCase[] = []

  for (let index = 0; index < 700; index += 1) {
    const capability = coreCapabilities[index % coreCapabilities.length]
    cases.push({
      id: `internal-${index}`,
      scope: `internal-case-${index}`,
      requiredCapabilities: [{ capability, minProficiency: 0.8, maxAgeDays: 30 }],
      principalRequired: false,
      estimatedHours: 2,
      dueAt: '2026-08-18T08:00:00.000Z',
    })
  }

  for (let index = 0; index < 250; index += 1) {
    const capability = nicheCapabilities[index % nicheCapabilities.length]
    cases.push({
      id: `external-${index}`,
      scope: `bounded-niche-case-${index}`,
      requiredCapabilities: [{ capability, minProficiency: 0.9, maxAgeDays: 30 }],
      principalRequired: false,
      estimatedHours: 3,
      dueAt: '2026-08-18T08:00:00.000Z',
    })
  }

  for (let index = 0; index < 50; index += 1) {
    cases.push({
      id: `principal-${index}`,
      scope: `new-normative-choice-${index}`,
      requiredCapabilities: [{ capability: 'governance', minProficiency: 0.8, maxAgeDays: 30 }],
      principalRequired: true,
      estimatedHours: 1,
      dueAt: '2026-08-18T08:00:00.000Z',
    })
  }

  return { now, coreMembers, experts, cases, coreCapabilities, nicheCapabilities }
}

export function simulateCapabilityOnDemand(): CapabilitySimulation {
  const scenario = buildCapabilityOnDemandReferenceScenario()
  let internalCases = 0
  let externalCases = 0
  let principalCases = 0
  let unresolvedCases = 0
  let wrongExpertRoutes = 0
  let purchasedExpertHours = 0
  const effectiveCapabilities = new Set<string>()

  for (const member of scenario.coreMembers) {
    for (const capability of member.capabilities) effectiveCapabilities.add(capability.capability)
  }

  for (const decisionCase of scenario.cases) {
    const assessment = assessDecisionCase(decisionCase, scenario.coreMembers, scenario.now)

    if (assessment.route === 'PRINCIPAL_REQUIRED') {
      principalCases += 1
      continue
    }

    if (assessment.route === 'INTERNAL') {
      internalCases += 1
      continue
    }

    const ranked = rankExternalExperts(assessment.gaps, scenario.experts, scenario.now)
    const selected = ranked[0]
    if (!selected) {
      unresolvedCases += 1
      continue
    }

    externalCases += 1
    purchasedExpertHours += decisionCase.estimatedHours
    for (const capability of selected.coveredCapabilities) effectiveCapabilities.add(capability)

    if (selected.coveredCapabilities.length !== assessment.gaps.length) wrongExpertRoutes += 1
  }

  return {
    mode: 'CAPABILITY_ON_DEMAND',
    cases: scenario.cases.length,
    permanentHeadcount: scenario.coreMembers.length,
    internalCases,
    externalCases,
    principalCases,
    unresolvedCases,
    wrongExpertRoutes,
    purchasedExpertHours,
    effectiveCapabilityDomains: effectiveCapabilities.size,
  }
}

export function simulateFixedStaffReference(): CapabilitySimulation {
  const scenario = buildCapabilityOnDemandReferenceScenario()
  const nicheMembers: InternalMember[] = scenario.nicheCapabilities.map((capability, index) => ({
    id: `fixed-niche-${index + 1}`,
    capabilities: [
      {
        capability,
        proficiency: 0.96,
        lastVerifiedAt: '2026-08-10T08:00:00.000Z',
        available: true,
      },
    ],
  }))

  const members = [...scenario.coreMembers, ...nicheMembers]
  let internalCases = 0
  let principalCases = 0
  let unresolvedCases = 0
  const effectiveCapabilities = new Set<string>()

  for (const member of members) {
    for (const capability of member.capabilities) effectiveCapabilities.add(capability.capability)
  }

  for (const decisionCase of scenario.cases) {
    const assessment = assessDecisionCase(decisionCase, members, scenario.now)
    if (assessment.route === 'PRINCIPAL_REQUIRED') principalCases += 1
    else if (assessment.route === 'INTERNAL') internalCases += 1
    else unresolvedCases += 1
  }

  return {
    mode: 'FIXED_STAFF',
    cases: scenario.cases.length,
    permanentHeadcount: members.length,
    internalCases,
    externalCases: 0,
    principalCases,
    unresolvedCases,
    wrongExpertRoutes: 0,
    purchasedExpertHours: 0,
    effectiveCapabilityDomains: effectiveCapabilities.size,
  }
}
