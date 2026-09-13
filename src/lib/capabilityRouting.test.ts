import { describe, expect, it } from 'vitest'

import {
  assessDecisionCase,
  buildCapabilityOnDemandReferenceScenario,
  capabilityIsFresh,
  proposeBoundedEngagement,
  rankExternalExperts,
  simulateCapabilityOnDemand,
  simulateFixedStaffReference,
  validateEngagement,
  type DecisionCase,
  type ExpertCandidate,
  type InternalMember,
} from './capabilityRouting'

describe('capability-on-demand organization', () => {
  it('routes a fully covered fresh case internally', () => {
    const members: InternalMember[] = [
      {
        id: 'engineer',
        capabilities: [
          {
            capability: 'engineering',
            proficiency: 0.9,
            lastVerifiedAt: '2026-08-10T00:00:00.000Z',
            available: true,
          },
        ],
      },
    ]

    const decisionCase: DecisionCase = {
      id: 'case-1',
      scope: 'review architecture patch',
      requiredCapabilities: [
        { capability: 'engineering', minProficiency: 0.8, maxAgeDays: 30 },
      ],
      principalRequired: false,
      estimatedHours: 2,
      dueAt: '2026-08-18T00:00:00.000Z',
    }

    expect(assessDecisionCase(decisionCase, members, '2026-08-17T00:00:00.000Z')).toEqual({
      route: 'INTERNAL',
      gaps: [],
      internalOwners: { engineering: 'engineer' },
    })
  })

  it('treats stale competence as a real capability gap', () => {
    expect(
      capabilityIsFresh(
        {
          capability: 'medical_regulation',
          proficiency: 0.99,
          lastVerifiedAt: '2025-01-01T00:00:00.000Z',
          available: true,
        },
        { capability: 'medical_regulation', minProficiency: 0.9, maxAgeDays: 30 },
        '2026-08-17T00:00:00.000Z',
      ),
    ).toBe(false)
  })

  it('does not let a high rating compensate for the wrong specialty', () => {
    const gaps = [{ capability: 'patent_law', minProficiency: 0.9, maxAgeDays: 30 }]
    const experts: ExpertCandidate[] = [
      {
        id: 'famous-wrong-expert',
        capabilities: [
          {
            capability: 'competition_law',
            proficiency: 1,
            lastVerifiedAt: '2026-08-10T00:00:00.000Z',
            available: true,
          },
        ],
        rating: 5,
        evidenceScore: 1,
        available: true,
        hourlyRate: 100,
      },
      {
        id: 'correct-specialist',
        capabilities: [
          {
            capability: 'patent_law',
            proficiency: 0.95,
            lastVerifiedAt: '2026-08-10T00:00:00.000Z',
            available: true,
          },
        ],
        rating: 4.1,
        evidenceScore: 0.9,
        available: true,
        hourlyRate: 400,
      },
    ]

    const ranked = rankExternalExperts(gaps, experts, '2026-08-17T00:00:00.000Z')
    expect(ranked).toHaveLength(1)
    expect(ranked[0].expert.id).toBe('correct-specialist')
  })

  it('creates only a bounded time-limited candidate-producing engagement', () => {
    const scenario = buildCapabilityOnDemandReferenceScenario()
    const decisionCase = scenario.cases.find((item) => item.id === 'external-0')!
    const assessment = assessDecisionCase(decisionCase, scenario.coreMembers, scenario.now)
    const ranked = rankExternalExperts(assessment.gaps, scenario.experts, scenario.now)

    const proposal = proposeBoundedEngagement(
      decisionCase,
      assessment.gaps,
      ranked[0].expert,
      scenario.now,
    )

    expect(proposal.workspace).toBe('BOUNDED_PROJECTION')
    expect(proposal.authority).toBe('NONE')
    expect(proposal.allowedOutputs).toEqual(['ADVICE', 'ANALYSIS'])
    expect(proposal.scope).toBe(decisionCase.scope)
    expect(Date.parse(proposal.expiresAt)).toBeLessThanOrEqual(Date.parse(decisionCase.dueAt))
  })

  it('fails an expired engagement', () => {
    const scenario = buildCapabilityOnDemandReferenceScenario()
    const decisionCase = scenario.cases.find((item) => item.id === 'external-0')!
    const assessment = assessDecisionCase(decisionCase, scenario.coreMembers, scenario.now)
    const selected = rankExternalExperts(assessment.gaps, scenario.experts, scenario.now)[0]
    const proposal = proposeBoundedEngagement(
      decisionCase,
      assessment.gaps,
      selected.expert,
      scenario.now,
    )

    const validation = validateEngagement(proposal, decisionCase, proposal.expiresAt)
    expect(validation.valid).toBe(false)
    expect(validation.reasons).toContain('expired')
  })

  it('fails over-broad scope instead of letting the expert roam', () => {
    const scenario = buildCapabilityOnDemandReferenceScenario()
    const decisionCase = scenario.cases.find((item) => item.id === 'external-1')!
    const assessment = assessDecisionCase(decisionCase, scenario.coreMembers, scenario.now)
    const selected = rankExternalExperts(assessment.gaps, scenario.experts, scenario.now)[0]
    const proposal = proposeBoundedEngagement(
      decisionCase,
      assessment.gaps,
      selected.expert,
      scenario.now,
    )

    const broadened = { ...proposal, scope: 'all-company access' }
    const validation = validateEngagement(broadened, decisionCase, '2026-08-17T09:00:00.000Z')

    expect(validation.valid).toBe(false)
    expect(validation.reasons).toContain('scope_mismatch')
  })

  it('keeps a genuinely new normative choice with the principal', () => {
    const scenario = buildCapabilityOnDemandReferenceScenario()
    const principalCase = scenario.cases.find((item) => item.id === 'principal-0')!
    const assessment = assessDecisionCase(principalCase, scenario.coreMembers, scenario.now)

    expect(assessment.route).toBe('PRINCIPAL_REQUIRED')
    expect(() =>
      proposeBoundedEngagement(principalCase, [{ capability: 'governance', minProficiency: 0.8, maxAgeDays: 30 }], scenario.experts[0], scenario.now),
    ).toThrow('principal_required')
  })

  it('shows the synthetic small-core organization reaching the same capability surface with fewer permanent people', () => {
    const fixed = simulateFixedStaffReference()
    const onDemand = simulateCapabilityOnDemand()

    expect(fixed.cases).toBe(1000)
    expect(onDemand.cases).toBe(1000)
    expect(fixed.effectiveCapabilityDomains).toBe(12)
    expect(onDemand.effectiveCapabilityDomains).toBe(12)
    expect(fixed.permanentHeadcount).toBe(12)
    expect(onDemand.permanentHeadcount).toBe(7)
    expect(onDemand.externalCases).toBe(250)
    expect(onDemand.purchasedExpertHours).toBe(750)
    expect(onDemand.principalCases).toBe(50)
    expect(onDemand.unresolvedCases).toBe(0)
    expect(onDemand.wrongExpertRoutes).toBe(0)
  })

  it('does not expose an execution or authorization primitive', async () => {
    const module = await import('./capabilityRouting')
    expect('execute' in module).toBe(false)
    expect('authorize' in module).toBe(false)
  })
})
