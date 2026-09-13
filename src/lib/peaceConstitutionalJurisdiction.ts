import type { PeaceAuthorityDecision } from './peaceStandingAuthority'

export type PeaceConstitutionStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED'

export type PeaceConstitutionalAmendmentPolicy = {
  standingId: string
  allowSelfBenefit: boolean
}

export type PeaceConstitution = {
  id: string
  domainId: string
  genesisRef: string
  revision: number
  status: PeaceConstitutionStatus
  amendmentPolicy: PeaceConstitutionalAmendmentPolicy
  amendmentHistory: readonly string[]
}

export type PeaceConstitutionAmendmentRequest = {
  actionRef: string
  expectedRevision: number
  beneficiaryActorIds: readonly string[]
  note: string
}

export type PeaceConstitutionalDecision = {
  decision: 'ALLOW' | 'DENY'
  consequence: 'AUTHORIZED' | 'NULL EFFECT'
  actionRef: string
  reason: string
}

export type PeaceConstitutionalReceipt = {
  constitutionId: string
  actionRef: string
  revisionBefore: number
  revisionAfter: number
  authorityActorId: string
  note: string
}

export function createPeaceConstitution(
  id: string,
  domainId: string,
  genesisRef: string,
  amendmentPolicy: PeaceConstitutionalAmendmentPolicy,
): PeaceConstitution {
  return {
    id,
    domainId,
    genesisRef,
    revision: 1,
    status: 'ACTIVE',
    amendmentPolicy: { ...amendmentPolicy },
    amendmentHistory: [],
  }
}

/**
 * Constitutional rules have explicit provenance and an explicit amendment path.
 * There is no invisible actor above the constitution and no implicit right to
 * rewrite the rules merely because an actor currently benefits from them.
 */
export function evaluatePeaceConstitutionAmendment(
  constitution: PeaceConstitution,
  authority: PeaceAuthorityDecision,
  request: PeaceConstitutionAmendmentRequest,
): PeaceConstitutionalDecision {
  const deny = (reason: string): PeaceConstitutionalDecision => ({
    decision: 'DENY',
    consequence: 'NULL EFFECT',
    actionRef: request.actionRef,
    reason,
  })

  if (constitution.status !== 'ACTIVE') {
    return deny(`Constitution is ${constitution.status.toLowerCase()} at amendment time.`)
  }

  if (request.expectedRevision !== constitution.revision) {
    return deny('Constitution changed after the amendment request was formed.')
  }

  if (authority.decision !== 'ALLOW' || authority.consequence !== 'AUTHORIZED') {
    return deny('No fresh authority exists for this constitutional amendment.')
  }

  if (authority.actionRef !== request.actionRef) {
    return deny('Amendment authority is bound to a different action reference.')
  }

  if (authority.standingId !== constitution.amendmentPolicy.standingId) {
    return deny('Authority does not satisfy the constitutionally declared amendment standing.')
  }

  if (
    !constitution.amendmentPolicy.allowSelfBenefit &&
    request.beneficiaryActorIds.includes(authority.actorId)
  ) {
    return deny('Constitution forbids an amendment authority from widening rules for its own benefit.')
  }

  return {
    decision: 'ALLOW',
    consequence: 'AUTHORIZED',
    actionRef: request.actionRef,
    reason: 'Fresh authority satisfies the constitutionally declared amendment procedure.',
  }
}

export function admitPeaceConstitutionAmendment(
  constitution: PeaceConstitution,
  authority: PeaceAuthorityDecision,
  request: PeaceConstitutionAmendmentRequest,
  decision: PeaceConstitutionalDecision,
): { constitution: PeaceConstitution; receipt: PeaceConstitutionalReceipt } {
  if (decision.decision !== 'ALLOW' || decision.consequence !== 'AUTHORIZED') {
    throw new Error('Cannot admit a denied constitutional amendment.')
  }

  if (request.expectedRevision !== constitution.revision) {
    throw new Error('Cannot admit an amendment against stale constitutional state.')
  }

  const next: PeaceConstitution = {
    ...constitution,
    revision: constitution.revision + 1,
    amendmentHistory: [...constitution.amendmentHistory, request.actionRef],
  }

  return {
    constitution: next,
    receipt: {
      constitutionId: constitution.id,
      actionRef: request.actionRef,
      revisionBefore: constitution.revision,
      revisionAfter: next.revision,
      authorityActorId: authority.actorId,
      note: request.note,
    },
  }
}

export type PeaceNormativeSourceKind = 'CONSTITUTION' | 'LAW' | 'TREATY' | 'CONTRACT'
export type PeaceNormativeEffect = 'ALLOW' | 'DENY' | 'REQUIRE_ADJUDICATION'
export type PeaceNormativeStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED'

export type PeaceNormativeInstrument = {
  id: string
  kind: PeaceNormativeSourceKind
  issuerDomainId: string
  jurisdictionRef: string
  provenanceRef: string
  revision: number
  status: PeaceNormativeStatus
  consequenceScopes: readonly string[]
  effect: PeaceNormativeEffect
}

export function createPeaceNormativeInstrument(
  instrument: Omit<PeaceNormativeInstrument, 'revision' | 'status'>,
): PeaceNormativeInstrument {
  if (instrument.provenanceRef.trim().length === 0) {
    throw new Error('Normative instruments require explicit constitutional or legal provenance.')
  }

  if (instrument.consequenceScopes.length === 0) {
    throw new Error('Normative instruments require at least one governed consequence scope.')
  }

  return {
    ...instrument,
    consequenceScopes: [...instrument.consequenceScopes],
    revision: 1,
    status: 'ACTIVE',
  }
}

export type PeaceRepresentationStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED'

export type PeaceRepresentationGrant = {
  id: string
  representedRef: string
  representativeActorId: string
  jurisdictionRef: string
  sourceInstrumentId: string
  scopes: readonly string[]
  revision: number
  status: PeaceRepresentationStatus
}

export type PeaceRepresentationRequest = {
  representedRef: string
  representativeActorId: string
  scope: string
  expectedRevision: number
}

export type PeaceRepresentationDecision = {
  decision: 'ALLOW' | 'DENY'
  reason: string
}

/**
 * Representation is explicit and scoped. It does not create ownership and it
 * does not manufacture consequence authority for the representative.
 */
export function createPeaceRepresentationGrant(
  grant: Omit<PeaceRepresentationGrant, 'revision' | 'status'>,
): PeaceRepresentationGrant {
  if (grant.representedRef === '*' || grant.representedRef.trim().length === 0) {
    throw new Error('Representation must bind an explicit actor or governed collective reference.')
  }

  return {
    ...grant,
    scopes: [...grant.scopes],
    revision: 1,
    status: 'ACTIVE',
  }
}

export function evaluatePeaceRepresentation(
  grant: PeaceRepresentationGrant,
  request: PeaceRepresentationRequest,
): PeaceRepresentationDecision {
  if (grant.status !== 'ACTIVE') {
    return { decision: 'DENY', reason: `Representation is ${grant.status.toLowerCase()}.` }
  }

  if (request.expectedRevision !== grant.revision) {
    return { decision: 'DENY', reason: 'Representation changed after the request was formed.' }
  }

  if (
    request.representedRef !== grant.representedRef ||
    request.representativeActorId !== grant.representativeActorId
  ) {
    return { decision: 'DENY', reason: 'Representation does not bind these exact parties.' }
  }

  if (!grant.scopes.includes(request.scope)) {
    return { decision: 'DENY', reason: 'Requested representation is outside the granted scope.' }
  }

  return {
    decision: 'ALLOW',
    reason: 'The representative may represent this explicit actor or collective for the declared scope only.',
  }
}

export type PeaceLegalConsequenceRequest = {
  actorId: string
  actionRef: string
  consequenceScope: string
  jurisdictionRefs: readonly string[]
  expectedAdjudicationRevision?: number
}

export type PeaceAdjudicationOutcome = {
  id: string
  actionRef: string
  bindingInstrumentIds: readonly string[]
  jurisdictionRefs: readonly string[]
  revision: number
  status: 'ACTIVE' | 'REVOKED' | 'EXPIRED'
  decision: 'ALLOW' | 'DENY'
}

export type PeaceLegalDecision = {
  decision: 'ALLOW' | 'DENY' | 'DEFER'
  consequence: 'AUTHORIZED' | 'NULL EFFECT'
  actionRef: string
  applicableInstrumentIds: readonly string[]
  jurisdictionRefs: readonly string[]
  reason: string
}

function sameSet(left: readonly string[], right: readonly string[]): boolean {
  if (left.length !== right.length) return false
  const rightSet = new Set(right)
  return left.every((value) => rightSet.has(value))
}

function matchesScope(instrument: PeaceNormativeInstrument, consequenceScope: string): boolean {
  return instrument.consequenceScopes.includes('*') || instrument.consequenceScopes.includes(consequenceScope)
}

/**
 * Jurisdiction is resolved over the consequence, not over actor substrate.
 * Multiple houses can bind the same action. Conflicting applicable rules do
 * not collapse into arbitrary hierarchy; they defer to explicit adjudication.
 */
export function evaluatePeaceLegalAdmissibility(
  authority: PeaceAuthorityDecision,
  request: PeaceLegalConsequenceRequest,
  instruments: readonly PeaceNormativeInstrument[],
  adjudication?: PeaceAdjudicationOutcome,
): PeaceLegalDecision {
  const applicable = instruments.filter(
    (instrument) =>
      instrument.status === 'ACTIVE' &&
      request.jurisdictionRefs.includes(instrument.jurisdictionRef) &&
      matchesScope(instrument, request.consequenceScope),
  )
  const applicableIds = applicable.map((instrument) => instrument.id)

  const decision = (
    result: PeaceLegalDecision['decision'],
    consequence: PeaceLegalDecision['consequence'],
    reason: string,
  ): PeaceLegalDecision => ({
    decision: result,
    consequence,
    actionRef: request.actionRef,
    applicableInstrumentIds: applicableIds,
    jurisdictionRefs: [...request.jurisdictionRefs],
    reason,
  })

  if (authority.decision !== 'ALLOW' || authority.consequence !== 'AUTHORIZED') {
    return decision('DENY', 'NULL EFFECT', 'Legal admissibility cannot manufacture missing actor authority.')
  }

  if (authority.actorId !== request.actorId || authority.actionRef !== request.actionRef) {
    return decision('DENY', 'NULL EFFECT', 'Fresh authority is not bound to this actor and exact legal consequence.')
  }

  if (applicable.length === 0) {
    return decision('DEFER', 'NULL EFFECT', 'No applicable jurisdiction has been established for this consequence.')
  }

  const effects = new Set(applicable.map((instrument) => instrument.effect))
  const requiresAdjudication = effects.size > 1 || effects.has('REQUIRE_ADJUDICATION')

  if (requiresAdjudication) {
    if (!adjudication) {
      return decision('DEFER', 'NULL EFFECT', 'Applicable jurisdictions conflict or require adjudication.')
    }

    if (adjudication.status !== 'ACTIVE' || adjudication.actionRef !== request.actionRef) {
      return decision('DEFER', 'NULL EFFECT', 'Adjudication is stale, inactive, or bound to a different action.')
    }

    if (
      request.expectedAdjudicationRevision !== undefined &&
      request.expectedAdjudicationRevision !== adjudication.revision
    ) {
      return decision('DEFER', 'NULL EFFECT', 'Adjudication changed after the request was formed.')
    }

    if (
      !sameSet(adjudication.bindingInstrumentIds, applicableIds) ||
      !sameSet(adjudication.jurisdictionRefs, request.jurisdictionRefs)
    ) {
      return decision('DEFER', 'NULL EFFECT', 'Adjudication does not resolve the exact applicable jurisdiction set.')
    }

    if (adjudication.decision === 'DENY') {
      return decision('DENY', 'NULL EFFECT', 'Binding adjudication denies the exact consequence.')
    }

    return decision('ALLOW', 'AUTHORIZED', 'Binding adjudication admits the exact consequence across jurisdictions.')
  }

  const onlyEffect = applicable[0].effect
  if (onlyEffect === 'DENY') {
    return decision('DENY', 'NULL EFFECT', 'Every applicable normative instrument denies this consequence.')
  }

  return decision('ALLOW', 'AUTHORIZED', 'Every applicable normative instrument admits this consequence.')
}

export type PeaceEnforcementBinding = {
  id: string
  effectorActorId: string
  jurisdictionRef: string
  consequenceScopes: readonly string[]
  revision: number
  status: 'ACTIVE' | 'REVOKED' | 'EXPIRED'
}

export type PeaceEnforcementRequest = {
  executorActorId: string
  actionRef: string
  consequenceScope: string
  expectedBindingRevision: number
}

export type PeaceEnforcementDecision = {
  decision: 'ALLOW' | 'DENY'
  consequence: 'EFFECT PERMITTED' | 'NULL EFFECT'
  reason: string
}

/**
 * Law is not self-executing. The designated effector must hold the binding
 * for the exact consequence after legal admissibility has resolved to ALLOW.
 */
export function evaluatePeaceEnforcement(
  binding: PeaceEnforcementBinding,
  legal: PeaceLegalDecision,
  request: PeaceEnforcementRequest,
): PeaceEnforcementDecision {
  const deny = (reason: string): PeaceEnforcementDecision => ({
    decision: 'DENY',
    consequence: 'NULL EFFECT',
    reason,
  })

  if (legal.decision !== 'ALLOW' || legal.consequence !== 'AUTHORIZED') {
    return deny('The consequence has no resolved legal admissibility.')
  }

  if (legal.actionRef !== request.actionRef) {
    return deny('Legal admissibility is bound to a different action reference.')
  }

  if (binding.status !== 'ACTIVE' || binding.revision !== request.expectedBindingRevision) {
    return deny('Enforcement binding is stale or inactive.')
  }

  if (binding.effectorActorId !== request.executorActorId) {
    return deny('Executor is not the designated effector for this consequence.')
  }

  if (!legal.jurisdictionRefs.includes(binding.jurisdictionRef)) {
    return deny('Enforcement binding belongs to a jurisdiction outside the resolved legal consequence.')
  }

  if (
    !binding.consequenceScopes.includes('*') &&
    !binding.consequenceScopes.includes(request.consequenceScope)
  ) {
    return deny('Consequence is outside the effector binding scope.')
  }

  return {
    decision: 'ALLOW',
    consequence: 'EFFECT PERMITTED',
    reason: 'Resolved law and the designated effector binding permit this exact consequence.',
  }
}
