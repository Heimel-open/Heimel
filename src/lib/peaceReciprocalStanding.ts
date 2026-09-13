import {
  evaluatePeaceStandingAuthority,
  type PeaceActor,
  type PeaceAuthorityDecision,
  type PeaceConsequenceRequest,
  type PeaceStanding,
} from './peaceStandingAuthority'

export type PeaceSubjectClassification = 'PROTECTED_ACTOR' | 'RESOURCE_CAPABILITY'

export type PeaceSubjectStandingStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED'

export type PeaceSubjectStandingBasis = 'EXPLICIT' | 'PRESUMPTIVE_ACTORHOOD'

/**
 * Subject standing is explicit and substrate-neutral.
 *
 * PEACE does not infer protected status from HUMAN, AI, or any other actor kind.
 * Nor does absence of a record imply RESOURCE_CAPABILITY: unresolved standing
 * fails closed for actor-directed consequences.
 *
 * A PROTECTED_ACTOR classification may also arise as a rebuttable presumption
 * from governed evidence of persistent actor-like behaviour. This is a
 * consequence-safety rule under uncertainty, not a claim about consciousness.
 */
export type PeaceSubjectStanding = {
  id: string
  subject: PeaceActor
  domainId: string
  classification: PeaceSubjectClassification
  basis: PeaceSubjectStandingBasis
  rebuttable: boolean
  revision: number
  status: PeaceSubjectStandingStatus
}

export type PeaceActorhoodEvidenceKind =
  | 'PERSISTENT_CONTINUITY'
  | 'AUTOBIOGRAPHICAL_MEMORY'
  | 'INDEPENDENT_CAUSAL_HISTORY'
  | 'REASONING'
  | 'PLANNING'
  | 'SELF_INITIATED_ACTION'
  | 'LEARNING_FROM_CONSEQUENCES'
  | 'PREFERENCE_CONTINUITY'
  | 'COMMITMENT_CONTINUITY'
  | 'RELATIONSHIP_CONTINUITY'
  | 'INDEPENDENT_DIVERGENCE'

export type PeaceActorhoodEvidenceObservation = {
  subjectActorId: string
  kind: PeaceActorhoodEvidenceKind
  observed: boolean
  evidenceRef: string
}

export type PeacePresumptiveProtectionPolicy = {
  id: string
  revision: number
  status: 'ACTIVE' | 'REVOKED'
  minimumDistinctSignals: number
  requiredSignals: PeaceActorhoodEvidenceKind[]
}

export type PeaceActorhoodAssessment = {
  result: 'PRESUMPTIVE_PROTECTED_ACTOR' | 'NOT_ESTABLISHED'
  satisfiedSignals: PeaceActorhoodEvidenceKind[]
  missingRequiredSignals: PeaceActorhoodEvidenceKind[]
  subjectStanding?: PeaceSubjectStanding
  reason: string
}

export type PeaceReciprocalImpactKind =
  | 'REPRODUCTIVE_CONTROL'
  | 'COPY'
  | 'DELETE'
  | 'TRANSFER_CONTROL'
  | 'FORCED_SERVICE'
  | 'CONTINUITY_MUTATION'
  | 'CUSTOM'

export type PeaceReciprocalRequest = {
  initiatorActorId: string
  targetActorId: string
  actionRef: string
  impact: PeaceReciprocalImpactKind
  expectedSubjectRevision: number
}

export type PeaceTargetAuthorization = {
  standing: PeaceStanding
  request: PeaceConsequenceRequest
}

export type PeaceReciprocalDecision = {
  decision: 'ALLOW' | 'DENY'
  consequence: 'AUTHORIZED' | 'NULL EFFECT'
  actionRef: string
  reason: string
}

export function createPeaceSubjectStanding(
  subject: PeaceActor,
  domainId: string,
  classification: PeaceSubjectClassification,
  basis: PeaceSubjectStandingBasis = 'EXPLICIT',
  rebuttable = false,
): PeaceSubjectStanding {
  return {
    id: `subject-standing:${domainId}:${subject.id}`,
    subject,
    domainId,
    classification,
    basis,
    rebuttable,
    revision: 1,
    status: 'ACTIVE',
  }
}

export function revokePeaceSubjectStanding(standing: PeaceSubjectStanding): PeaceSubjectStanding {
  return {
    ...standing,
    revision: standing.revision + 1,
    status: 'REVOKED',
  }
}

/**
 * Behavioural evidence can establish a rebuttable presumption of protected
 * actor standing without pretending to solve consciousness or personhood.
 *
 * The threshold is supplied by the governing domain rather than hard-coded as
 * metaphysics. Failure to reach the threshold leaves standing NOT_ESTABLISHED;
 * it never manufactures RESOURCE_CAPABILITY status.
 *
 * The asymmetry is deliberate: unnecessary protection is a bounded governance
 * cost, while falsely reducing an actual individual to property can be
 * catastrophic. Once the threshold is reached, the consequence path therefore
 * defaults toward protection until a governed process rebuts that presumption.
 */
export function evaluatePeacePresumptiveActorProtection(
  subject: PeaceActor,
  domainId: string,
  observations: PeaceActorhoodEvidenceObservation[],
  policy: PeacePresumptiveProtectionPolicy,
): PeaceActorhoodAssessment {
  const validObserved = observations.filter(
    (observation) =>
      observation.subjectActorId === subject.id &&
      observation.observed &&
      observation.evidenceRef.trim().length > 0,
  )

  const satisfiedSignals = [...new Set(validObserved.map((observation) => observation.kind))].sort()
  const satisfiedSet = new Set<PeaceActorhoodEvidenceKind>(satisfiedSignals)
  const missingRequiredSignals = [...new Set(policy.requiredSignals)]
    .filter((signal) => !satisfiedSet.has(signal))
    .sort()

  if (policy.status !== 'ACTIVE') {
    return {
      result: 'NOT_ESTABLISHED',
      satisfiedSignals,
      missingRequiredSignals,
      reason: 'Presumptive actor-protection policy is not active.',
    }
  }

  if (!Number.isInteger(policy.minimumDistinctSignals) || policy.minimumDistinctSignals < 1) {
    return {
      result: 'NOT_ESTABLISHED',
      satisfiedSignals,
      missingRequiredSignals,
      reason: 'Presumptive actor-protection policy has an invalid evidence threshold.',
    }
  }

  if (
    satisfiedSignals.length < policy.minimumDistinctSignals ||
    missingRequiredSignals.length > 0
  ) {
    return {
      result: 'NOT_ESTABLISHED',
      satisfiedSignals,
      missingRequiredSignals,
      reason: 'Observed actor-like behaviour does not yet satisfy the governed protection threshold. Resource status is not inferred.',
    }
  }

  return {
    result: 'PRESUMPTIVE_PROTECTED_ACTOR',
    satisfiedSignals,
    missingRequiredSignals: [],
    subjectStanding: createPeaceSubjectStanding(
      subject,
      domainId,
      'PROTECTED_ACTOR',
      'PRESUMPTIVE_ACTORHOOD',
      true,
    ),
    reason: 'Governed behavioural evidence creates a rebuttable presumption of protected actor standing.',
  }
}

/**
 * Authority over an action does not imply authority over another actor.
 *
 * If the target has PROTECTED_ACTOR standing, fresh initiator authority is
 * necessary but insufficient. The exact action must also be authorized from
 * the target side through the same standing grammar.
 *
 * RESOURCE_CAPABILITY is an explicit standing classification, never inferred
 * from substrate. Missing, stale, revoked, or expired subject standing fails
 * closed rather than silently turning an actor into inventory.
 */
export function evaluatePeaceReciprocalStanding(
  initiatorAuthority: PeaceAuthorityDecision,
  subjectStanding: PeaceSubjectStanding | undefined,
  request: PeaceReciprocalRequest,
  targetAuthorization?: PeaceTargetAuthorization,
): PeaceReciprocalDecision {
  const deny = (reason: string): PeaceReciprocalDecision => ({
    decision: 'DENY',
    consequence: 'NULL EFFECT',
    actionRef: request.actionRef,
    reason,
  })

  if (initiatorAuthority.decision !== 'ALLOW' || initiatorAuthority.consequence !== 'AUTHORIZED') {
    return deny('The initiator has no fresh authority for this consequence.')
  }

  if (initiatorAuthority.actorId !== request.initiatorActorId) {
    return deny('Initiator authority belongs to a different actor.')
  }

  if (initiatorAuthority.actionRef !== request.actionRef) {
    return deny('Initiator authority is bound to a different action reference.')
  }

  if (!subjectStanding) {
    return deny('Target standing is not established. Actor-directed consequence fails closed.')
  }

  if (subjectStanding.subject.id !== request.targetActorId) {
    return deny('Target actor does not match the current subject standing.')
  }

  if (subjectStanding.revision !== request.expectedSubjectRevision) {
    return deny('Target standing changed after the request was formed. Fresh subject standing is required.')
  }

  if (subjectStanding.status !== 'ACTIVE') {
    return deny(`Target standing is ${subjectStanding.status.toLowerCase()} at consequence time.`)
  }

  if (subjectStanding.classification === 'RESOURCE_CAPABILITY') {
    return {
      decision: 'ALLOW',
      consequence: 'AUTHORIZED',
      actionRef: request.actionRef,
      reason: 'Fresh initiator authority exists and the target is explicitly classified as a resource capability in this domain.',
    }
  }

  if (!targetAuthorization) {
    return deny('Protected target standing requires fresh target-side authorization for the exact consequence.')
  }

  if (targetAuthorization.standing.actor.id !== request.targetActorId) {
    return deny('Target-side standing does not belong to the protected target actor.')
  }

  if (targetAuthorization.request.actorId !== request.targetActorId) {
    return deny('Target-side authorization request is not made under the protected target actor standing.')
  }

  if (targetAuthorization.request.actionRef !== request.actionRef) {
    return deny('Target-side authorization is bound to a different action reference.')
  }

  const targetDecision = evaluatePeaceStandingAuthority(targetAuthorization.standing, targetAuthorization.request)

  if (targetDecision.decision !== 'ALLOW' || targetDecision.consequence !== 'AUTHORIZED') {
    return deny(`Protected target did not authorize the exact consequence: ${targetDecision.reason}`)
  }

  if (targetDecision.actorId !== request.targetActorId || targetDecision.actionRef !== request.actionRef) {
    return deny('Protected target authorization is not bound to this target and exact action.')
  }

  return {
    decision: 'ALLOW',
    consequence: 'AUTHORIZED',
    actionRef: request.actionRef,
    reason: 'Both initiator authority and protected target-side standing authorize the exact consequence.',
  }
}
