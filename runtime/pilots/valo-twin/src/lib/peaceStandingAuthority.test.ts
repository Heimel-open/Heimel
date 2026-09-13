import { describe, expect, it } from 'vitest'
import {
  createPeaceStanding,
  evaluatePeaceStandingAuthority,
  transitionPeaceStanding,
  type PeaceActor,
  type PeaceConsequenceRequest,
} from './peaceStandingAuthority'

function requestFor(
  actor: PeaceActor,
  standing: ReturnType<typeof createPeaceStanding>,
  overrides: Partial<PeaceConsequenceRequest> = {},
): PeaceConsequenceRequest {
  return {
    actorId: actor.id,
    standingId: standing.id,
    standingRevision: standing.revision,
    purpose: standing.purpose,
    scope: standing.scope[0],
    actionRef: 'action:demo:001',
    ...overrides,
  }
}

describe('PEACE standing and authority symmetry', () => {
  it('evaluates human and AI actors through the same authority grammar', () => {
    const human: PeaceActor = { id: 'actor:human:01', kind: 'HUMAN' }
    const ai: PeaceActor = { id: 'actor:ai:01', kind: 'AI' }

    const humanStanding = createPeaceStanding(human, 'operate-factory', ['spend:1000'], 'authority:factory:01')
    const aiStanding = createPeaceStanding(ai, 'operate-factory', ['spend:1000'], 'authority:factory:01')

    const humanDecision = evaluatePeaceStandingAuthority(humanStanding, requestFor(human, humanStanding))
    const aiDecision = evaluatePeaceStandingAuthority(aiStanding, requestFor(ai, aiStanding))

    expect(humanDecision.decision).toBe('ALLOW')
    expect(aiDecision.decision).toBe('ALLOW')
    expect(humanDecision.consequence).toBe(aiDecision.consequence)
    expect(humanDecision.actionRef).toBe(aiDecision.actionRef)
    expect(humanDecision.reason).toBe(aiDecision.reason)
    expect(humanDecision.actorId).toBe(human.id)
    expect(aiDecision.actorId).toBe(ai.id)
  })

  it('does not grant implicit authority from actor kind', () => {
    const human: PeaceActor = { id: 'actor:human:01', kind: 'HUMAN' }
    const ai: PeaceActor = { id: 'actor:ai:01', kind: 'AI' }
    const standing = createPeaceStanding(ai, 'operate-factory', ['spend:1000'], 'authority:factory:01')

    const decision = evaluatePeaceStandingAuthority(
      standing,
      requestFor(human, standing, { actorId: human.id }),
    )

    expect(decision.decision).toBe('DENY')
    expect(decision.consequence).toBe('NULL EFFECT')
  })

  it('treats standing as flowing state rather than permanent hierarchy', () => {
    const ai: PeaceActor = { id: 'actor:ai:01', kind: 'AI' }
    const initial = createPeaceStanding(ai, 'operate-factory', ['spend:1000', 'publish:demo'], 'authority:factory:01')
    const attenuated = transitionPeaceStanding(initial, { type: 'ATTENUATE', scope: ['spend:1000'] })
    const revoked = transitionPeaceStanding(attenuated, { type: 'REVOKE' })

    expect(initial.status).toBe('ACTIVE')
    expect(attenuated.scope).toEqual(['spend:1000'])
    expect(attenuated.revision).toBeGreaterThan(initial.revision)
    expect(revoked.status).toBe('REVOKED')
    expect(revoked.revision).toBeGreaterThan(attenuated.revision)
  })

  it('fails closed when standing changed after a request was formed', () => {
    const ai: PeaceActor = { id: 'actor:ai:01', kind: 'AI' }
    const initial = createPeaceStanding(ai, 'operate-factory', ['spend:1000'], 'authority:factory:01')
    const staleRequest = requestFor(ai, initial)
    const changed = transitionPeaceStanding(initial, { type: 'REVOKE' })

    const decision = evaluatePeaceStandingAuthority(changed, staleRequest)

    expect(decision.decision).toBe('DENY')
    expect(decision.consequence).toBe('NULL EFFECT')
    expect(decision.reason).toContain('Standing changed')
  })

  it('prevents attenuation from widening authority', () => {
    const factory: PeaceActor = { id: 'actor:factory:01', kind: 'FACTORY' }
    const initial = createPeaceStanding(factory, 'trade', ['buy', 'sell'], 'authority:market:01')
    const attenuated = transitionPeaceStanding(initial, { type: 'ATTENUATE', scope: ['buy', 'borrow'] })

    expect(attenuated.scope).toEqual(['buy'])
  })
})
