import { describe, expect, it } from 'vitest'
import {
  evaluateRecoveryFederation,
  rotateRecoveryFederation,
  validateRecoveryCompartmentalization,
  type RecoveryFederationPolicy,
  type RecoveryProviderCertification,
  type RecoveryProviderSlot,
} from './peaceRecoveryFederation'

const policy: RecoveryFederationPolicy = {
  federationId: 'recovery:peace:demo',
  minimumProviders: 3,
  quorum: 2,
  rotationEpoch: 7,
  requirePeerCompartmentalization: true,
  requireDistinctOperators: true,
  requireCertifiedProviders: true,
}

const slots: readonly RecoveryProviderSlot[] = [
  {
    slotId: 'slot:a',
    providerId: 'provider:a',
    opaquePeerSetRef: 'opaque:a:9f2c',
    activeFrom: 100,
    activeUntil: 300,
  },
  {
    slotId: 'slot:b',
    providerId: 'provider:b',
    opaquePeerSetRef: 'opaque:b:41ad',
    activeFrom: 100,
    activeUntil: 300,
  },
  {
    slotId: 'slot:c',
    providerId: 'provider:c',
    opaquePeerSetRef: 'opaque:c:77e1',
    activeFrom: 100,
    activeUntil: 300,
  },
]

const certifications: readonly RecoveryProviderCertification[] = slots.map((slot, index) => ({
  providerId: slot.providerId,
  certificationRef: `cert:${index + 1}`,
  validFrom: 50,
  validUntil: 400,
  revoked: false,
}))

describe('PEACE certified recovery federation', () => {
  it('never permits single-provider recovery', () => {
    const decision = evaluateRecoveryFederation(policy, slots, certifications, {
      requestId: 'recovery:1',
      actorId: 'actor:person:demo',
      requestedAt: 150,
      currentEpoch: 7,
      presentedProviders: ['provider:a'],
    })

    expect(decision.decision).toBe('DENY')
  })

  it('allows recovery only from a currently certified quorum', () => {
    const decision = evaluateRecoveryFederation(policy, slots, certifications, {
      requestId: 'recovery:2',
      actorId: 'actor:person:demo',
      requestedAt: 150,
      currentEpoch: 7,
      presentedProviders: ['provider:a', 'provider:b'],
    })

    expect(decision.decision).toBe('ALLOW_RECOVERY')
    expect(decision.admittedProviders).toEqual(['provider:a', 'provider:b'])
  })

  it('rejects a revoked recovery provider even when quorum would otherwise be met', () => {
    const revoked = certifications.map((certification) =>
      certification.providerId === 'provider:b'
        ? { ...certification, revoked: true }
        : certification,
    )

    const decision = evaluateRecoveryFederation(policy, slots, revoked, {
      requestId: 'recovery:3',
      actorId: 'actor:person:demo',
      requestedAt: 150,
      currentEpoch: 7,
      presentedProviders: ['provider:a', 'provider:b'],
    })

    expect(decision.decision).toBe('DENY')
    expect(decision.admittedProviders).toEqual(['provider:a'])
  })

  it('defers stale recovery epochs after provider rotation', () => {
    const nextPolicy = rotateRecoveryFederation(policy, slots)

    const decision = evaluateRecoveryFederation(nextPolicy, slots, certifications, {
      requestId: 'recovery:4',
      actorId: 'actor:person:demo',
      requestedAt: 150,
      currentEpoch: 7,
      presentedProviders: ['provider:a', 'provider:b'],
    })

    expect(nextPolicy.rotationEpoch).toBe(8)
    expect(decision.decision).toBe('DEFER')
  })

  it('keeps peer membership compartmentalized', () => {
    expect(validateRecoveryCompartmentalization(slots).valid).toBe(true)

    const compromised: readonly RecoveryProviderSlot[] = [
      slots[0],
      { ...slots[1], opaquePeerSetRef: slots[0].opaquePeerSetRef },
      slots[2],
    ]

    expect(validateRecoveryCompartmentalization(compromised).valid).toBe(false)
  })

  it('refuses rotations that collapse the federation below its minimum provider count', () => {
    expect(() => rotateRecoveryFederation(policy, slots.slice(0, 2))).toThrow(
      'Rotation must preserve the configured minimum provider count.',
    )
  })
})
