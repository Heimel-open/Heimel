import type { PeaceAuthorityDecision } from './peaceStandingAuthority'

export type PeaceSustainabilityDimension =
  | 'LAND'
  | 'ENERGY'
  | 'WATER'
  | 'MATERIALS'
  | 'EMISSIONS'
  | 'MARKET_CONCENTRATION'
  | 'CUSTOM'

export type PeaceSustainabilityConstraint = {
  key: string
  dimension: PeaceSustainabilityDimension
  unit: string
  minCumulative?: number
  maxCumulative: number
}

export type PeaceSustainabilityEnvelopeStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED'

export type PeaceSustainabilityEnvelope = {
  id: string
  domainId: string
  revision: number
  status: PeaceSustainabilityEnvelopeStatus
  constraints: readonly PeaceSustainabilityConstraint[]
}

export type PeaceTrajectoryState = {
  envelopeId: string
  envelopeRevision: number
  stateRevision: number
  cumulative: Readonly<Record<string, number>>
  admittedActionRefs: readonly string[]
}

export type PeaceTrajectoryImpact = {
  constraintKey: string
  delta: number
}

export type PeaceTrajectoryRequest = {
  actorId: string
  actionRef: string
  expectedEnvelopeRevision: number
  expectedStateRevision: number
  impacts: readonly PeaceTrajectoryImpact[]
}

export type PeaceTrajectoryDecision = {
  decision: 'ALLOW' | 'DENY'
  consequence: 'AUTHORIZED' | 'NULL EFFECT'
  reason: string
  projected: Readonly<Record<string, number>>
}

export type PeaceSustainabilityReceipt = {
  actionRef: string
  actorId: string
  envelopeId: string
  envelopeRevision: number
  stateRevisionBefore: number
  stateRevisionAfter: number
  cumulativeBefore: Readonly<Record<string, number>>
  cumulativeAfter: Readonly<Record<string, number>>
}

function deny(reason: string, projected: Readonly<Record<string, number>>): PeaceTrajectoryDecision {
  return {
    decision: 'DENY',
    consequence: 'NULL EFFECT',
    reason,
    projected,
  }
}

function assertEnvelope(constraints: readonly PeaceSustainabilityConstraint[]): void {
  const keys = new Set<string>()

  for (const constraint of constraints) {
    if (keys.has(constraint.key)) {
      throw new Error(`Duplicate sustainability constraint: ${constraint.key}`)
    }
    keys.add(constraint.key)

    const minimum = constraint.minCumulative ?? 0
    if (!Number.isFinite(minimum) || !Number.isFinite(constraint.maxCumulative)) {
      throw new Error(`Sustainability bounds must be finite for ${constraint.key}`)
    }
    if (minimum > constraint.maxCumulative) {
      throw new Error(`Sustainability minimum exceeds maximum for ${constraint.key}`)
    }
  }
}

export function createPeaceSustainabilityEnvelope(
  id: string,
  domainId: string,
  constraints: readonly PeaceSustainabilityConstraint[],
): PeaceSustainabilityEnvelope {
  assertEnvelope(constraints)
  return {
    id,
    domainId,
    revision: 1,
    status: 'ACTIVE',
    constraints: constraints.map((constraint) => ({ ...constraint })),
  }
}

export function createPeaceTrajectoryState(envelope: PeaceSustainabilityEnvelope): PeaceTrajectoryState {
  return {
    envelopeId: envelope.id,
    envelopeRevision: envelope.revision,
    stateRevision: 1,
    cumulative: Object.fromEntries(envelope.constraints.map((constraint) => [constraint.key, 0])),
    admittedActionRefs: [],
  }
}

/**
 * Authority answers whether an actor may perform an act.
 * Sustainability answers whether admitting that act keeps the cumulative
 * trajectory inside the governed envelope.
 *
 * A locally authorized act is therefore still denied when repeated effects
 * would cross a cumulative resource or concentration boundary.
 */
export function evaluatePeaceSustainabilityTrajectory(
  envelope: PeaceSustainabilityEnvelope,
  state: PeaceTrajectoryState,
  authority: PeaceAuthorityDecision,
  request: PeaceTrajectoryRequest,
): PeaceTrajectoryDecision {
  const projected: Record<string, number> = { ...state.cumulative }

  if (authority.decision !== 'ALLOW' || authority.consequence !== 'AUTHORIZED') {
    return deny('The act has no fresh authority. Sustainability cannot promote it into consequence.', projected)
  }

  if (authority.actorId !== request.actorId) {
    return deny('Fresh authority belongs to a different actor.', projected)
  }

  if (authority.actionRef !== request.actionRef) {
    return deny('Fresh authority is bound to a different action reference. Exact-action binding is required.', projected)
  }

  if (envelope.status !== 'ACTIVE') {
    return deny(`Sustainability envelope is ${envelope.status.toLowerCase()} at consequence time.`, projected)
  }

  if (state.envelopeId !== envelope.id || request.expectedEnvelopeRevision !== envelope.revision) {
    return deny('Sustainability envelope reference is stale or does not match current governed state.', projected)
  }

  if (state.envelopeRevision !== envelope.revision) {
    return deny('Trajectory state was derived from a stale sustainability envelope revision.', projected)
  }

  if (request.expectedStateRevision !== state.stateRevision) {
    return deny('Trajectory changed after the request was formed. Fresh cumulative state is required.', projected)
  }

  if (state.admittedActionRefs.includes(request.actionRef)) {
    return deny('Action reference already has an admitted sustainability receipt. Replay denied.', projected)
  }

  const constraints = new Map(envelope.constraints.map((constraint) => [constraint.key, constraint]))
  const deltas = new Map<string, number>()

  for (const impact of request.impacts) {
    const constraint = constraints.get(impact.constraintKey)
    if (!constraint) {
      return deny(`No sustainability constraint exists for ${impact.constraintKey}.`, projected)
    }
    if (!Number.isFinite(impact.delta)) {
      return deny(`Non-finite trajectory impact for ${impact.constraintKey}.`, projected)
    }
    deltas.set(impact.constraintKey, (deltas.get(impact.constraintKey) ?? 0) + impact.delta)
  }

  for (const constraint of envelope.constraints) {
    const current = state.cumulative[constraint.key] ?? 0
    const next = current + (deltas.get(constraint.key) ?? 0)
    const minimum = constraint.minCumulative ?? 0
    projected[constraint.key] = next

    if (next < minimum) {
      return deny(
        `${constraint.key} trajectory would fall below ${minimum} ${constraint.unit}; projected ${next}.`,
        projected,
      )
    }

    if (next > constraint.maxCumulative) {
      return deny(
        `${constraint.key} trajectory would exceed ${constraint.maxCumulative} ${constraint.unit}; projected ${next}.`,
        projected,
      )
    }
  }

  return {
    decision: 'ALLOW',
    consequence: 'AUTHORIZED',
    reason: 'Fresh authority exists and the projected cumulative trajectory remains inside every governed constraint.',
    projected,
  }
}

export function admitPeaceSustainabilityReceipt(
  envelope: PeaceSustainabilityEnvelope,
  state: PeaceTrajectoryState,
  request: PeaceTrajectoryRequest,
  decision: PeaceTrajectoryDecision,
): { state: PeaceTrajectoryState; receipt: PeaceSustainabilityReceipt } {
  if (decision.decision !== 'ALLOW' || decision.consequence !== 'AUTHORIZED') {
    throw new Error('Cannot admit sustainability state for a denied trajectory.')
  }

  if (request.expectedStateRevision !== state.stateRevision) {
    throw new Error('Cannot admit against stale trajectory state.')
  }

  if (request.expectedEnvelopeRevision !== envelope.revision || state.envelopeRevision !== envelope.revision) {
    throw new Error('Cannot admit against stale sustainability envelope.')
  }

  if (state.admittedActionRefs.includes(request.actionRef)) {
    throw new Error('Cannot admit a replayed action reference.')
  }

  const nextState: PeaceTrajectoryState = {
    envelopeId: state.envelopeId,
    envelopeRevision: state.envelopeRevision,
    stateRevision: state.stateRevision + 1,
    cumulative: { ...decision.projected },
    admittedActionRefs: [...state.admittedActionRefs, request.actionRef],
  }

  return {
    state: nextState,
    receipt: {
      actionRef: request.actionRef,
      actorId: request.actorId,
      envelopeId: envelope.id,
      envelopeRevision: envelope.revision,
      stateRevisionBefore: state.stateRevision,
      stateRevisionAfter: nextState.stateRevision,
      cumulativeBefore: { ...state.cumulative },
      cumulativeAfter: { ...nextState.cumulative },
    },
  }
}

export function revokePeaceSustainabilityEnvelope(
  envelope: PeaceSustainabilityEnvelope,
): PeaceSustainabilityEnvelope {
  return {
    ...envelope,
    revision: envelope.revision + 1,
    status: 'REVOKED',
  }
}
