import { describe, expect, it } from 'vitest'
import {
  createPeaceLogicalAuthorityState,
  createPeaceReplica,
  evaluatePeaceStateTransition,
  recoverPeaceLogicalAuthorityState,
  syncPeaceReplica,
  type PeaceStateTransitionCandidate,
} from './peaceStateReplication'

function candidate(overrides: Partial<PeaceStateTransitionCandidate> = {}): PeaceStateTransitionCandidate {
  return {
    transitionId: 'transition:1',
    domainId: 'domain:person:demo',
    baseVersion: 1,
    baseStateRoot: 'state:v1:7c4a2f',
    nextStateRoot: 'state:v2:904fd1',
    purpose: 'admit-preference',
    authorityFresh: true,
    requiresExternalFreshness: false,
    ...overrides,
  }
}

describe('PEACE state replication', () => {
  it('admits a transition only against current logical authority state', () => {
    const authority = createPeaceLogicalAuthorityState()
    const result = evaluatePeaceStateTransition(authority, candidate(), true)

    expect(result.status).toBe('ADMIT')
    if (result.status !== 'ADMIT') throw new Error('expected ADMIT')
    expect(result.nextAuthority.admittedVersion).toBe(2)
    expect(result.nextAuthority.admittedStateRoot).toBe('state:v2:904fd1')
    expect(result.nextAuthority.lineageRoot).not.toBe(authority.lineageRoot)
  })

  it('rejects last-write-wins behavior from a stale replica', () => {
    const authority = createPeaceLogicalAuthorityState()
    const result = evaluatePeaceStateTransition(
      authority,
      candidate({ baseVersion: 0, baseStateRoot: 'state:stale' }),
      true,
    )

    expect(result.status).toBe('DENY')
    expect(result.consequence).toBe('NULL_EFFECT')
    expect(result.nextAuthority).toEqual(authority)
  })

  it('defers offline material transitions that require external freshness', () => {
    const authority = createPeaceLogicalAuthorityState()
    const result = evaluatePeaceStateTransition(
      authority,
      candidate({ requiresExternalFreshness: true }),
      false,
    )

    expect(result.status).toBe('DEFER')
    expect(result.consequence).toBe('NULL_EFFECT')
  })

  it('allows bounded offline transitions when freshness can be established locally', () => {
    const authority = createPeaceLogicalAuthorityState()
    const result = evaluatePeaceStateTransition(
      authority,
      candidate({ requiresExternalFreshness: false }),
      false,
    )

    expect(result.status).toBe('ADMIT')
  })

  it('syncs admitted state to replicas without promoting replicas to authority', () => {
    const authority = createPeaceLogicalAuthorityState()
    const phone = createPeaceReplica(authority, 'replica:phone', 'DEVICE')
    const admitted = evaluatePeaceStateTransition(authority, candidate(), true)
    if (admitted.status !== 'ADMIT') throw new Error('expected ADMIT')

    const synced = syncPeaceReplica(phone, admitted.nextAuthority)
    expect(synced.status).toBe('SYNCED')
    expect(synced.replica.admittedStateRoot).toBe(admitted.nextAuthority.admittedStateRoot)
    expect(synced.replica.replicaId).toBe('replica:phone')
  })

  it('detects same-version divergent lineage instead of silently merging', () => {
    const authority = createPeaceLogicalAuthorityState()
    const replica = {
      ...createPeaceReplica(authority, 'replica:laptop', 'DEVICE'),
      admittedStateRoot: 'state:v1:evil',
    }

    const synced = syncPeaceReplica(replica, authority)
    expect(synced.status).toBe('CONFLICT')
  })

  it('does not let newest bytes become sovereign', () => {
    const authority = createPeaceLogicalAuthorityState()
    const replica = {
      ...createPeaceReplica(authority, 'replica:phone', 'DEVICE'),
      admittedVersion: 99,
      admittedStateRoot: 'state:unadmitted',
      lineageRoot: 'lineage:unadmitted',
    }

    const synced = syncPeaceReplica(replica, authority)
    expect(synced.status).toBe('CONFLICT')
  })

  it('recovers logical authority from matching independent trusted replicas', () => {
    const authority = createPeaceLogicalAuthorityState()
    const home = createPeaceReplica(authority, 'replica:home', 'HOME_NODE')
    const cloud = createPeaceReplica(authority, 'replica:recovery', 'CLOUD_RECOVERY')
    const phone = createPeaceReplica(authority, 'replica:phone', 'DEVICE')

    const recovered = recoverPeaceLogicalAuthorityState([home, cloud, phone])
    expect(recovered.status).toBe('RECOVERED')
    if (recovered.status !== 'RECOVERED') throw new Error('expected RECOVERED')
    expect(recovered.authority.admittedStateRoot).toBe(authority.admittedStateRoot)
    expect(recovered.sourceReplicaIds).toEqual(['replica:home', 'replica:recovery'])
  })

  it('fails recovery closed when trusted replicas disagree', () => {
    const authority = createPeaceLogicalAuthorityState()
    const home = createPeaceReplica(authority, 'replica:home', 'HOME_NODE')
    const cloud = {
      ...createPeaceReplica(authority, 'replica:recovery', 'CLOUD_RECOVERY'),
      admittedStateRoot: 'state:conflict',
    }

    const recovered = recoverPeaceLogicalAuthorityState([home, cloud])
    expect(recovered.status).toBe('DENY')
  })
})
