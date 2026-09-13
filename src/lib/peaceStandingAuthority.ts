export type PeaceActorKind = 'HUMAN' | 'AI' | 'ORGANISATION' | 'FACTORY' | 'SERVICE'

export type PeaceActor = {
  id: string
  kind: PeaceActorKind
}

export type PeaceStandingStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED'

export type PeaceStanding = {
  id: string
  actor: PeaceActor
  purpose: string
  scope: readonly string[]
  authorityRoot: string
  revision: number
  status: PeaceStandingStatus
}

export type PeaceConsequenceRequest = {
  actorId: string
  standingId: string
  standingRevision: number
  purpose: string
  scope: string
  actionRef: string
}

export type PeaceAuthorityDecision = {
  decision: 'ALLOW' | 'DENY'
  consequence: 'AUTHORIZED' | 'NULL EFFECT'
  actorId: string
  standingId: string
  standingRevision: number
  actionRef: string
  reason: string
}

export type PeaceStandingTransition =
  | { type: 'REVOKE' }
  | { type: 'EXPIRE' }
  | { type: 'RENEW' }
  | { type: 'ATTENUATE'; scope: readonly string[] }

export function createPeaceStanding(
  actor: PeaceActor,
  purpose: string,
  scope: readonly string[],
  authorityRoot: string,
): PeaceStanding {
  return {
    id: `standing:${actor.id}:${purpose}`,
    actor,
    purpose,
    scope: [...scope],
    authorityRoot,
    revision: 1,
    status: 'ACTIVE',
  }
}

export function transitionPeaceStanding(
  standing: PeaceStanding,
  transition: PeaceStandingTransition,
): PeaceStanding {
  switch (transition.type) {
    case 'REVOKE':
      return { ...standing, status: 'REVOKED', revision: standing.revision + 1 }
    case 'EXPIRE':
      return { ...standing, status: 'EXPIRED', revision: standing.revision + 1 }
    case 'RENEW':
      return { ...standing, status: 'ACTIVE', revision: standing.revision + 1 }
    case 'ATTENUATE': {
      const current = new Set(standing.scope)
      const narrowed = transition.scope.filter((item) => current.has(item))
      return { ...standing, scope: narrowed, revision: standing.revision + 1 }
    }
  }
}

/**
 * PEACE authority is actor-symmetric by construction.
 *
 * Human, AI, organisation, factory and service actors are evaluated through
 * exactly the same standing grammar. Actor kind confers no implicit power.
 * Authority follows fresh standing for the exact consequence request.
 */
export function evaluatePeaceStandingAuthority(
  standing: PeaceStanding,
  request: PeaceConsequenceRequest,
): PeaceAuthorityDecision {
  const decisionBase = {
    actorId: request.actorId,
    standingId: request.standingId,
    standingRevision: request.standingRevision,
    actionRef: request.actionRef,
  }

  const denied = (reason: string): PeaceAuthorityDecision => ({
    decision: 'DENY',
    consequence: 'NULL EFFECT',
    ...decisionBase,
    reason,
  })

  if (standing.actor.id !== request.actorId) {
    return denied('The consequence request does not belong to the standing holder.')
  }

  if (standing.id !== request.standingId) {
    return denied('Standing reference does not match the current standing.')
  }

  if (standing.revision !== request.standingRevision) {
    return denied('Standing changed after the request was formed. Fresh standing is required.')
  }

  if (standing.status !== 'ACTIVE') {
    return denied(`Standing is ${standing.status.toLowerCase()} at consequence time.`)
  }

  if (standing.purpose !== request.purpose) {
    return denied('Purpose does not match the standing grant.')
  }

  if (!standing.scope.includes(request.scope)) {
    return denied('Requested consequence is outside the standing scope.')
  }

  return {
    decision: 'ALLOW',
    consequence: 'AUTHORIZED',
    ...decisionBase,
    reason: 'Fresh standing authorizes this exact consequence request.',
  }
}
