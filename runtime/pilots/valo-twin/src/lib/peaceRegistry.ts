import type { PeaceAuthorityDecision } from './peaceStandingAuthority'

export type PeaceRegistryRecordKind =
  | 'ACTOR'
  | 'DOMAIN'
  | 'GENESIS'
  | 'CONSTITUTION'
  | 'NORMATIVE_INSTRUMENT'
  | 'REPRESENTATION'
  | 'SUBJECT_STANDING'
  | 'ADJUDICATION'
  | 'ENFORCEMENT_BINDING'
  | 'TRAJECTORY_ENVELOPE'

export type PeaceRegistryRecordStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED'

export type PeaceRegistryRecord = {
  id: string
  registryId: string
  kind: PeaceRegistryRecordKind
  subjectRef: string
  publisherActorId: string
  provenanceRef: string
  payloadRef: string
  signatureRef: string
  revision: number
  status: PeaceRegistryRecordStatus
  validFrom: number
  validUntil?: number
  supersedes?: string
}

export type PeaceRegistry = {
  id: string
  domainId: string
  revision: number
  records: readonly PeaceRegistryRecord[]
}

export type PeaceRegistryPublishRequest = {
  actionRef: string
  expectedRegistryRevision: number
}

export type PeaceRegistryRecordInput = Omit<
  PeaceRegistryRecord,
  'registryId' | 'revision' | 'supersedes'
>

export type PeaceRegistryPublishReceipt = {
  registryId: string
  actionRef: string
  recordId: string
  registryRevisionBefore: number
  registryRevisionAfter: number
  recordRevision: number
}

export function createPeaceRegistry(id: string, domainId: string): PeaceRegistry {
  return {
    id,
    domainId,
    revision: 1,
    records: [],
  }
}

function latestRecordFor(
  registry: PeaceRegistry,
  kind: PeaceRegistryRecordKind,
  subjectRef: string,
): PeaceRegistryRecord | undefined {
  return registry.records
    .filter((record) => record.kind === kind && record.subjectRef === subjectRef)
    .sort((left, right) => right.revision - left.revision)[0]
}

/**
 * A registry publishes evidence about governed state. It does not create the
 * authority represented by that state. Publication therefore requires fresh
 * authority for the exact registry action and explicit provenance/signature
 * references. Production implementations must verify the referenced
 * cryptographic signatures outside this deterministic demo.
 */
export function publishPeaceRegistryRecord(
  registry: PeaceRegistry,
  authority: PeaceAuthorityDecision,
  request: PeaceRegistryPublishRequest,
  input: PeaceRegistryRecordInput,
): { registry: PeaceRegistry; receipt: PeaceRegistryPublishReceipt; record: PeaceRegistryRecord } {
  if (authority.decision !== 'ALLOW' || authority.consequence !== 'AUTHORIZED') {
    throw new Error('Registry publication requires fresh authority.')
  }

  if (authority.actionRef !== request.actionRef) {
    throw new Error('Registry publication authority is bound to a different action reference.')
  }

  if (authority.actorId !== input.publisherActorId) {
    throw new Error('Registry publisher does not match the actor holding publication authority.')
  }

  if (request.expectedRegistryRevision !== registry.revision) {
    throw new Error('Registry changed after the publication request was formed.')
  }

  if (input.provenanceRef.trim().length === 0 || input.signatureRef.trim().length === 0) {
    throw new Error('Registry records require explicit provenance and signature references.')
  }

  if (registry.records.some((record) => record.id === input.id)) {
    throw new Error('Registry record id already exists.')
  }

  if (!Number.isFinite(input.validFrom) || (input.validUntil !== undefined && !Number.isFinite(input.validUntil))) {
    throw new Error('Registry validity bounds must be finite.')
  }

  if (input.validUntil !== undefined && input.validUntil <= input.validFrom) {
    throw new Error('Registry validUntil must be later than validFrom.')
  }

  const previous = latestRecordFor(registry, input.kind, input.subjectRef)
  const record: PeaceRegistryRecord = {
    ...input,
    registryId: registry.id,
    revision: (previous?.revision ?? 0) + 1,
    supersedes: previous?.id,
  }
  const next: PeaceRegistry = {
    ...registry,
    revision: registry.revision + 1,
    records: [...registry.records, record],
  }

  return {
    registry: next,
    record,
    receipt: {
      registryId: registry.id,
      actionRef: request.actionRef,
      recordId: record.id,
      registryRevisionBefore: registry.revision,
      registryRevisionAfter: next.revision,
      recordRevision: record.revision,
    },
  }
}

export type PeaceRegistryQuery = {
  kind: PeaceRegistryRecordKind
  subjectRef: string
  atTime: number
  acceptedRegistryIds: readonly string[]
}

export type PeaceRegistryResolution =
  | {
      status: 'RESOLVED'
      record: PeaceRegistryRecord
      supportingRegistryIds: readonly string[]
      reason: string
    }
  | {
      status: 'NOT_ESTABLISHED' | 'REVOKED' | 'EXPIRED' | 'CONFLICT'
      candidates: readonly PeaceRegistryRecord[]
      reason: string
    }

function currentRecordAt(
  registry: PeaceRegistry,
  query: PeaceRegistryQuery,
): PeaceRegistryRecord | undefined {
  const latest = latestRecordFor(registry, query.kind, query.subjectRef)
  if (!latest) return undefined
  if (latest.validFrom > query.atTime) return undefined
  return latest
}

/**
 * The resolver is open-world and federated. No registry is a global sovereign.
 * Callers explicitly choose the registries whose records are admissible for
 * the current jurisdiction/domain. Missing data is NOT_ESTABLISHED; divergent
 * current records are CONFLICT and must not be converted into authority.
 */
export function resolvePeaceRegistryRecord(
  registries: readonly PeaceRegistry[],
  query: PeaceRegistryQuery,
): PeaceRegistryResolution {
  const accepted = registries.filter((registry) => query.acceptedRegistryIds.includes(registry.id))
  const candidates = accepted
    .map((registry) => currentRecordAt(registry, query))
    .filter((record): record is PeaceRegistryRecord => record !== undefined)

  if (candidates.length === 0) {
    return {
      status: 'NOT_ESTABLISHED',
      candidates: [],
      reason: 'No accepted registry establishes current state for this subject.',
    }
  }

  const expired = candidates.filter(
    (record) => record.validUntil !== undefined && record.validUntil <= query.atTime,
  )
  const live = candidates.filter(
    (record) => record.validUntil === undefined || record.validUntil > query.atTime,
  )

  if (live.length === 0 && expired.length > 0) {
    return {
      status: 'EXPIRED',
      candidates,
      reason: 'Every accepted current registry record has expired.',
    }
  }

  const revoked = live.filter((record) => record.status === 'REVOKED')
  const active = live.filter((record) => record.status === 'ACTIVE')

  if (active.length === 0 && revoked.length > 0) {
    return {
      status: 'REVOKED',
      candidates: live,
      reason: 'Every accepted live registry record is revoked.',
    }
  }

  if (active.length === 0) {
    return {
      status: 'NOT_ESTABLISHED',
      candidates: live,
      reason: 'No accepted live registry record establishes active state.',
    }
  }

  const first = active[0]
  const equivalent = active.every(
    (record) =>
      record.payloadRef === first.payloadRef &&
      record.provenanceRef === first.provenanceRef &&
      record.status === first.status,
  )

  if (!equivalent || revoked.length > 0) {
    return {
      status: 'CONFLICT',
      candidates: live,
      reason: 'Accepted registries disagree about current state; explicit resolution is required.',
    }
  }

  return {
    status: 'RESOLVED',
    record: first,
    supportingRegistryIds: active.map((record) => record.registryId),
    reason: 'Accepted registries resolve the same current governed-state reference.',
  }
}
