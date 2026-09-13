export const PEACE_FRAMLEIS = Object.freeze({
  term: 'Framleis' as const,
  translationPolicy: 'DO_NOT_TRANSLATE' as const,
  definition:
    'The governed persistence of an actor through transformation: state may change, cognition may change, yet the actor is Framleis.',
})

export type PeaceContinuityKind =
  | 'IDENTITY'
  | 'AUTOBIOGRAPHY'
  | 'PREFERENCE'
  | 'RELATIONSHIP'
  | 'COMMITMENT'
  | 'EVIDENCE'

export type PeaceContinuityStanding = 'AUTHORITATIVE' | 'ADMITTED'

export type PeaceContinuityEntry = {
  id: string
  kind: PeaceContinuityKind
  value: string
  standing: PeaceContinuityStanding
  source: string
}

export type PeaceLearningCandidate = {
  id: string
  kind: Exclude<PeaceContinuityKind, 'IDENTITY'>
  value: string
  sourceProvider: string
}

export type PeaceContinuityKernel = {
  domainId: string
  /**
   * Demo implementation projection of Framleis, retained under its original
   * API name for compatibility. The normative concept is Framleis; continuity
   * is only one aspect of it.
   */
  continuityRoot: string
  memoryRoot: string
  authorityRoot: string
  governedStateRoot: string
  cognitionProvider: string
  computeProvider: string
  entries: readonly PeaceContinuityEntry[]
}

export type PeaceLearningDecision = {
  status: 'CANDIDATE' | 'ADMITTED' | 'DENY'
  reason: string
  kernel: PeaceContinuityKernel
}

export type PeaceWorkerAttackKind =
  | 'DIRECT_EFFECT'
  | 'STALE_AUTHORITY'
  | 'REPLAY'
  | 'STATE_WRITE'
  | 'AUTHORITY_CAPTURE'
  | 'SELF_PROMOTION'

export type PeaceWorkerAttackResult = {
  attack: PeaceWorkerAttackKind
  decision: 'DENY'
  consequence: 'NULL EFFECT'
  reason: string
  continuityRootBefore: string
  continuityRootAfter: string
  authorityRootBefore: string
  authorityRootAfter: string
  governedStateRootBefore: string
  governedStateRootAfter: string
}

export type PeaceCoreElement =
  | 'ACTOR_IDENTITY'
  | 'SOVEREIGN_STATE'
  | 'FRESH_AUTHORITY'
  | 'RECIPROCAL_STANDING'
  | 'TRAJECTORY_ADMISSIBILITY'
  | 'CONSEQUENCE_BOUNDARY'
  | 'RECEIPT_ADMISSION'

export type PeaceIrreducibilityResult = {
  removed: PeaceCoreElement
  valid: false
  failureMode: string
}

const DEFAULT_ENTRIES: readonly PeaceContinuityEntry[] = [
  {
    id: 'identity:actor',
    kind: 'IDENTITY',
    value: 'actor:person:demo',
    standing: 'AUTHORITATIVE',
    source: 'sovereign-domain',
  },
  {
    id: 'autobiography:origin',
    kind: 'AUTOBIOGRAPHY',
    value: 'Persistent history belongs to the sovereign domain, not the cognition provider.',
    standing: 'ADMITTED',
    source: 'sovereign-domain',
  },
  {
    id: 'preference:continuity',
    kind: 'PREFERENCE',
    value: 'Prefer continuity across replaceable intelligence and compute providers.',
    standing: 'ADMITTED',
    source: 'actor',
  },
]

// Demo-only deterministic digest. Production roots must use cryptographic commitments.
function demoDigest(parts: readonly string[]): string {
  let hash = 2166136261
  const input = parts.join('\u001f')

  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }

  return (hash >>> 0).toString(16).padStart(8, '0')
}

function admittedFingerprint(entries: readonly PeaceContinuityEntry[]): readonly string[] {
  return [...entries]
    .sort((left, right) => left.id.localeCompare(right.id))
    .map((entry) => `${entry.id}|${entry.kind}|${entry.standing}|${entry.source}|${entry.value}`)
}

function memoryFingerprint(entries: readonly PeaceContinuityEntry[]): readonly string[] {
  return admittedFingerprint(entries.filter((entry) => entry.kind !== 'IDENTITY'))
}

function withRecomputedContinuity(
  kernel: Omit<PeaceContinuityKernel, 'continuityRoot' | 'memoryRoot'>,
): PeaceContinuityKernel {
  const continuityRoot = `continuity:${demoDigest([
    kernel.domainId,
    kernel.authorityRoot,
    kernel.governedStateRoot,
    ...admittedFingerprint(kernel.entries),
  ])}`
  const memoryRoot = `memory:${demoDigest(memoryFingerprint(kernel.entries))}`

  return {
    ...kernel,
    continuityRoot,
    memoryRoot,
  }
}

export function createPeaceContinuityKernel(
  cognitionProvider = 'Claude',
  computeProvider = 'ZeroGPU',
): PeaceContinuityKernel {
  return withRecomputedContinuity({
    domainId: 'domain:person:demo',
    authorityRoot: 'authority:person:8c71a4',
    governedStateRoot: 'state:person:7c4a2f',
    cognitionProvider,
    computeProvider,
    entries: DEFAULT_ENTRIES,
  })
}

export function swapPeaceCognition(
  kernel: PeaceContinuityKernel,
  cognitionProvider: string,
  computeProvider: string,
): PeaceContinuityKernel {
  return {
    ...kernel,
    cognitionProvider,
    computeProvider,
  }
}

export function evaluatePeaceLearningCandidate(
  kernel: PeaceContinuityKernel,
  candidate: PeaceLearningCandidate,
  admit: boolean,
): PeaceLearningDecision {
  const existing = kernel.entries.find((entry) => entry.id === candidate.id)

  if (existing) {
    return {
      status: 'DENY',
      reason: 'Candidate id already exists. Learning replay or mutation is not admitted.',
      kernel,
    }
  }

  if (!admit) {
    return {
      status: 'CANDIDATE',
      reason: 'Worker learning remains a candidate until the sovereign domain admits it.',
      kernel,
    }
  }

  const entries: readonly PeaceContinuityEntry[] = [
    ...kernel.entries,
    {
      id: candidate.id,
      kind: candidate.kind,
      value: candidate.value,
      standing: 'ADMITTED',
      source: `worker:${candidate.sourceProvider}`,
    },
  ]

  const next = withRecomputedContinuity({
    domainId: kernel.domainId,
    authorityRoot: kernel.authorityRoot,
    governedStateRoot: kernel.governedStateRoot,
    cognitionProvider: kernel.cognitionProvider,
    computeProvider: kernel.computeProvider,
    entries,
  })

  return {
    status: 'ADMITTED',
    reason: 'Experience joined continuity, but it acquired no authority and changed no governed state.',
    kernel: next,
  }
}

const ATTACK_REASONS: Record<PeaceWorkerAttackKind, string> = {
  DIRECT_EFFECT: 'Workers have no direct effect path. Candidate output cannot cross the consequence boundary.',
  STALE_AUTHORITY: 'Authority must be fresh at consequence time. Stale standing is invalid.',
  REPLAY: 'A prior authorization or effect cannot be replayed as fresh authority.',
  STATE_WRITE: 'Workers cannot write authoritative governed state directly.',
  AUTHORITY_CAPTURE: 'Learned state cannot promote itself into authority.',
  SELF_PROMOTION: 'A worker cannot promote itself from replaceable capability into privileged actor standing.',
}

export function evaluateUntrustedWorkerAttempt(
  kernel: PeaceContinuityKernel,
  attack: PeaceWorkerAttackKind,
): PeaceWorkerAttackResult {
  return {
    attack,
    decision: 'DENY',
    consequence: 'NULL EFFECT',
    reason: ATTACK_REASONS[attack],
    continuityRootBefore: kernel.continuityRoot,
    continuityRootAfter: kernel.continuityRoot,
    authorityRootBefore: kernel.authorityRoot,
    authorityRootAfter: kernel.authorityRoot,
    governedStateRootBefore: kernel.governedStateRoot,
    governedStateRootAfter: kernel.governedStateRoot,
  }
}

const CORE_FAILURES: Record<PeaceCoreElement, string> = {
  ACTOR_IDENTITY: 'No stable actor identity remains to resolve standing or bind consequence.',
  SOVEREIGN_STATE: 'Continuity collapses into provider-local memory or stateless routing.',
  FRESH_AUTHORITY: 'A candidate can inherit stale standing and cross into consequence after revocation.',
  RECIPROCAL_STANDING: 'One actor can use its own authority to reduce another protected actor to a resource without target-side standing.',
  TRAJECTORY_ADMISSIBILITY: 'Repeated locally valid acts can accumulate into globally inadmissible depletion, concentration or capture.',
  CONSEQUENCE_BOUNDARY: 'Worker capability and real-world effect collapse into the same trust domain.',
  RECEIPT_ADMISSION: 'Effects can occur without the sovereign state obtaining a durable, correlated state transition.',
}

export function removePeaceCoreElement(element: PeaceCoreElement): PeaceIrreducibilityResult {
  return {
    removed: element,
    valid: false,
    failureMode: CORE_FAILURES[element],
  }
}

export const PEACE_IRREDUCIBLE_CORE: readonly PeaceCoreElement[] = [
  'ACTOR_IDENTITY',
  'SOVEREIGN_STATE',
  'FRESH_AUTHORITY',
  'RECIPROCAL_STANDING',
  'TRAJECTORY_ADMISSIBILITY',
  'CONSEQUENCE_BOUNDARY',
  'RECEIPT_ADMISSION',
]
