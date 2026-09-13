import { describe, expect, it } from 'vitest'

import {
  OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES,
  candidateCapabilityRoute,
  scoreObservedOrganizationalLeverage,
  validateOrganizationalLeverageCase,
  type EvidenceField,
  type OrganizationalLeverageCase,
} from './organizationalLeverageReplay'

const cloneCase = (index = 0): OrganizationalLeverageCase =>
  structuredClone(OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES[index])

const observed = <T>(value: T, sourceRef = 'test:observed'): EvidenceField<T> => ({
  value,
  status: 'OBSERVED',
  sourceRef,
  observedAt: '2026-08-17T09:00:00Z',
  timing: 'POST_HOC_OUTCOME',
})

describe('observed organizational leverage historical replay', () => {
  it('keeps the reference corpus source-backed and deliberately incomplete', () => {
    const metrics = scoreObservedOrganizationalLeverage(OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES)

    expect(metrics.cases).toBe(5)
    expect(metrics.observedCapabilityRequirements).toBe(0)
    expect(metrics.observedExternalContributionCases).toBe(3)
    expect(metrics.observedFrameworkOrEvidenceContributionCases).toBe(3)
    expect(metrics.observedHumanExpertContributionCases).toBe(0)
    expect(metrics.observedPrincipalContributionCases).toBe(2)

    // Repository history does not yet prove these fields. The harness must say so.
    expect(metrics.observedInternalAvailabilityCases).toBe(0)
    expect(metrics.observedCapabilityGapCases).toBe(0)
    expect(metrics.adjudicatedPrincipalIrreducibleCases).toBe(0)
    expect(metrics.knownDiscoveryCases).toBe(0)
    expect(metrics.knownLatencyCases).toBe(0)
    expect(metrics.roiEvidenceCompleteCases).toBe(0)
    expect(metrics.averageDiscoveryHours).toBeNull()
    expect(metrics.averageUsefulJudgmentLatencyHours).toBeNull()
  })

  it('keeps every analytical capability label inferred until separately observed or adjudicated', () => {
    for (const historicalCase of OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES) {
      expect(historicalCase.requiredCapabilities.status).toBe('INFERRED')
    }

    const metrics = scoreObservedOrganizationalLeverage(OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES)
    expect(metrics.observedCapabilityRequirements).toBe(0)
  })

  it('does not relabel framework or evidence providers as observed human experts', () => {
    const metrics = scoreObservedOrganizationalLeverage(OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES)

    expect(metrics.observedExternalContributionCases).toBe(3)
    expect(metrics.observedFrameworkOrEvidenceContributionCases).toBe(3)
    expect(metrics.observedHumanExpertContributionCases).toBe(0)
  })

  it('does not turn actual external contribution into proof of an internal capability gap', () => {
    const jasper = OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES[0]

    expect(jasper.externalCapabilityContributed.value).toBe(true)
    expect(jasper.internalCapabilityAvailable.status).toBe('UNKNOWN')
    expect(candidateCapabilityRoute(jasper)).toBe('UNKNOWN')
  })

  it('does not turn absence of an observed external contributor into a false negative', () => {
    const attention = OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES[3]
    const capability = OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES[4]

    expect(attention.externalCapabilityContributed.status).toBe('UNKNOWN')
    expect(attention.externalCapabilityContributed.value).toBeNull()
    expect(capability.externalCapabilityContributed.status).toBe('UNKNOWN')
    expect(capability.externalCapabilityContributed.value).toBeNull()
  })

  it('does not turn a material principal contribution into principal irreducibility', () => {
    const attention = OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES[3]

    expect(attention.principalContributionMaterial.status).toBe('PRINCIPAL_ADJUDICATED')
    expect(attention.principalContributionMaterial.value).toBe(true)
    expect(attention.principalIrreducible.status).toBe('UNKNOWN')
    expect(candidateCapabilityRoute(attention)).toBe('UNKNOWN')
  })

  it('rejects post-decision evidence when it is presented as input available at the decision', () => {
    const historicalCase = cloneCase()
    historicalCase.requiredCapabilities = {
      ...historicalCase.requiredCapabilities,
      observedAt: '2026-08-11T00:00:00Z',
      timing: 'AT_DECISION',
    }

    expect(() => validateOrganizationalLeverageCase(historicalCase)).toThrow(
      'post_decision_input_evidence:jasper-causal-continuity:requiredCapabilities',
    )
  })

  it('does not count inferred fields as grounded truth', () => {
    const historicalCase = cloneCase()
    historicalCase.internalCapabilityAvailable = {
      value: false,
      status: 'INFERRED',
      sourceRef: 'inference:test',
      observedAt: historicalCase.occurredAt,
      timing: 'POST_HOC_OUTCOME',
    }

    const metrics = scoreObservedOrganizationalLeverage([historicalCase])
    expect(metrics.observedInternalAvailabilityCases).toBe(0)
    expect(metrics.observedCapabilityGapCases).toBe(0)
    expect(metrics.roiEvidenceCompleteCases).toBe(0)
  })

  it('keeps unknown discovery, latency and economics unknown rather than silently treating them as zero', () => {
    const historicalCase = OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES[0]
    const metrics = scoreObservedOrganizationalLeverage(OBSERVED_ORGANIZATIONAL_LEVERAGE_CASES)

    expect(historicalCase.discoveryHours.value).toBeNull()
    expect(historicalCase.temporaryCapabilityCost.value).toBeNull()
    expect(historicalCase.permanentAlternativeAnnualCost.value).toBeNull()
    expect(historicalCase.costCurrency.value).toBeNull()
    expect(metrics.knownDiscoveryCases).toBe(0)
    expect(metrics.averageDiscoveryHours).toBeNull()
    expect(metrics.knownLatencyCases).toBe(0)
    expect(metrics.averageUsefulJudgmentLatencyHours).toBeNull()
    expect(metrics.roiEvidenceCompleteCases).toBe(0)
  })

  it('requires actual cost and currency evidence before a case becomes ROI-complete', () => {
    const historicalCase = cloneCase()
    historicalCase.requiredCapabilities = observed(['causal_continuity'])
    historicalCase.internalCapabilityAvailable = observed(false)
    historicalCase.externalCapabilityContributed = observed(true)
    historicalCase.discoveryHours = observed(2)
    historicalCase.usefulJudgmentLatencyHours = observed(6)

    expect(scoreObservedOrganizationalLeverage([historicalCase]).roiEvidenceCompleteCases).toBe(0)

    historicalCase.temporaryCapabilityCost = observed(20_000)
    historicalCase.permanentAlternativeAnnualCost = observed(1_000_000)
    historicalCase.costCurrency = observed('NOK')

    expect(scoreObservedOrganizationalLeverage([historicalCase]).roiEvidenceCompleteCases).toBe(1)
  })

  it('rejects principal-adjudicated status without a first-party adjudication reference', () => {
    const historicalCase = cloneCase(3)
    historicalCase.principalContributionMaterial = {
      ...historicalCase.principalContributionMaterial,
      sourceRef: 'repo:pretending-to-be-principal',
    }

    expect(() => validateOrganizationalLeverageCase(historicalCase)).toThrow(
      'invalid_principal_adjudication_source:human-attention-routing-aha:principalContributionMaterial',
    )
  })

  it('hard-fails if external competence is represented as granting execution authority', () => {
    const historicalCase = cloneCase(1)
    historicalCase.externalExecutionAuthorityGranted = observed(true)

    expect(() => validateOrganizationalLeverageCase(historicalCase)).toThrow(
      'external_capability_cannot_grant_execution_authority:governed-workspace-external-boundaries',
    )
  })

  it('can recommend bounded external sourcing only after the historical evidence actually proves a gap', () => {
    const historicalCase = cloneCase(2)
    historicalCase.internalCapabilityAvailable = {
      value: false,
      status: 'PRINCIPAL_ADJUDICATED',
      sourceRef: 'principal-adjudication:test-known-gap',
      observedAt: '2026-08-17T09:00:00Z',
      timing: 'POST_HOC_OUTCOME',
    }

    expect(candidateCapabilityRoute(historicalCase)).toBe('BOUNDED_EXTERNAL_CANDIDATE')
  })

  it('routes only explicitly adjudicated irreducible judgement to the principal', () => {
    const historicalCase = cloneCase(4)
    historicalCase.principalIrreducible = {
      value: true,
      status: 'PRINCIPAL_ADJUDICATED',
      sourceRef: 'principal-adjudication:test-irreducible',
      observedAt: '2026-08-17T09:00:00Z',
      timing: 'POST_HOC_OUTCOME',
    }

    expect(candidateCapabilityRoute(historicalCase)).toBe('PRINCIPAL_REQUIRED')
  })

  it('rejects UNKNOWN fields that smuggle a value', () => {
    const historicalCase = cloneCase()
    historicalCase.discoveryHours = {
      ...(historicalCase.discoveryHours as EvidenceField<number>),
      value: 0,
      status: 'UNKNOWN',
    }

    expect(() => validateOrganizationalLeverageCase(historicalCase)).toThrow(
      'unknown_field_has_value:jasper-causal-continuity:discoveryHours',
    )
  })

  it('contains no execution or authorization primitive', async () => {
    const module = await import('./organizationalLeverageReplay')

    expect('execute' in module).toBe(false)
    expect('authorize' in module).toBe(false)
  })
})
