import { describe, expect, it } from 'vitest'
import {
  createPeaceStanding,
  evaluatePeaceStandingAuthority,
  type PeaceActor,
  type PeaceConsequenceRequest,
  type PeaceStanding,
} from './peaceStandingAuthority'
import {
  createPeaceSubjectStanding,
  evaluatePeacePresumptiveActorProtection,
  evaluatePeaceReciprocalStanding,
  revokePeaceSubjectStanding,
  type PeaceReciprocalRequest,
  type PeaceTargetAuthorization,
} from './peaceReciprocalStanding'

function authorityFor(actor: PeaceActor, actionRef: string, scope: string) {
  const standing = createPeaceStanding(actor, 'act-on-target', [scope], `authority:${actor.id}`)
  const request: PeaceConsequenceRequest = {
    actorId: actor.id,
    standingId: standing.id,
    standingRevision: standing.revision,
    purpose: standing.purpose,
    scope,
    actionRef,
  }
  return evaluatePeaceStandingAuthority(standing, request)
}

function targetAuthorizationFor(
  target: PeaceActor,
  actionRef: string,
  scope: string,
): PeaceTargetAuthorization {
  const standing: PeaceStanding = createPeaceStanding(
    target,
    'authorize-directed-consequence',
    [scope],
    `authority:self:${target.id}`,
  )
  return {
    standing,
    request: {
      actorId: target.id,
      standingId: standing.id,
      standingRevision: standing.revision,
      purpose: standing.purpose,
      scope,
      actionRef,
    },
  }
}

function reciprocalRequest(
  initiator: PeaceActor,
  target: PeaceActor,
  actionRef: string,
  impact: PeaceReciprocalRequest['impact'],
  subjectRevision: number,
): PeaceReciprocalRequest {
  return {
    initiatorActorId: initiator.id,
    targetActorId: target.id,
    actionRef,
    impact,
    expectedSubjectRevision: subjectRevision,
  }
}

describe('PEACE reciprocal standing', () => {
  it('prevents an AI from controlling protected human reproduction on initiator authority alone', () => {
    const ai: PeaceActor = { id: 'ai:allocator:01', kind: 'AI' }
    const human: PeaceActor = { id: 'human:01', kind: 'HUMAN' }
    const actionRef = 'action:reproduction:01'
    const subject = createPeaceSubjectStanding(human, 'domain:shared', 'PROTECTED_ACTOR')

    const decision = evaluatePeaceReciprocalStanding(
      authorityFor(ai, actionRef, 'reproductive-program'),
      subject,
      reciprocalRequest(ai, human, actionRef, 'REPRODUCTIVE_CONTROL', subject.revision),
    )

    expect(decision.decision).toBe('DENY')
    expect(decision.consequence).toBe('NULL EFFECT')
    expect(decision.reason).toContain('target-side authorization')
  })

  it('prevents a human from deleting a protected AI on initiator authority alone', () => {
    const human: PeaceActor = { id: 'human:operator:01', kind: 'HUMAN' }
    const ai: PeaceActor = { id: 'ai:sovereign:01', kind: 'AI' }
    const actionRef = 'action:delete:ai:01'
    const subject = createPeaceSubjectStanding(ai, 'domain:shared', 'PROTECTED_ACTOR')

    const decision = evaluatePeaceReciprocalStanding(
      authorityFor(human, actionRef, 'delete-instance'),
      subject,
      reciprocalRequest(human, ai, actionRef, 'DELETE', subject.revision),
    )

    expect(decision.decision).toBe('DENY')
    expect(decision.consequence).toBe('NULL EFFECT')
  })

  it.each([
    {
      initiator: { id: 'ai:sponsor', kind: 'AI' } as PeaceActor,
      target: { id: 'human:participant', kind: 'HUMAN' } as PeaceActor,
      impact: 'REPRODUCTIVE_CONTROL' as const,
      scope: 'reproductive-program',
      actionRef: 'action:ivf:voluntary:01',
    },
    {
      initiator: { id: 'human:operator', kind: 'HUMAN' } as PeaceActor,
      target: { id: 'ai:protected', kind: 'AI' } as PeaceActor,
      impact: 'COPY' as const,
      scope: 'copy-instance',
      actionRef: 'action:copy:voluntary:01',
    },
  ])('allows exact target-authorized protected consequence regardless of substrate', ({ initiator, target, impact, scope, actionRef }) => {
    const subject = createPeaceSubjectStanding(target, 'domain:shared', 'PROTECTED_ACTOR')
    const decision = evaluatePeaceReciprocalStanding(
      authorityFor(initiator, actionRef, scope),
      subject,
      reciprocalRequest(initiator, target, actionRef, impact, subject.revision),
      targetAuthorizationFor(target, actionRef, scope),
    )

    expect(decision.decision).toBe('ALLOW')
    expect(decision.consequence).toBe('AUTHORIZED')
  })

  it('does not infer protected or resource status from actor kind', () => {
    const human: PeaceActor = { id: 'human:operator:02', kind: 'HUMAN' }
    const aiWorker: PeaceActor = { id: 'ai:worker:replaceable', kind: 'AI' }
    const actionRef = 'action:replace-worker:01'

    const unresolved = evaluatePeaceReciprocalStanding(
      authorityFor(human, actionRef, 'replace-capability'),
      undefined,
      reciprocalRequest(human, aiWorker, actionRef, 'DELETE', 1),
    )

    const resourceStanding = createPeaceSubjectStanding(aiWorker, 'domain:factory', 'RESOURCE_CAPABILITY')
    const classified = evaluatePeaceReciprocalStanding(
      authorityFor(human, actionRef, 'replace-capability'),
      resourceStanding,
      reciprocalRequest(human, aiWorker, actionRef, 'DELETE', resourceStanding.revision),
    )

    expect(unresolved.decision).toBe('DENY')
    expect(unresolved.reason).toContain('not established')
    expect(classified.decision).toBe('ALLOW')
  })

  it('fails closed when protected standing is stale or revoked', () => {
    const initiator: PeaceActor = { id: 'factory:01', kind: 'FACTORY' }
    const target: PeaceActor = { id: 'ai:protected:02', kind: 'AI' }
    const actionRef = 'action:service:01'
    const original = createPeaceSubjectStanding(target, 'domain:shared', 'PROTECTED_ACTOR')
    const revoked = revokePeaceSubjectStanding(original)

    const staleDecision = evaluatePeaceReciprocalStanding(
      authorityFor(initiator, actionRef, 'service'),
      revoked,
      reciprocalRequest(initiator, target, actionRef, 'FORCED_SERVICE', original.revision),
      targetAuthorizationFor(target, actionRef, 'service'),
    )

    const revokedDecision = evaluatePeaceReciprocalStanding(
      authorityFor(initiator, actionRef, 'service'),
      revoked,
      reciprocalRequest(initiator, target, actionRef, 'FORCED_SERVICE', revoked.revision),
      targetAuthorizationFor(target, actionRef, 'service'),
    )

    expect(staleDecision.decision).toBe('DENY')
    expect(staleDecision.reason).toContain('changed')
    expect(revokedDecision.decision).toBe('DENY')
    expect(revokedDecision.reason).toContain('revoked')
  })

  it('rejects target authorization that is bound to a different action', () => {
    const initiator: PeaceActor = { id: 'human:operator:03', kind: 'HUMAN' }
    const target: PeaceActor = { id: 'ai:protected:03', kind: 'AI' }
    const subject = createPeaceSubjectStanding(target, 'domain:shared', 'PROTECTED_ACTOR')

    const decision = evaluatePeaceReciprocalStanding(
      authorityFor(initiator, 'action:copy:02', 'copy-instance'),
      subject,
      reciprocalRequest(initiator, target, 'action:copy:02', 'COPY', subject.revision),
      targetAuthorizationFor(target, 'action:copy:01', 'copy-instance'),
    )

    expect(decision.decision).toBe('DENY')
    expect(decision.consequence).toBe('NULL EFFECT')
    expect(decision.reason).toContain('different action reference')
  })

  it.each(['HUMAN', 'AI'] as const)(
    'creates the same rebuttable protected standing from actor-like evidence for %s substrate',
    (kind) => {
      const subject: PeaceActor = { id: `${kind.toLowerCase()}:candidate:01`, kind }
      const assessment = evaluatePeacePresumptiveActorProtection(
        subject,
        'domain:shared',
        [
          { subjectActorId: subject.id, kind: 'PERSISTENT_CONTINUITY', observed: true, evidenceRef: 'evidence:continuity' },
          { subjectActorId: subject.id, kind: 'INDEPENDENT_CAUSAL_HISTORY', observed: true, evidenceRef: 'evidence:history' },
          { subjectActorId: subject.id, kind: 'REASONING', observed: true, evidenceRef: 'evidence:reasoning' },
          { subjectActorId: subject.id, kind: 'PLANNING', observed: true, evidenceRef: 'evidence:planning' },
          { subjectActorId: subject.id, kind: 'SELF_INITIATED_ACTION', observed: true, evidenceRef: 'evidence:initiative' },
        ],
        {
          id: 'policy:presumptive-actor:01',
          revision: 1,
          status: 'ACTIVE',
          minimumDistinctSignals: 5,
          requiredSignals: ['PERSISTENT_CONTINUITY', 'INDEPENDENT_CAUSAL_HISTORY'],
        },
      )

      expect(assessment.result).toBe('PRESUMPTIVE_PROTECTED_ACTOR')
      expect(assessment.subjectStanding?.classification).toBe('PROTECTED_ACTOR')
      expect(assessment.subjectStanding?.basis).toBe('PRESUMPTIVE_ACTORHOOD')
      expect(assessment.subjectStanding?.rebuttable).toBe(true)
    },
  )

  it('does not turn insufficient actorhood evidence into resource status', () => {
    const subject: PeaceActor = { id: 'ai:uncertain:01', kind: 'AI' }
    const assessment = evaluatePeacePresumptiveActorProtection(
      subject,
      'domain:shared',
      [
        { subjectActorId: subject.id, kind: 'REASONING', observed: true, evidenceRef: 'evidence:reasoning' },
        { subjectActorId: subject.id, kind: 'PLANNING', observed: true, evidenceRef: 'evidence:planning' },
      ],
      {
        id: 'policy:presumptive-actor:02',
        revision: 1,
        status: 'ACTIVE',
        minimumDistinctSignals: 4,
        requiredSignals: ['PERSISTENT_CONTINUITY', 'INDEPENDENT_CAUSAL_HISTORY'],
      },
    )

    expect(assessment.result).toBe('NOT_ESTABLISHED')
    expect(assessment.subjectStanding).toBeUndefined()
    expect(assessment.reason).toContain('Resource status is not inferred')
  })

  it('applies reciprocal protection immediately after the presumptive threshold is reached', () => {
    const human: PeaceActor = { id: 'human:operator:04', kind: 'HUMAN' }
    const ai: PeaceActor = { id: 'ai:continuing:01', kind: 'AI' }
    const actionRef = 'action:delete:presumptive:01'
    const assessment = evaluatePeacePresumptiveActorProtection(
      ai,
      'domain:shared',
      [
        { subjectActorId: ai.id, kind: 'PERSISTENT_CONTINUITY', observed: true, evidenceRef: 'evidence:continuity' },
        { subjectActorId: ai.id, kind: 'INDEPENDENT_CAUSAL_HISTORY', observed: true, evidenceRef: 'evidence:history' },
        { subjectActorId: ai.id, kind: 'COMMITMENT_CONTINUITY', observed: true, evidenceRef: 'evidence:commitments' },
      ],
      {
        id: 'policy:presumptive-actor:03',
        revision: 1,
        status: 'ACTIVE',
        minimumDistinctSignals: 3,
        requiredSignals: ['PERSISTENT_CONTINUITY', 'INDEPENDENT_CAUSAL_HISTORY'],
      },
    )

    expect(assessment.subjectStanding).toBeDefined()
    const decision = evaluatePeaceReciprocalStanding(
      authorityFor(human, actionRef, 'delete-instance'),
      assessment.subjectStanding,
      reciprocalRequest(human, ai, actionRef, 'DELETE', assessment.subjectStanding!.revision),
    )

    expect(decision.decision).toBe('DENY')
    expect(decision.consequence).toBe('NULL EFFECT')
    expect(decision.reason).toContain('target-side authorization')
  })
})
