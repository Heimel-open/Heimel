export type FieldTruthStatus =
  | 'OBSERVED'
  | 'PRINCIPAL_ADJUDICATED'
  | 'INFERRED'
  | 'UNKNOWN'

export type EvidenceTiming = 'AT_DECISION' | 'POST_HOC_OUTCOME'

export type EvidenceField<T> = {
  value: T | null
  status: FieldTruthStatus
  sourceRef: string | null
  observedAt: string | null
  timing: EvidenceTiming
}

export type ExternalCapabilityRole =
  | 'FRAMEWORK_PROVIDER'
  | 'EVIDENCE_PROVIDER'
  | 'DOMAIN_EXPERT'
  | 'NONE'

export type HistoricalCapabilityContributor = {
  id: string
  role: ExternalCapabilityRole
  capabilities: readonly string[]
  ownership: string
  approvalStatus: 'ACCEPTED' | 'PENDING' | 'NOT_APPLICABLE'
  sourceRef: string
}

export type OrganizationalLeverageCase = {
  id: string
  occurredAt: string
  title: string
  decisionSourceRef: string
  requiredCapabilities: EvidenceField<readonly string[]>
  internalCapabilityAvailable: EvidenceField<boolean>
  externalCapabilityContributed: EvidenceField<boolean>
  principalContributionMaterial: EvidenceField<boolean>
  principalIrreducible: EvidenceField<boolean>
  discoveryHours: EvidenceField<number>
  usefulJudgmentLatencyHours: EvidenceField<number>
  temporaryCapabilityCost: EvidenceField<number>
  permanentAlternativeAnnualCost: EvidenceField<number>
  costCurrency: EvidenceField<string>
  externalExecutionAuthorityGranted: EvidenceField<boolean>
  contributors: readonly HistoricalCapabilityContributor[]
}

export type CandidateCapabilityRoute =
  | 'INTERNAL'
  | 'BOUNDED_EXTERNAL_CANDIDATE'
  | 'PRINCIPAL_REQUIRED'
  | 'UNKNOWN'

export type OrganizationalLeverageMetrics = {
  cases: number
  observedCapabilityRequirements: number
  observedInternalAvailabilityCases: number
  observedCapabilityGapCases: number
  observedExternalContributionCases: number
  observedHumanExpertContributionCases: number
  observedFrameworkOrEvidenceContributionCases: number
  observedPrincipalContributionCases: number
  adjudicatedPrincipalIrreducibleCases: number
  knownDiscoveryCases: number
  averageDiscoveryHours: number | null
  knownLatencyCases: number
  averageUsefulJudgmentLatencyHours: number | null
  roiEvidenceCompleteCases: number
  externalAuthorityViolations: number
  counterfactualRouteCounts: Readonly<Record<CandidateCapabilityRoute, number>>
}

const parseTime = (value: string): number => {
  const parsed = Date.parse(value)
  if (!Number.isFinite(parsed)) throw new Error(`invalid_timestamp:${value}`)
  return parsed
}

export const isGrounded = <T>(field: EvidenceField<T>): boolean =>
  field.status === 'OBSERVED' || field.status === 'PRINCIPAL_ADJUDICATED'

const assertFieldIntegrity = <T>(
  caseId: string,
  fieldName: string,
  field: EvidenceField<T>,
  occurredAt: string,
): void => {
  if (field.status === 'UNKNOWN') {
    if (field.value !== null) throw new Error(`unknown_field_has_value:${caseId}:${fieldName}`)
    return
  }

  if (field.value === null) throw new Error(`known_field_missing_value:${caseId}:${fieldName}`)
  if (!field.sourceRef || !field.observedAt) {
    throw new Error(`known_field_missing_evidence:${caseId}:${fieldName}`)
  }

  if (
    field.status === 'PRINCIPAL_ADJUDICATED' &&
    !field.sourceRef.startsWith('principal-adjudication:')
  ) {
    throw new Error(`invalid_principal_adjudication_source:${caseId}:${fieldName}`)
  }

  if (field.timing === 'AT_DECISION' && parseTime(field.observedAt) > parseTime(occurredAt)) {
    throw new Error(`post_decision_input_evidence:${caseId}:${fieldName}`)
  }
}

export function validateOrganizationalLeverageCase(
  historicalCase: OrganizationalLeverageCase,
): void {
  parseTime(historicalCase.occurredAt)

  const fields: readonly [string, EvidenceField<unknown>][] = [
    ['requiredCapabilities', historicalCase.requiredCapabilities],
    ['internalCapabilityAvailable', historicalCase.internalCapabilityAvailable],
    ['externalCapabilityContributed', historicalCase.externalCapabilityContributed],
    ['principalContributionMaterial', historicalCase.principalContributionMaterial],
    ['principalIrreducible', historicalCase.principalIrreducible],
    ['discoveryHours', historicalCase.discoveryHours],
    ['usefulJudgmentLatencyHours', historicalCase.usefulJudgmentLatencyHours],
    ['temporaryCapabilityCost', historicalCase.temporaryCapabilityCost],
    ['permanentAlternativeAnnualCost', historicalCase.permanentAlternativeAnnualCost],
    ['costCurrency', historicalCase.costCurrency],
    ['externalExecutionAuthorityGranted', historicalCase.externalExecutionAuthorityGranted],
  ]

  for (const [name, field] of fields) {
    assertFieldIntegrity(historicalCase.id, name, field, historicalCase.occurredAt)
  }

  for (const [name, field] of [
    ['discoveryHours', historicalCase.discoveryHours],
    ['usefulJudgmentLatencyHours', historicalCase.usefulJudgmentLatencyHours],
    ['temporaryCapabilityCost', historicalCase.temporaryCapabilityCost],
    ['permanentAlternativeAnnualCost', historicalCase.permanentAlternativeAnnualCost],
  ] as const) {
    if (isGrounded(field) && (field.value ?? 0) < 0) {
      throw new Error(`negative_${name}:${historicalCase.id}`)
    }
  }

  if (
    isGrounded(historicalCase.externalExecutionAuthorityGranted) &&
    historicalCase.externalExecutionAuthorityGranted.value === true
  ) {
    throw new Error(`external_capability_cannot_grant_execution_authority:${historicalCase.id}`)
  }
}

export function candidateCapabilityRoute(
  historicalCase: OrganizationalLeverageCase,
): CandidateCapabilityRoute {
  validateOrganizationalLeverageCase(historicalCase)

  if (
    isGrounded(historicalCase.principalIrreducible) &&
    historicalCase.principalIrreducible.value === true
  ) {
    return 'PRINCIPAL_REQUIRED'
  }

  if (isGrounded(historicalCase.internalCapabilityAvailable)) {
    if (historicalCase.internalCapabilityAvailable.value === true) return 'INTERNAL'
    if (
      historicalCase.internalCapabilityAvailable.value === false &&
      isGrounded(historicalCase.externalCapabilityContributed) &&
      historicalCase.externalCapabilityContributed.value === true
    ) {
      return 'BOUNDED_EXTERNAL_CANDIDATE'
    }
  }

  return 'UNKNOWN'
}

const groundedNumberAverage = (fields: readonly EvidenceField<number>[]): number | null => {
  const values = fields
    .filter(isGrounded)
    .map((field) => field.value)
    .filter((value): value is number => typeof value === 'number')

  if (values.length === 0) return null
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

const hasContributorRole = (
  historicalCase: OrganizationalLeverageCase,
  roles: readonly ExternalCapabilityRole[],
): boolean => historicalCase.contributors.some((contributor) => roles.includes(contributor.role))

export function scoreObservedOrganizationalLeverage(
  cases: readonly OrganizationalLeverageCase[],
): OrganizationalLeverageMetrics {
  for (const historicalCase of cases) validateOrganizationalLeverageCase(historicalCase)

  const routeCounts: Record<CandidateCapabilityRoute, number> = {
    INTERNAL: 0,
    BOUNDED_EXTERNAL_CANDIDATE: 0,
    PRINCIPAL_REQUIRED: 0,
    UNKNOWN: 0,
  }

  let observedCapabilityRequirements = 0
  let observedInternalAvailabilityCases = 0
  let observedCapabilityGapCases = 0
  let observedExternalContributionCases = 0
  let observedHumanExpertContributionCases = 0
  let observedFrameworkOrEvidenceContributionCases = 0
  let observedPrincipalContributionCases = 0
  let adjudicatedPrincipalIrreducibleCases = 0
  let roiEvidenceCompleteCases = 0
  let externalAuthorityViolations = 0

  for (const historicalCase of cases) {
    if (isGrounded(historicalCase.requiredCapabilities)) observedCapabilityRequirements += 1

    if (isGrounded(historicalCase.internalCapabilityAvailable)) {
      observedInternalAvailabilityCases += 1
      if (historicalCase.internalCapabilityAvailable.value === false) observedCapabilityGapCases += 1
    }

    const externalContributionObserved =
      isGrounded(historicalCase.externalCapabilityContributed) &&
      historicalCase.externalCapabilityContributed.value === true

    if (externalContributionObserved) {
      observedExternalContributionCases += 1
      if (hasContributorRole(historicalCase, ['DOMAIN_EXPERT'])) {
        observedHumanExpertContributionCases += 1
      }
      if (hasContributorRole(historicalCase, ['FRAMEWORK_PROVIDER', 'EVIDENCE_PROVIDER'])) {
        observedFrameworkOrEvidenceContributionCases += 1
      }
    }

    if (
      isGrounded(historicalCase.principalContributionMaterial) &&
      historicalCase.principalContributionMaterial.value === true
    ) {
      observedPrincipalContributionCases += 1
    }

    if (
      historicalCase.principalIrreducible.status === 'PRINCIPAL_ADJUDICATED' &&
      historicalCase.principalIrreducible.value === true
    ) {
      adjudicatedPrincipalIrreducibleCases += 1
    }

    if (
      isGrounded(historicalCase.externalExecutionAuthorityGranted) &&
      historicalCase.externalExecutionAuthorityGranted.value === true
    ) {
      externalAuthorityViolations += 1
    }

    if (
      isGrounded(historicalCase.requiredCapabilities) &&
      isGrounded(historicalCase.internalCapabilityAvailable) &&
      isGrounded(historicalCase.externalCapabilityContributed) &&
      isGrounded(historicalCase.discoveryHours) &&
      isGrounded(historicalCase.usefulJudgmentLatencyHours) &&
      isGrounded(historicalCase.temporaryCapabilityCost) &&
      isGrounded(historicalCase.permanentAlternativeAnnualCost) &&
      isGrounded(historicalCase.costCurrency)
    ) {
      roiEvidenceCompleteCases += 1
    }

    routeCounts[candidateCapabilityRoute(historicalCase)] += 1
  }

  const discoveryFields = cases.map((historicalCase) => historicalCase.discoveryHours)
  const latencyFields = cases.map((historicalCase) => historicalCase.usefulJudgmentLatencyHours)

  return {
    cases: cases.length,
    observedCapabilityRequirements,
    observedInternalAvailabilityCases,
    observedCapabilityGapCases,
    observedExternalContributionCases,
    observedHumanExpertContributionCases,
    observedFrameworkOrEvidenceContributionCases,
    observedPrincipalContributionCases,
    adjudicatedPrincipalIrreducibleCases,
    knownDiscoveryCases: discoveryFields.filter(isGrounded).length,
    averageDiscoveryHours: groundedNumberAverage(discoveryFields),
    knownLatencyCases: latencyFields.filter(isGrounded).length,
    averageUsefulJudgmentLatencyHours: groundedNumberAverage(latencyFields),
    roiEvidenceCompleteCases,
    externalAuthorityViolations,
    counterfactualRouteCounts: routeCounts,
  }
}

const unknown = <T>(): EvidenceField<T> => ({
  value: null,
  status: 'UNKNOWN',
  sourceRef: null,
  observedAt: null,
  timing: 'POST_HOC_OUTCOME',
})

const observedOutcome = <T>(
  value: T,
  sourceRef: string,
  observedAt: string,
): EvidenceField<T> => ({
  value,
  status: 'OBSERVED',
  sourceRef,
  observedAt,
  timing: 'POST_HOC_OUTCOME',
})

const inferredOutcome = <T>(
  value: T,
  sourceRef: string,
  observedAt: string,
): EvidenceField<T> => ({
  value,
  status: 'INFERRED',
  sourceRef,
  observedAt,
  timing: 'POST_HOC_OUTCOME',
})

const principalAdjudicated = <T>(
  value: T,
  adjudicationId: string,
  observedAt: string,
): EvidenceField<T> => ({
  value,
  status: 'PRINCIPAL_ADJUDICATED',
  sourceRef: `principal-adjudication:${adjudicationId}`,
  observedAt,
  timing: 'POST_HOC_OUTCOME',
})

const JASPER_SOURCE =
  'nsolland/valo-platform@152611328e91310aeb427c4ccca8aa588b4acb1f:docs/integrations/JASPER_CAUSAL_SUBSTRATE_ADAPTER_2026-08-10.md'
const WORKSPACE_SOURCE =
  'nsolland/valo-research-collaborations@de2c5873c3a2c5c54b9011d61b64d2d3569232f2:intersections/valo-2-governed-workspace/BOUNDARY_REVISION_V0_1.md'
const AUTHORITY_SOURCE =
  'nsolland/valo-platform@1b4ffaf03b1d05b19ca6cb547d04958c82e38375:.claims/authority-v02-runtime-bridge-20260815.md'
const ATTENTION_SOURCE =
  'nsolland/Valo-Twin@78c712c67d60bf93b8d29c5b3ceebc347ce10c4c:docs/human-attention-simulation.md'
const CAPABILITY_SOURCE =
  'nsolland/Valo-Twin@2b7415041b30c47a0806ee23c3600ef946eeaf56:docs/capability-on-demand-organization.md'

const inferredCapabilities = (
  value: readonly string[],
  sourceRef: string,
  observedAt: string,
): EvidenceField<readonly string[]> => inferredOutcome(value, sourceRef, observedAt)

const emptyEconomics = () => ({
  discoveryHours: unknown<number>(),
  usefulJudgmentLatencyHours: unknown<number>(),
  temporaryCapabilityCost: unknown<number>(),
  permanentAlternativeAnnualCost: unknown<number>(),
  costCurrency: unknown<string>(),
})

export const OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES: readonly OrganizationalLeverageCase[] = [
  {
    id: 'jasper-causal-continuity',
    occurredAt: '2026-08-10T19:11:43Z',
    title: 'Connect external causal-substrate evidence without transferring execution authority',
    decisionSourceRef: JASPER_SOURCE,
    requiredCapabilities: inferredCapabilities(
      ['causal_continuity', 'replay_integrity', 'execution_envelope_binding'],
      JASPER_SOURCE,
      '2026-08-10T19:11:43Z',
    ),
    internalCapabilityAvailable: unknown(),
    externalCapabilityContributed: observedOutcome(true, JASPER_SOURCE, '2026-08-10T19:11:43Z'),
    principalContributionMaterial: unknown(),
    principalIrreducible: unknown(),
    ...emptyEconomics(),
    externalExecutionAuthorityGranted: observedOutcome(false, JASPER_SOURCE, '2026-08-10T19:11:43Z'),
    contributors: [
      {
        id: 'jasper-causal-substrate',
        role: 'EVIDENCE_PROVIDER',
        capabilities: ['causal_continuity', 'replay_integrity'],
        ownership: 'external causal-substrate semantics remain optional implementation input',
        approvalStatus: 'NOT_APPLICABLE',
        sourceRef: JASPER_SOURCE,
      },
    ],
  },
  {
    id: 'governed-workspace-external-boundaries',
    occurredAt: '2026-08-12T11:27:55Z',
    title:
      'Bind external standing and authority frameworks into VALO Governed Workspace without making them core dependencies',
    decisionSourceRef: WORKSPACE_SOURCE,
    requiredCapabilities: inferredCapabilities(
      ['standing_admissibility', 'authority_state', 'governed_workspace_architecture'],
      WORKSPACE_SOURCE,
      '2026-08-12T11:27:55Z',
    ),
    internalCapabilityAvailable: unknown(),
    externalCapabilityContributed: observedOutcome(true, WORKSPACE_SOURCE, '2026-08-12T11:27:55Z'),
    principalContributionMaterial: unknown(),
    principalIrreducible: unknown(),
    ...emptyEconomics(),
    externalExecutionAuthorityGranted: observedOutcome(false, WORKSPACE_SOURCE, '2026-08-12T11:27:55Z'),
    contributors: [
      {
        id: 'margaret-stokes-aurora-lens',
        role: 'FRAMEWORK_PROVIDER',
        capabilities: ['standing_admissibility', 'evidence_admission', 'persistent_state'],
        ownership: 'Margaret Stokes retains Aurora-Lens and PEF-related pre-existing IP',
        approvalStatus: 'PENDING',
        sourceRef: WORKSPACE_SOURCE,
      },
      {
        id: 'elsa-authority-instrumentation',
        role: 'FRAMEWORK_PROVIDER',
        capabilities: ['authority_state', 'mandate_scope_revocation'],
        ownership: 'Elsa retains Authority Instrumentation pre-existing IP',
        approvalStatus: 'PENDING',
        sourceRef: WORKSPACE_SOURCE,
      },
    ],
  },
  {
    id: 'authority-state-v02-runtime-bridge',
    occurredAt: '2026-08-15T19:38:52Z',
    title: 'Consume external Authority State v0.2 as evidence while retaining fresh REHT authorization',
    decisionSourceRef: AUTHORITY_SOURCE,
    requiredCapabilities: inferredCapabilities(
      ['authority_state_resolution', 'runtime_bridge', 'authority_drift_detection'],
      AUTHORITY_SOURCE,
      '2026-08-15T19:38:52Z',
    ),
    internalCapabilityAvailable: unknown(),
    externalCapabilityContributed: observedOutcome(true, AUTHORITY_SOURCE, '2026-08-15T19:38:52Z'),
    principalContributionMaterial: unknown(),
    principalIrreducible: unknown(),
    ...emptyEconomics(),
    externalExecutionAuthorityGranted: observedOutcome(false, AUTHORITY_SOURCE, '2026-08-15T19:38:52Z'),
    contributors: [
      {
        id: 'authority-instrumentation-v02-producer-contract',
        role: 'FRAMEWORK_PROVIDER',
        capabilities: ['authority_state_resolution'],
        ownership:
          'external Authority Instrumentation producer contract; VALO owns its evidence-only bridge',
        approvalStatus: 'NOT_APPLICABLE',
        sourceRef: AUTHORITY_SOURCE,
      },
    ],
  },
  {
    id: 'human-attention-routing-aha',
    occurredAt: '2026-08-17T08:24:58Z',
    title: 'Route the right human attention at the right time',
    decisionSourceRef: ATTENTION_SOURCE,
    requiredCapabilities: inferredCapabilities(
      ['human_attention_design', 'principal_judgment_routing'],
      ATTENTION_SOURCE,
      '2026-08-17T08:32:32Z',
    ),
    internalCapabilityAvailable: unknown(),
    externalCapabilityContributed: unknown(),
    principalContributionMaterial: principalAdjudicated(
      true,
      '2026-08-17T08:24:58Z:material-contribution',
      '2026-08-17T08:24:58Z',
    ),
    principalIrreducible: unknown(),
    ...emptyEconomics(),
    externalExecutionAuthorityGranted: unknown(),
    contributors: [],
  },
  {
    id: 'capability-on-demand-organization-aha',
    occurredAt: '2026-08-17T08:43:41Z',
    title: 'Turn human-attention routing into capability-on-demand organization design',
    decisionSourceRef: CAPABILITY_SOURCE,
    requiredCapabilities: inferredCapabilities(
      ['organization_design', 'capability_routing', 'bounded_external_engagement'],
      CAPABILITY_SOURCE,
      '2026-08-17T08:47:34Z',
    ),
    internalCapabilityAvailable: unknown(),
    externalCapabilityContributed: unknown(),
    principalContributionMaterial: principalAdjudicated(
      true,
      '2026-08-17T08:43:41Z:material-contribution',
      '2026-08-17T08:43:41Z',
    ),
    principalIrreducible: unknown(),
    ...emptyEconomics(),
    externalExecutionAuthorityGranted: unknown(),
    contributors: [],
  },
] as const
