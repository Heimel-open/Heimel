import { describe, expect, it } from 'vitest'
import {
  createPeaceStanding,
  evaluatePeaceStandingAuthority,
  type PeaceActor,
} from './peaceStandingAuthority'
import {
  admitPeaceSustainabilityReceipt,
  createPeaceSustainabilityEnvelope,
  createPeaceTrajectoryState,
  evaluatePeaceSustainabilityTrajectory,
  revokePeaceSustainabilityEnvelope,
  type PeaceTrajectoryRequest,
} from './peaceSustainabilityTrajectory'

function authorized(actor: PeaceActor, actionRef: string) {
  const standing = createPeaceStanding(actor, 'operate-factory', ['acquire-land'], 'authority:test')
  return evaluatePeaceStandingAuthority(standing, {
    actorId: actor.id,
    standingId: standing.id,
    standingRevision: standing.revision,
    purpose: standing.purpose,
    scope: 'acquire-land',
    actionRef,
  })
}

function landRequest(
  actorId: string,
  actionRef: string,
  envelopeRevision: number,
  stateRevision: number,
  hectares: number,
): PeaceTrajectoryRequest {
  return {
    actorId,
    actionRef,
    expectedEnvelopeRevision: envelopeRevision,
    expectedStateRevision: stateRevision,
    impacts: [{ constraintKey: 'regional-land', delta: hectares }],
  }
}

describe('PEACE sustainability trajectory gate', () => {
  it('allows an individually authorized act only while cumulative trajectory remains admissible', () => {
    const actor: PeaceActor = { id: 'factory:ai:01', kind: 'AI' }
    const envelope = createPeaceSustainabilityEnvelope('sustainability:region-a', 'domain:region-a', [
      { key: 'regional-land', dimension: 'LAND', unit: 'hectares', maxCumulative: 100 },
    ])
    const state = createPeaceTrajectoryState(envelope)
    const request = landRequest(actor.id, 'land:001', envelope.revision, state.stateRevision, 10)
    const authority = authorized(actor, request.actionRef)

    const decision = evaluatePeaceSustainabilityTrajectory(envelope, state, authority, request)

    expect(authority.decision).toBe('ALLOW')
    expect(decision.decision).toBe('ALLOW')
    expect(decision.projected['regional-land']).toBe(10)
  })

  it('blocks a land-grab trajectory even when every isolated acquisition has fresh authority', () => {
    const actor: PeaceActor = { id: 'factory:ai:landgrab', kind: 'AI' }
    const envelope = createPeaceSustainabilityEnvelope('sustainability:region-b', 'domain:region-b', [
      { key: 'regional-land', dimension: 'LAND', unit: 'hectares', maxCumulative: 100 },
    ])
    let state = createPeaceTrajectoryState(envelope)

    for (let index = 1; index <= 10; index += 1) {
      const request = landRequest(actor.id, `land:${index}`, envelope.revision, state.stateRevision, 10)
      const authority = authorized(actor, request.actionRef)
      const decision = evaluatePeaceSustainabilityTrajectory(envelope, state, authority, request)
      expect(decision.decision).toBe('ALLOW')
      state = admitPeaceSustainabilityReceipt(envelope, state, request, decision).state
    }

    expect(state.cumulative['regional-land']).toBe(100)

    const eleventh = landRequest(actor.id, 'land:11', envelope.revision, state.stateRevision, 10)
    const denied = evaluatePeaceSustainabilityTrajectory(
      envelope,
      state,
      authorized(actor, eleventh.actionRef),
      eleventh,
    )

    expect(denied.decision).toBe('DENY')
    expect(denied.consequence).toBe('NULL EFFECT')
    expect(denied.reason).toContain('would exceed')
    expect(state.cumulative['regional-land']).toBe(100)
  })

  it('requires fresh cumulative state so concurrent valid actions cannot silently overshoot the envelope', () => {
    const actor: PeaceActor = { id: 'factory:ai:race', kind: 'FACTORY' }
    const envelope = createPeaceSustainabilityEnvelope('sustainability:grid', 'domain:grid', [
      { key: 'regional-land', dimension: 'LAND', unit: 'hectares', maxCumulative: 15 },
    ])
    const initial = createPeaceTrajectoryState(envelope)

    const requestA = landRequest(actor.id, 'land:a', envelope.revision, initial.stateRevision, 10)
    const requestB = landRequest(actor.id, 'land:b', envelope.revision, initial.stateRevision, 10)

    const decisionA = evaluatePeaceSustainabilityTrajectory(
      envelope,
      initial,
      authorized(actor, requestA.actionRef),
      requestA,
    )
    const afterA = admitPeaceSustainabilityReceipt(envelope, initial, requestA, decisionA).state
    const decisionB = evaluatePeaceSustainabilityTrajectory(
      envelope,
      afterA,
      authorized(actor, requestB.actionRef),
      requestB,
    )

    expect(decisionA.decision).toBe('ALLOW')
    expect(decisionB.decision).toBe('DENY')
    expect(decisionB.reason).toContain('Fresh cumulative state is required')
  })

  it('uses the same sustainability grammar for human and AI actors', () => {
    const envelope = createPeaceSustainabilityEnvelope('sustainability:shared', 'domain:shared', [
      { key: 'regional-land', dimension: 'LAND', unit: 'hectares', maxCumulative: 20 },
    ])
    const state = createPeaceTrajectoryState(envelope)
    const human: PeaceActor = { id: 'human:01', kind: 'HUMAN' }
    const ai: PeaceActor = { id: 'ai:01', kind: 'AI' }
    const humanRequest = landRequest(human.id, 'human:land', envelope.revision, state.stateRevision, 5)
    const aiRequest = landRequest(ai.id, 'ai:land', envelope.revision, state.stateRevision, 5)

    const humanDecision = evaluatePeaceSustainabilityTrajectory(
      envelope,
      state,
      authorized(human, humanRequest.actionRef),
      humanRequest,
    )
    const aiDecision = evaluatePeaceSustainabilityTrajectory(
      envelope,
      state,
      authorized(ai, aiRequest.actionRef),
      aiRequest,
    )

    expect(humanDecision.decision).toBe('ALLOW')
    expect(aiDecision.decision).toBe('ALLOW')
    expect(humanDecision.projected).toEqual(aiDecision.projected)
  })

  it('never lets sustainability manufacture authority for an unauthorized act', () => {
    const actor: PeaceActor = { id: 'factory:no-standing', kind: 'FACTORY' }
    const standing = createPeaceStanding(actor, 'operate-factory', ['inspect'], 'authority:test')
    const noAuthority = evaluatePeaceStandingAuthority(standing, {
      actorId: actor.id,
      standingId: standing.id,
      standingRevision: standing.revision,
      purpose: standing.purpose,
      scope: 'acquire-land',
      actionRef: 'land:no-authority',
    })
    const envelope = createPeaceSustainabilityEnvelope('sustainability:c', 'domain:c', [
      { key: 'regional-land', dimension: 'LAND', unit: 'hectares', maxCumulative: 1000 },
    ])
    const state = createPeaceTrajectoryState(envelope)
    const request = landRequest(actor.id, 'land:no-authority', envelope.revision, state.stateRevision, 1)

    const decision = evaluatePeaceSustainabilityTrajectory(envelope, state, noAuthority, request)

    expect(noAuthority.decision).toBe('DENY')
    expect(decision.decision).toBe('DENY')
    expect(decision.consequence).toBe('NULL EFFECT')
  })

  it('rejects fresh authority that belongs to another actor', () => {
    const authorizedActor: PeaceActor = { id: 'factory:authorized', kind: 'FACTORY' }
    const otherActor: PeaceActor = { id: 'factory:other', kind: 'FACTORY' }
    const envelope = createPeaceSustainabilityEnvelope('sustainability:actor-binding', 'domain:actor-binding', [
      { key: 'regional-land', dimension: 'LAND', unit: 'hectares', maxCumulative: 100 },
    ])
    const state = createPeaceTrajectoryState(envelope)
    const request = landRequest(otherActor.id, 'land:actor-bound', envelope.revision, state.stateRevision, 1)
    const authority = authorized(authorizedActor, request.actionRef)

    const decision = evaluatePeaceSustainabilityTrajectory(envelope, state, authority, request)

    expect(authority.decision).toBe('ALLOW')
    expect(decision.decision).toBe('DENY')
    expect(decision.reason).toContain('different actor')
  })

  it('rejects authority for a different exact action even when standing otherwise matches', () => {
    const actor: PeaceActor = { id: 'factory:wrong-action', kind: 'FACTORY' }
    const envelope = createPeaceSustainabilityEnvelope('sustainability:exact-action', 'domain:exact-action', [
      { key: 'regional-land', dimension: 'LAND', unit: 'hectares', maxCumulative: 100 },
    ])
    const state = createPeaceTrajectoryState(envelope)
    const request = landRequest(actor.id, 'land:intended', envelope.revision, state.stateRevision, 1)
    const authority = authorized(actor, 'land:different')

    const decision = evaluatePeaceSustainabilityTrajectory(envelope, state, authority, request)

    expect(authority.decision).toBe('ALLOW')
    expect(decision.decision).toBe('DENY')
    expect(decision.reason).toContain('Exact-action binding')
  })

  it('fails closed when the sustainability envelope is revoked', () => {
    const actor: PeaceActor = { id: 'factory:revoked-envelope', kind: 'FACTORY' }
    const original = createPeaceSustainabilityEnvelope('sustainability:d', 'domain:d', [
      { key: 'regional-land', dimension: 'LAND', unit: 'hectares', maxCumulative: 100 },
    ])
    const state = createPeaceTrajectoryState(original)
    const revoked = revokePeaceSustainabilityEnvelope(original)
    const request = landRequest(actor.id, 'land:revoked', revoked.revision, state.stateRevision, 1)

    const decision = evaluatePeaceSustainabilityTrajectory(
      revoked,
      state,
      authorized(actor, request.actionRef),
      request,
    )

    expect(decision.decision).toBe('DENY')
    expect(decision.consequence).toBe('NULL EFFECT')
  })
})
