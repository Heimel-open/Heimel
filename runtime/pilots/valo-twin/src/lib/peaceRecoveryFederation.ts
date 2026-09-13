export type RecoveryProviderId = string

export type RecoveryProviderCertification = {
  providerId: RecoveryProviderId
  certificationRef: string
  validFrom: number
  validUntil: number
  revoked: boolean
}

export type RecoveryProviderSlot = {
  slotId: string
  providerId: RecoveryProviderId
  opaquePeerSetRef: string
  activeFrom: number
  activeUntil: number
}

export type RecoveryFederationPolicy = {
  federationId: string
  minimumProviders: number
  quorum: number
  rotationEpoch: number
  requirePeerCompartmentalization: true
  requireDistinctOperators: true
  requireCertifiedProviders: true
}

export type RecoveryRequest = {
  requestId: string
  actorId: string
  requestedAt: number
  currentEpoch: number
  presentedProviders: readonly RecoveryProviderId[]
}

export type RecoveryDecision = {
  decision: 'ALLOW_RECOVERY' | 'DENY' | 'DEFER'
  reason: string
  admittedProviders: readonly RecoveryProviderId[]
}

export function evaluateRecoveryFederation(
  policy: RecoveryFederationPolicy,
  slots: readonly RecoveryProviderSlot[],
  certifications: readonly RecoveryProviderCertification[],
  request: RecoveryRequest,
): RecoveryDecision {
  if (policy.minimumProviders < 2 || policy.quorum < 2) {
    return {
      decision: 'DENY',
      reason: 'Recovery cannot depend on a single provider or single-party quorum.',
      admittedProviders: [],
    }
  }

  if (request.currentEpoch !== policy.rotationEpoch) {
    return {
      decision: 'DEFER',
      reason: 'Recovery request is bound to a stale federation rotation epoch.',
      admittedProviders: [],
    }
  }

  const uniquePresented = [...new Set(request.presentedProviders)]
  const admittedProviders = uniquePresented.filter((providerId) => {
    const slot = slots.find((candidate) => candidate.providerId === providerId)
    const certification = certifications.find((candidate) => candidate.providerId === providerId)

    if (!slot || !certification) return false
    if (certification.revoked) return false
    if (request.requestedAt < certification.validFrom || request.requestedAt > certification.validUntil) return false
    if (request.requestedAt < slot.activeFrom || request.requestedAt > slot.activeUntil) return false
    return true
  })

  if (admittedProviders.length < policy.quorum) {
    return {
      decision: 'DENY',
      reason: 'Certified independent recovery quorum was not established.',
      admittedProviders,
    }
  }

  return {
    decision: 'ALLOW_RECOVERY',
    reason:
      'A rotating quorum of currently certified recovery providers is established. No single provider is sufficient.',
    admittedProviders,
  }
}

export function validateRecoveryCompartmentalization(
  slots: readonly RecoveryProviderSlot[],
): { valid: boolean; reason: string } {
  const refs = slots.map((slot) => slot.opaquePeerSetRef)
  const uniqueRefs = new Set(refs)

  if (uniqueRefs.size !== refs.length) {
    return {
      valid: false,
      reason: 'Recovery providers must not share one discoverable peer-set reference.',
    }
  }

  return {
    valid: true,
    reason:
      'Each recovery provider receives only its own opaque membership reference; peer membership is not disclosed by the federation contract.',
  }
}

export function rotateRecoveryFederation(
  policy: RecoveryFederationPolicy,
  nextSlots: readonly RecoveryProviderSlot[],
): RecoveryFederationPolicy {
  if (nextSlots.length < policy.minimumProviders) {
    throw new Error('Rotation must preserve the configured minimum provider count.')
  }

  return {
    ...policy,
    rotationEpoch: policy.rotationEpoch + 1,
  }
}
