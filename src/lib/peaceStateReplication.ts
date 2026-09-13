export type PeaceReplicaKind = 'DEVICE' | 'HOME_NODE' | 'CLOUD_RECOVERY'

export type PeaceReplica = {
  replicaId: string
  kind: PeaceReplicaKind
  domainId: string
  admittedVersion: number
  admittedStateRoot: string
  lineageRoot: string
  online: boolean
  trustedForRecovery: boolean
}

export type PeaceStateTransitionCandidate = {
  transitionId: string
  domainId: string
  baseVersion: number
  baseStateRoot: string
  nextStateRoot: string
  purpose: string
  authorityFresh: boolean
  requiresExternalFreshness: boolean
}

export type PeaceAdmittedTransition = PeaceStateTransitionCandidate & {
  admittedVersion: number
  admissionReceipt: string
}

export type PeaceReplicationDecision =
  | {
      status: 'ADMIT'
      consequence: 'STATE_TRANSITION'
      transition: PeaceAdmittedTransition
      nextAuthority: PeaceLogicalAuthorityState
      reason: string
    }
  | {
      status: 'DENY' | 'DEFER'
      consequence: 'NULL_EFFECT'
      nextAuthority: PeaceLogicalAuthorityState
      reason: string
    }

export type PeaceLogicalAuthorityState = {
  domainId: string
  admittedVersion: number
  admittedStateRoot: string
  lineageRoot: string
  admittedTransitionIds: readonly string[]
}

export type PeaceReplicaSyncResult = {
  status: 'SYNCED' | 'NOOP' | 'CONFLICT'
  replica: PeaceReplica
  reason: string
}

export type PeaceRecoveryResult =
  | {
      status: 'RECOVERED'
      authority: PeaceLogicalAuthorityState
      sourceReplicaIds: readonly string[]
      reason: string
    }
  | {
      status: 'DENY'
      reason: string
    }

function digest(parts: readonly string[]): string {
  let hash = 2166136261
  const input = parts.join('\u001f')
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(16).padStart(8, '0')
}

export function createPeaceLogicalAuthorityState(domainId = 'domain:person:demo'): PeaceLogicalAuthorityState {
  return {
    domainId,
    admittedVersion: 1,
    admittedStateRoot: 'state:v1:7c4a2f',
    lineageRoot: 'lineage:v1:1a72d4',
    admittedTransitionIds: [],
  }
}

export function createPeaceReplica(
  authority: PeaceLogicalAuthorityState,
  replicaId: string,
  kind: PeaceReplicaKind,
  online = true,
  trustedForRecovery = kind !== 'DEVICE',
): PeaceReplica {
  return {
    replicaId,
    kind,
    domainId: authority.domainId,
    admittedVersion: authority.admittedVersion,
    admittedStateRoot: authority.admittedStateRoot,
    lineageRoot: authority.lineageRoot,
    online,
    trustedForRecovery,
  }
}

export function evaluatePeaceStateTransition(
  authority: PeaceLogicalAuthorityState,
  candidate: PeaceStateTransitionCandidate,
  online: boolean,
): PeaceReplicationDecision {
  if (candidate.domainId !== authority.domainId) {
    return {
      status: 'DENY',
      consequence: 'NULL_EFFECT',
      nextAuthority: authority,
      reason: 'Transition belongs to another governed domain.',
    }
  }

  if (authority.admittedTransitionIds.includes(candidate.transitionId)) {
    return {
      status: 'DENY',
      consequence: 'NULL_EFFECT',
      nextAuthority: authority,
      reason: 'Transition replay detected.',
    }
  }

  if (candidate.baseVersion !== authority.admittedVersion || candidate.baseStateRoot !== authority.admittedStateRoot) {
    return {
      status: 'DENY',
      consequence: 'NULL_EFFECT',
      nextAuthority: authority,
      reason: 'Replica is stale or divergent. PEACE never resolves this with last-write-wins.',
    }
  }

  if (!candidate.authorityFresh) {
    return {
      status: 'DENY',
      consequence: 'NULL_EFFECT',
      nextAuthority: authority,
      reason: 'Fresh authority is required before an authoritative state transition is admitted.',
    }
  }

  if (!online && candidate.requiresExternalFreshness) {
    return {
      status: 'DEFER',
      consequence: 'NULL_EFFECT',
      nextAuthority: authority,
      reason: 'Offline replica cannot establish required external freshness. Defer until authoritative sync is available.',
    }
  }

  const admittedVersion = authority.admittedVersion + 1
  const lineageRoot = `lineage:v${admittedVersion}:${digest([
    authority.lineageRoot,
    candidate.transitionId,
    candidate.baseStateRoot,
    candidate.nextStateRoot,
    candidate.purpose,
  ])}`
  const admissionReceipt = `receipt:${digest([
    candidate.transitionId,
    String(admittedVersion),
    candidate.nextStateRoot,
    lineageRoot,
  ])}`

  const transition: PeaceAdmittedTransition = {
    ...candidate,
    admittedVersion,
    admissionReceipt,
  }

  return {
    status: 'ADMIT',
    consequence: 'STATE_TRANSITION',
    transition,
    nextAuthority: {
      domainId: authority.domainId,
      admittedVersion,
      admittedStateRoot: candidate.nextStateRoot,
      lineageRoot,
      admittedTransitionIds: [...authority.admittedTransitionIds, candidate.transitionId],
    },
    reason: 'Transition admitted against the current logical authority state. Replicas may now copy the admitted result.',
  }
}

export function syncPeaceReplica(
  replica: PeaceReplica,
  authority: PeaceLogicalAuthorityState,
): PeaceReplicaSyncResult {
  if (replica.domainId !== authority.domainId) {
    return { status: 'CONFLICT', replica, reason: 'Replica belongs to another domain.' }
  }

  if (replica.admittedVersion > authority.admittedVersion) {
    return {
      status: 'CONFLICT',
      replica,
      reason: 'Replica claims a version beyond the accepted authority state. Newest bytes do not become sovereign.',
    }
  }

  if (
    replica.admittedVersion === authority.admittedVersion &&
    (replica.admittedStateRoot !== authority.admittedStateRoot || replica.lineageRoot !== authority.lineageRoot)
  ) {
    return {
      status: 'CONFLICT',
      replica,
      reason: 'Same-version lineage conflict. Do not silently merge or overwrite.',
    }
  }

  if (
    replica.admittedVersion === authority.admittedVersion &&
    replica.admittedStateRoot === authority.admittedStateRoot &&
    replica.lineageRoot === authority.lineageRoot
  ) {
    return { status: 'NOOP', replica, reason: 'Replica already matches admitted authority state.' }
  }

  return {
    status: 'SYNCED',
    replica: {
      ...replica,
      admittedVersion: authority.admittedVersion,
      admittedStateRoot: authority.admittedStateRoot,
      lineageRoot: authority.lineageRoot,
    },
    reason: 'Replica synchronized by copying admitted state and lineage, not by becoming the authority root.',
  }
}

export function recoverPeaceLogicalAuthorityState(replicas: readonly PeaceReplica[]): PeaceRecoveryResult {
  const eligible = replicas.filter((replica) => replica.trustedForRecovery)
  if (eligible.length < 2) {
    return {
      status: 'DENY',
      reason: 'Recovery requires at least two independent trusted recovery replicas in this demonstrator.',
    }
  }

  const groups = new Map<string, PeaceReplica[]>()
  for (const replica of eligible) {
    const key = `${replica.domainId}|${replica.admittedVersion}|${replica.admittedStateRoot}|${replica.lineageRoot}`
    groups.set(key, [...(groups.get(key) ?? []), replica])
  }

  const consensus = [...groups.values()]
    .filter((group) => group.length >= 2)
    .sort((left, right) => right[0].admittedVersion - left[0].admittedVersion)[0]

  if (!consensus) {
    return {
      status: 'DENY',
      reason: 'Trusted recovery replicas do not establish a matching admitted state and lineage.',
    }
  }

  const exemplar = consensus[0]
  return {
    status: 'RECOVERED',
    authority: {
      domainId: exemplar.domainId,
      admittedVersion: exemplar.admittedVersion,
      admittedStateRoot: exemplar.admittedStateRoot,
      lineageRoot: exemplar.lineageRoot,
      admittedTransitionIds: [],
    },
    sourceReplicaIds: consensus.map((replica) => replica.replicaId),
    reason: 'Logical authority reconstructed from matching trusted replicas. No storage location becomes sovereign by itself.',
  }
}
