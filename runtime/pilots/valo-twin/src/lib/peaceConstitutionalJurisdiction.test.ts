import { describe, expect, it } from 'vitest'
import {
  createPeaceStanding,
  evaluatePeaceStandingAuthority,
  type PeaceActor,
} from './peaceStandingAuthority'
import {
  admitPeaceConstitutionAmendment,
  createPeaceConstitution,
  createPeaceNormativeInstrument,
  createPeaceRepresentationGrant,
  evaluatePeaceConstitutionAmendment,
  evaluatePeaceEnforcement,
  evaluatePeaceLegalAdmissibility,
  evaluatePeaceRepresentation,
  type PeaceAdjudicationOutcome,
  type PeaceEnforcementBinding,
} from './peaceConstitutionalJurisdiction'

function freshAuthority(actor: PeaceActor, purpose: string, scope: string, actionRef: string) {
  const standing = createPeaceStanding(actor, purpose, [scope], `authority:${purpose}`)
  return {
    standing,
    decision: evaluatePeaceStandingAuthority(standing, {
      actorId: actor.id,
      standingId: standing.id,
      standingRevision: standing.revision,
      purpose,
      scope,
      actionRef,
    }),
  }
}

describe('PEACE constitutional provenance and jurisdiction', () => {
  it('requires the constitutionally declared amendment standing and can prohibit self-benefit', () => {
    const council: PeaceActor = { id: 'actor:council', kind: 'ORGANISATION' }
    const auth = freshAuthority(council, 'amend-constitution', 'constitution:amend', 'amend:001')
    const constitution = createPeaceConstitution(
      'constitution:shared',
      'domain:shared',
      'genesis:compact:001',
      { standingId: auth.standing.id, allowSelfBenefit: false },
    )

    const decision = evaluatePeaceConstitutionAmendment(constitution, auth.decision, {
      actionRef: 'amend:001',
      expectedRevision: constitution.revision,
      beneficiaryActorIds: [council.id],
      note: 'Widen council power over itself.',
    })

    expect(decision.decision).toBe('DENY')
    expect(decision.consequence).toBe('NULL EFFECT')
  })

  it('preserves genesis provenance across a valid constitutional amendment', () => {
    const council: PeaceActor = { id: 'actor:council', kind: 'ORGANISATION' }
    const auth = freshAuthority(council, 'amend-constitution', 'constitution:amend', 'amend:002')
    const constitution = createPeaceConstitution(
      'constitution:shared',
      'domain:shared',
      'genesis:compact:001',
      { standingId: auth.standing.id, allowSelfBenefit: false },
    )
    const request = {
      actionRef: 'amend:002',
      expectedRevision: constitution.revision,
      beneficiaryActorIds: ['actor:public'],
      note: 'Add a shared consequence procedure.',
    }
    const decision = evaluatePeaceConstitutionAmendment(constitution, auth.decision, request)
    const admitted = admitPeaceConstitutionAmendment(constitution, auth.decision, request, decision)

    expect(decision.decision).toBe('ALLOW')
    expect(admitted.constitution.genesisRef).toBe('genesis:compact:001')
    expect(admitted.constitution.revision).toBe(2)
    expect(admitted.receipt.revisionBefore).toBe(1)
  })

  it('makes representation explicit and scoped rather than universal', () => {
    const grant = createPeaceRepresentationGrant({
      id: 'representation:ai-c:delegate',
      representedRef: 'actor:ai-c',
      representativeActorId: 'actor:delegate',
      jurisdictionRef: 'compact:shared',
      sourceInstrumentId: 'treaty:representation',
      scopes: ['negotiate:treaty'],
    })

    expect(
      evaluatePeaceRepresentation(grant, {
        representedRef: 'actor:ai-c',
        representativeActorId: 'actor:delegate',
        scope: 'negotiate:treaty',
        expectedRevision: 1,
      }).decision,
    ).toBe('ALLOW')

    expect(
      evaluatePeaceRepresentation(grant, {
        representedRef: 'actor:ai-c',
        representativeActorId: 'actor:delegate',
        scope: 'terminate:continuity',
        expectedRevision: 1,
      }).decision,
    ).toBe('DENY')

    expect(() =>
      createPeaceRepresentationGrant({
        id: 'representation:universal',
        representedRef: '*',
        representativeActorId: 'actor:delegate',
        jurisdictionRef: 'compact:shared',
        sourceInstrumentId: 'treaty:representation',
        scopes: ['negotiate:treaty'],
      }),
    ).toThrow('explicit actor or governed collective')
  })

  it('defers conflicting houses to explicit adjudication', () => {
    const ai: PeaceActor = { id: 'actor:ai-buyer', kind: 'AI' }
    const actionRef = 'land:buy:001'
    const auth = freshAuthority(ai, 'acquire-property', 'property:acquire', actionRef)
    const request = {
      actorId: ai.id,
      actionRef,
      consequenceScope: 'property:acquire',
      jurisdictionRefs: ['domain:ai-house', 'jurisdiction:spain-property'],
    }
    const instruments = [
      createPeaceNormativeInstrument({
        id: 'rule:ai-house',
        kind: 'CONSTITUTION',
        issuerDomainId: 'domain:ai-house',
        jurisdictionRef: 'domain:ai-house',
        provenanceRef: 'constitution:ai-house',
        consequenceScopes: ['property:acquire'],
        effect: 'ALLOW',
      }),
      createPeaceNormativeInstrument({
        id: 'law:spain-property',
        kind: 'LAW',
        issuerDomainId: 'jurisdiction:spain',
        jurisdictionRef: 'jurisdiction:spain-property',
        provenanceRef: 'constitution:spain',
        consequenceScopes: ['property:acquire'],
        effect: 'DENY',
      }),
    ]

    const decision = evaluatePeaceLegalAdmissibility(auth.decision, request, instruments)

    expect(decision.decision).toBe('DEFER')
    expect(decision.consequence).toBe('NULL EFFECT')
    expect(decision.reason).toContain('conflict')
  })

  it('binds adjudication to the exact action and jurisdiction set', () => {
    const ai: PeaceActor = { id: 'actor:ai-buyer', kind: 'AI' }
    const actionRef = 'land:buy:002'
    const auth = freshAuthority(ai, 'acquire-property', 'property:acquire', actionRef)
    const request = {
      actorId: ai.id,
      actionRef,
      consequenceScope: 'property:acquire',
      jurisdictionRefs: ['domain:ai-house', 'jurisdiction:spain-property'],
      expectedAdjudicationRevision: 1,
    }
    const instruments = [
      createPeaceNormativeInstrument({
        id: 'rule:ai-house',
        kind: 'CONSTITUTION',
        issuerDomainId: 'domain:ai-house',
        jurisdictionRef: 'domain:ai-house',
        provenanceRef: 'constitution:ai-house',
        consequenceScopes: ['property:acquire'],
        effect: 'ALLOW',
      }),
      createPeaceNormativeInstrument({
        id: 'law:spain-property',
        kind: 'LAW',
        issuerDomainId: 'jurisdiction:spain',
        jurisdictionRef: 'jurisdiction:spain-property',
        provenanceRef: 'constitution:spain',
        consequenceScopes: ['property:acquire'],
        effect: 'DENY',
      }),
    ]
    const adjudication: PeaceAdjudicationOutcome = {
      id: 'judgment:002',
      actionRef,
      bindingInstrumentIds: instruments.map((instrument) => instrument.id),
      jurisdictionRefs: [...request.jurisdictionRefs],
      revision: 1,
      status: 'ACTIVE',
      decision: 'DENY',
    }

    const resolved = evaluatePeaceLegalAdmissibility(auth.decision, request, instruments, adjudication)

    expect(resolved.decision).toBe('DENY')
    expect(resolved.consequence).toBe('NULL EFFECT')
  })

  it('requires the designated effector after legal admissibility', () => {
    const actor: PeaceActor = { id: 'actor:buyer', kind: 'HUMAN' }
    const actionRef = 'payment:execute:001'
    const auth = freshAuthority(actor, 'pay', 'payment:execute', actionRef)
    const request = {
      actorId: actor.id,
      actionRef,
      consequenceScope: 'payment:execute',
      jurisdictionRefs: ['jurisdiction:bank'],
    }
    const law = createPeaceNormativeInstrument({
      id: 'law:bank-payment',
      kind: 'LAW',
      issuerDomainId: 'jurisdiction:bank',
      jurisdictionRef: 'jurisdiction:bank',
      provenanceRef: 'constitution:banking-law',
      consequenceScopes: ['payment:execute'],
      effect: 'ALLOW',
    })
    const legal = evaluatePeaceLegalAdmissibility(auth.decision, request, [law])
    const binding: PeaceEnforcementBinding = {
      id: 'effector:bank-ledger',
      effectorActorId: 'service:bank-ledger',
      jurisdictionRef: 'jurisdiction:bank',
      consequenceScopes: ['payment:execute'],
      revision: 1,
      status: 'ACTIVE',
    }

    const wrongEffector = evaluatePeaceEnforcement(binding, legal, {
      executorActorId: 'service:other',
      actionRef,
      consequenceScope: 'payment:execute',
      expectedBindingRevision: 1,
    })
    const rightEffector = evaluatePeaceEnforcement(binding, legal, {
      executorActorId: 'service:bank-ledger',
      actionRef,
      consequenceScope: 'payment:execute',
      expectedBindingRevision: 1,
    })

    expect(wrongEffector.decision).toBe('DENY')
    expect(rightEffector.decision).toBe('ALLOW')
    expect(rightEffector.consequence).toBe('EFFECT PERMITTED')
  })
})
