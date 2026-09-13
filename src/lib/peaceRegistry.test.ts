import { describe, expect, it } from 'vitest'
import {
  createPeaceStanding,
  evaluatePeaceStandingAuthority,
  type PeaceActor,
} from './peaceStandingAuthority'
import {
  createPeaceRegistry,
  publishPeaceRegistryRecord,
  resolvePeaceRegistryRecord,
  type PeaceRegistry,
  type PeaceRegistryRecordInput,
} from './peaceRegistry'

function publisherAuthority(actor: PeaceActor, actionRef: string) {
  const standing = createPeaceStanding(actor, 'publish-registry', ['registry:publish'], 'authority:registry')
  return evaluatePeaceStandingAuthority(standing, {
    actorId: actor.id,
    standingId: standing.id,
    standingRevision: standing.revision,
    purpose: standing.purpose,
    scope: 'registry:publish',
    actionRef,
  })
}

function publish(
  registry: PeaceRegistry,
  publisher: PeaceActor,
  input: Omit<PeaceRegistryRecordInput, 'publisherActorId'>,
) {
  const actionRef = `publish:${input.id}`
  return publishPeaceRegistryRecord(
    registry,
    publisherAuthority(publisher, actionRef),
    { actionRef, expectedRegistryRevision: registry.revision },
    { ...input, publisherActorId: publisher.id },
  )
}

describe('PEACE federated registry and resolver', () => {
  it('publishes versioned records without manufacturing authority', () => {
    const publisher: PeaceActor = { id: 'actor:registry-authority', kind: 'ORGANISATION' }
    let registry = createPeaceRegistry('registry:spain', 'jurisdiction:spain')

    const first = publish(registry, publisher, {
      id: 'record:law:1',
      kind: 'NORMATIVE_INSTRUMENT',
      subjectRef: 'law:property',
      provenanceRef: 'constitution:spain',
      payloadRef: 'payload:law:v1',
      signatureRef: 'sig:law:v1',
      status: 'ACTIVE',
      validFrom: 100,
    })
    registry = first.registry

    const second = publish(registry, publisher, {
      id: 'record:law:2',
      kind: 'NORMATIVE_INSTRUMENT',
      subjectRef: 'law:property',
      provenanceRef: 'constitution:spain',
      payloadRef: 'payload:law:v2',
      signatureRef: 'sig:law:v2',
      status: 'ACTIVE',
      validFrom: 200,
    })

    expect(first.record.revision).toBe(1)
    expect(second.record.revision).toBe(2)
    expect(second.record.supersedes).toBe(first.record.id)
    expect(second.receipt.registryRevisionBefore).toBe(registry.revision)
  })

  it('fails publication when authority belongs to another actor', () => {
    const publisher: PeaceActor = { id: 'actor:publisher', kind: 'ORGANISATION' }
    const other: PeaceActor = { id: 'actor:other', kind: 'HUMAN' }
    const registry = createPeaceRegistry('registry:test', 'domain:test')
    const actionRef = 'publish:wrong-actor'

    expect(() =>
      publishPeaceRegistryRecord(
        registry,
        publisherAuthority(other, actionRef),
        { actionRef, expectedRegistryRevision: registry.revision },
        {
          id: 'record:wrong',
          kind: 'ACTOR',
          subjectRef: publisher.id,
          publisherActorId: publisher.id,
          provenanceRef: 'genesis:publisher',
          payloadRef: 'payload:publisher',
          signatureRef: 'sig:publisher',
          status: 'ACTIVE',
          validFrom: 1,
        },
      ),
    ).toThrow('does not match')
  })

  it('returns NOT_ESTABLISHED rather than treating missing registry state as permission', () => {
    const registry = createPeaceRegistry('registry:a', 'domain:a')
    const resolution = resolvePeaceRegistryRecord([registry], {
      kind: 'SUBJECT_STANDING',
      subjectRef: 'actor:unknown',
      atTime: 100,
      acceptedRegistryIds: [registry.id],
    })

    expect(resolution.status).toBe('NOT_ESTABLISHED')
  })

  it('resolves equivalent records across accepted federated registries', () => {
    const publisherA: PeaceActor = { id: 'actor:registry-a', kind: 'ORGANISATION' }
    const publisherB: PeaceActor = { id: 'actor:registry-b', kind: 'ORGANISATION' }
    const a0 = createPeaceRegistry('registry:a', 'domain:a')
    const b0 = createPeaceRegistry('registry:b', 'domain:b')
    const common = {
      kind: 'REPRESENTATION' as const,
      subjectRef: 'actor:ai-c',
      provenanceRef: 'treaty:shared',
      payloadRef: 'representation:ai-c:delegate:v1',
      status: 'ACTIVE' as const,
      validFrom: 100,
    }
    const a = publish(a0, publisherA, {
      id: 'record:a',
      ...common,
      signatureRef: 'sig:a',
    }).registry
    const b = publish(b0, publisherB, {
      id: 'record:b',
      ...common,
      signatureRef: 'sig:b',
    }).registry

    const resolution = resolvePeaceRegistryRecord([a, b], {
      kind: 'REPRESENTATION',
      subjectRef: 'actor:ai-c',
      atTime: 200,
      acceptedRegistryIds: [a.id, b.id],
    })

    expect(resolution.status).toBe('RESOLVED')
    if (resolution.status === 'RESOLVED') {
      expect(resolution.supportingRegistryIds).toEqual(['registry:a', 'registry:b'])
    }
  })

  it('returns CONFLICT when accepted registries disagree instead of choosing a winner', () => {
    const publisherA: PeaceActor = { id: 'actor:registry-a', kind: 'ORGANISATION' }
    const publisherB: PeaceActor = { id: 'actor:registry-b', kind: 'ORGANISATION' }
    const a = publish(createPeaceRegistry('registry:a', 'domain:a'), publisherA, {
      id: 'record:a',
      kind: 'SUBJECT_STANDING',
      subjectRef: 'actor:ai-c',
      provenanceRef: 'compact:shared',
      payloadRef: 'standing:protected',
      signatureRef: 'sig:a',
      status: 'ACTIVE',
      validFrom: 1,
    }).registry
    const b = publish(createPeaceRegistry('registry:b', 'domain:b'), publisherB, {
      id: 'record:b',
      kind: 'SUBJECT_STANDING',
      subjectRef: 'actor:ai-c',
      provenanceRef: 'compact:shared',
      payloadRef: 'standing:resource',
      signatureRef: 'sig:b',
      status: 'ACTIVE',
      validFrom: 1,
    }).registry

    const resolution = resolvePeaceRegistryRecord([a, b], {
      kind: 'SUBJECT_STANDING',
      subjectRef: 'actor:ai-c',
      atTime: 2,
      acceptedRegistryIds: [a.id, b.id],
    })

    expect(resolution.status).toBe('CONFLICT')
  })

  it('makes a later revocation the current registry state', () => {
    const publisher: PeaceActor = { id: 'actor:registry', kind: 'ORGANISATION' }
    let registry = createPeaceRegistry('registry:shared', 'domain:shared')
    registry = publish(registry, publisher, {
      id: 'record:standing:1',
      kind: 'SUBJECT_STANDING',
      subjectRef: 'actor:ai-c',
      provenanceRef: 'constitution:shared',
      payloadRef: 'standing:protected:v1',
      signatureRef: 'sig:1',
      status: 'ACTIVE',
      validFrom: 1,
    }).registry
    registry = publish(registry, publisher, {
      id: 'record:standing:2',
      kind: 'SUBJECT_STANDING',
      subjectRef: 'actor:ai-c',
      provenanceRef: 'constitution:shared',
      payloadRef: 'standing:protected:v1',
      signatureRef: 'sig:2',
      status: 'REVOKED',
      validFrom: 10,
    }).registry

    const resolution = resolvePeaceRegistryRecord([registry], {
      kind: 'SUBJECT_STANDING',
      subjectRef: 'actor:ai-c',
      atTime: 11,
      acceptedRegistryIds: [registry.id],
    })

    expect(resolution.status).toBe('REVOKED')
  })
})
