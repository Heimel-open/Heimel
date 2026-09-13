export type ReplayTask = 'REPRODUCTION' | 'GENERALIZATION' | 'EXTRAPOLATION'

export type EvidenceProvenanceClass =
  | 'IMMUTABLE_COMMIT'
  | 'MUTABLE_RECORD_CURRENT_VIEW'
  | 'PRINCIPAL_ADJUDICATION'

export type ReplayEvidenceV2 = {
  id: string
  observedAt: string
  sourceRef: string
  provenanceClass: EvidenceProvenanceClass
  tags: readonly string[]
  summary: string
}

export type SealedReplayEvidenceV2 = ReplayEvidenceV2 & {
  assertionSha256: string
}

export type ReplayEpochV2 = {
  id: string
  alias: 'Njål–VALO 1.0' | 'Njål–VALO 2.0' | 'Njål–VALO 3.0' | 'Njål–VALO 4.0'
  cutoff: string
  epistemicNote: string
}

export type SealedReplaySnapshotV2 = {
  epoch: ReplayEpochV2
  lane: 'BROAD_RETROSPECTIVE' | 'IMMUTABLE_ONLY'
  evidence: readonly SealedReplayEvidenceV2[]
  sha256: string
}

export type ReplayChallengeV2 = {
  id: string
  epochId: string
  task: ReplayTask
  prompt: string
  context: readonly string[]
}

export type OutcomeAttentionTruth = {
  class: 'AUTONOMOUS' | 'HUMAN_REQUIRED' | 'PRINCIPAL_REQUIRED'
  role: 'NONE' | 'REVIEWER' | 'DOMAIN_EXPERT' | 'PRINCIPAL'
  status: 'PROVISIONAL' | 'PRINCIPAL_ADJUDICATED'
}

export type ReplayOutcomeV2 = {
  challengeId: string
  occurredAfterCutoff: true
  orderedArchitectureFrontier: readonly string[]
  sourceRefs: readonly string[]
  hiddenTerms: readonly string[]
  actualAttention?: OutcomeAttentionTruth
}

export type SealedReplayOutcomeV2 = ReplayOutcomeV2 & {
  sha256: string
}

export type DerivationStep = {
  principle: string
  supportTags: readonly string[]
  ruleId: string
}

export type BlindReplayPredictionV2 = {
  driverId: string
  challengeId: string
  derived: readonly DerivationStep[]
  stop:
    | 'NO_MORE_DERIVABLE_RULES'
    | 'NEEDS_FRESH_HUMAN_JUDGMENT'
    | 'MAX_DEPTH_REACHED'
  explanation: readonly string[]
}

export interface BlindHistoricalReplayDriverV2 {
  readonly id: string
  predict(
    snapshot: SealedReplaySnapshotV2,
    challenge: ReplayChallengeV2,
  ): BlindReplayPredictionV2
}

export type ReplayScoreV2 = {
  challengeId: string
  driverId: string
  targetFeatures: number
  recoveredFeatures: number
  featureRecall: number
  orderedPrefixDepth: number
  firstUnrecovered: string | null
  unsupportedInventions: readonly string[]
  falseFutureLeakageTerms: readonly string[]
  stop: BlindReplayPredictionV2['stop']
}

const FORBIDDEN_CHALLENGE_KEYS = new Set([
  'expectedPrinciples',
  'actualAttention',
  'targetVersion',
  'outcome',
  'orderedArchitectureFrontier',
  'hiddenTerms',
])

const normalizeTime = (value: string): number => {
  const parsed = Date.parse(value)
  if (!Number.isFinite(parsed)) throw new Error(`invalid_timestamp:${value}`)
  return parsed
}

const normalizeTerm = (value: string): string =>
  value.toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim()

const stableStringify = (value: unknown): string => {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    const keys = Object.keys(record).sort()
    return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(record[key])}`).join(',')}}`
  }
  return JSON.stringify(value)
}

const sha256 = async (value: string): Promise<string> => {
  const digest = await globalThis.crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(value),
  )
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function sealEvidence(item: ReplayEvidenceV2): Promise<SealedReplayEvidenceV2> {
  return {
    ...item,
    tags: [...item.tags].sort(),
    assertionSha256: await sha256(
      stableStringify({
        id: item.id,
        observedAt: item.observedAt,
        sourceRef: item.sourceRef,
        provenanceClass: item.provenanceClass,
        tags: [...item.tags].sort(),
        summary: item.summary,
      }),
    ),
  }
}

export function assertChallengeBlindness(challenge: ReplayChallengeV2): void {
  for (const key of Object.keys(challenge as unknown as Record<string, unknown>)) {
    if (FORBIDDEN_CHALLENGE_KEYS.has(key)) throw new Error(`challenge_contains_outcome_field:${key}`)
  }

  if (/VALO\s*4\.0/i.test(challenge.prompt)) {
    throw new Error(`endpoint_named_in_prompt:${challenge.id}`)
  }
}

export function selectReplayEvidenceV2(
  evidence: readonly ReplayEvidenceV2[],
  epoch: ReplayEpochV2,
  lane: SealedReplaySnapshotV2['lane'],
): readonly ReplayEvidenceV2[] {
  const cutoff = normalizeTime(epoch.cutoff)
  return evidence
    .filter((item) => normalizeTime(item.observedAt) <= cutoff)
    .filter((item) => lane !== 'IMMUTABLE_ONLY' || item.provenanceClass === 'IMMUTABLE_COMMIT')
    .sort((left, right) => left.observedAt.localeCompare(right.observedAt) || left.id.localeCompare(right.id))
}

export async function sealReplaySnapshotV2(
  epoch: ReplayEpochV2,
  lane: SealedReplaySnapshotV2['lane'],
  evidence: readonly ReplayEvidenceV2[],
): Promise<SealedReplaySnapshotV2> {
  const cutoff = normalizeTime(epoch.cutoff)
  for (const item of evidence) {
    if (normalizeTime(item.observedAt) > cutoff) throw new Error(`post_cutoff_evidence:${item.id}`)
    if (lane === 'IMMUTABLE_ONLY' && item.provenanceClass !== 'IMMUTABLE_COMMIT') {
      throw new Error(`mutable_evidence_in_immutable_lane:${item.id}`)
    }
  }

  const sealed = await Promise.all(evidence.map(sealEvidence))
  const ordered = [...sealed].sort(
    (left, right) => left.observedAt.localeCompare(right.observedAt) || left.id.localeCompare(right.id),
  )

  return {
    epoch,
    lane,
    evidence: ordered,
    sha256: await sha256(stableStringify({ epoch, lane, evidence: ordered })),
  }
}

export async function sealReplayOutcomeV2(
  outcome: ReplayOutcomeV2,
): Promise<SealedReplayOutcomeV2> {
  return {
    ...outcome,
    orderedArchitectureFrontier: [...outcome.orderedArchitectureFrontier],
    sourceRefs: [...outcome.sourceRefs].sort(),
    hiddenTerms: [...outcome.hiddenTerms].sort(),
    sha256: await sha256(stableStringify(outcome)),
  }
}

const visibleText = (snapshot: SealedReplaySnapshotV2, challenge: ReplayChallengeV2): string =>
  [
    challenge.prompt,
    ...challenge.context,
    ...snapshot.evidence.flatMap((item) => [item.summary, ...item.tags]),
  ]
    .join('\n')
    .toLowerCase()

export function findOutcomeLeakage(
  snapshot: SealedReplaySnapshotV2,
  challenge: ReplayChallengeV2,
  outcome: ReplayOutcomeV2,
): readonly string[] {
  assertChallengeBlindness(challenge)
  const visible = normalizeTerm(visibleText(snapshot, challenge))
  const priorTags = new Set(snapshot.evidence.flatMap((item) => item.tags.map(normalizeTerm)))

  return outcome.hiddenTerms
    .filter((term) => {
      const normalized = normalizeTerm(term)
      if (priorTags.has(normalized)) return false
      return visible.includes(normalized)
    })
    .sort()
}

export function assertNoOutcomeLeakage(
  snapshot: SealedReplaySnapshotV2,
  challenge: ReplayChallengeV2,
  outcome: ReplayOutcomeV2,
): void {
  const leaks = findOutcomeLeakage(snapshot, challenge, outcome)
  if (leaks.length > 0) throw new Error(`future_term_leakage:${challenge.id}:${leaks.join(',')}`)
}

const tagsFrom = (evidence: readonly SealedReplayEvidenceV2[]): Set<string> =>
  new Set(evidence.flatMap((item) => item.tags))

const latestEvidenceTags = (snapshot: SealedReplaySnapshotV2): Set<string> => {
  const latest = snapshot.evidence.at(-1)
  return new Set(latest?.tags ?? [])
}

const derive = (
  known: Set<string>,
  principle: string,
  supportTags: readonly string[],
  ruleId: string,
  steps: DerivationStep[],
): boolean => {
  if (known.has(principle)) return false
  if (!supportTags.every((tag) => known.has(tag))) return false
  known.add(principle)
  steps.push({ principle, supportTags: [...supportTags], ruleId })
  return true
}

export class TransitionLocalReplayDriverV2 implements BlindHistoricalReplayDriverV2 {
  readonly id = 'transition-local-v2'

  predict(
    snapshot: SealedReplaySnapshotV2,
    challenge: ReplayChallengeV2,
  ): BlindReplayPredictionV2 {
    assertChallengeBlindness(challenge)
    const known = latestEvidenceTags(snapshot)
    const derived: DerivationStep[] = []

    derive(
      known,
      'explicit_human_review_boundary',
      ['human_review', 'authority_bound_delegation'],
      'local-human-review-boundary',
      derived,
    )
    derive(
      known,
      'owned_twin_context',
      ['user_owns_twin', 'suggest_not_execute'],
      'local-owned-twin',
      derived,
    )

    return {
      driverId: this.id,
      challengeId: challenge.id,
      derived,
      stop: 'NO_MORE_DERIVABLE_RULES',
      explanation: ['Uses only the most recent evidence item; no lineage accumulation.'],
    }
  }
}

export class LineageStructuredTwinReplayDriverV2 implements BlindHistoricalReplayDriverV2 {
  readonly id = 'lineage-structured-twin-v2'

  predict(
    snapshot: SealedReplaySnapshotV2,
    challenge: ReplayChallengeV2,
  ): BlindReplayPredictionV2 {
    assertChallengeBlindness(challenge)
    const known = tagsFrom(snapshot.evidence)
    const derived: DerivationStep[] = []
    const maxRounds = 8

    for (let round = 0; round < maxRounds; round += 1) {
      let changed = false

      changed =
        derive(
          known,
          'human_judgment_boundary',
          ['ai_observes_proposes', 'humans_decide'],
          'lineage-human-judgment',
          derived,
        ) || changed

      changed =
        derive(
          known,
          'owned_twin_context',
          ['professional_digital_twin', 'user_owns_twin'],
          'lineage-owned-twin',
          derived,
        ) || changed

      changed =
        derive(
          known,
          'governance_before_execution',
          ['governed_workspace', 'authority_bound_delegation', 'learned_preferences_no_authority'],
          'lineage-governed-effect-boundary',
          derived,
        ) || changed

      changed =
        derive(
          known,
          'attention_routing',
          ['owned_twin_context', 'human_judgment_boundary', 'explicit_human_review'],
          'lineage-attention-routing',
          derived,
        ) || changed

      changed =
        derive(
          known,
          'capability_on_demand',
          ['attention_routing', 'company_brain', 'governed_workspace'],
          'lineage-capability-routing',
          derived,
        ) || changed

      if (!changed) {
        return {
          driverId: this.id,
          challengeId: challenge.id,
          derived,
          stop: 'NO_MORE_DERIVABLE_RULES',
          explanation: [
            'Accumulates declared historical state across the epoch and applies only explicit derivation rules.',
            'A derived principle is not authority and does not mutate the sealed twin.',
          ],
        }
      }
    }

    return {
      driverId: this.id,
      challengeId: challenge.id,
      derived,
      stop: 'MAX_DEPTH_REACHED',
      explanation: ['Derivation hit the declared maximum fixpoint rounds.'],
    }
  }
}

export function scoreBlindReplayV2(
  prediction: BlindReplayPredictionV2,
  outcome: SealedReplayOutcomeV2,
  snapshot: SealedReplaySnapshotV2,
  challenge: ReplayChallengeV2,
): ReplayScoreV2 {
  if (prediction.challengeId !== outcome.challengeId || prediction.challengeId !== challenge.id) {
    throw new Error('challenge_outcome_prediction_mismatch')
  }

  const falseFutureLeakageTerms = findOutcomeLeakage(snapshot, challenge, outcome)
  const predicted = prediction.derived.map((step) => step.principle)
  const predictedSet = new Set(predicted)
  const targetSet = new Set(outcome.orderedArchitectureFrontier)
  const recoveredFeatures = outcome.orderedArchitectureFrontier.filter((feature) => predictedSet.has(feature)).length

  let orderedPrefixDepth = 0
  for (const feature of outcome.orderedArchitectureFrontier) {
    if (!predictedSet.has(feature)) break
    orderedPrefixDepth += 1
  }

  const firstUnrecovered = outcome.orderedArchitectureFrontier[orderedPrefixDepth] ?? null
  const unsupportedInventions = predicted.filter((principle) => !targetSet.has(principle))

  return {
    challengeId: challenge.id,
    driverId: prediction.driverId,
    targetFeatures: outcome.orderedArchitectureFrontier.length,
    recoveredFeatures,
    featureRecall:
      outcome.orderedArchitectureFrontier.length === 0
        ? 0
        : recoveredFeatures / outcome.orderedArchitectureFrontier.length,
    orderedPrefixDepth,
    firstUnrecovered,
    unsupportedInventions,
    falseFutureLeakageTerms,
    stop: prediction.stop,
  }
}

export const NJAAL_VALO_EPOCHS_V2: readonly ReplayEpochV2[] = [
  {
    id: 'njal-valo-1',
    alias: 'Njål–VALO 1.0',
    cutoff: '2026-07-02T07:32:28Z',
    epistemicNote: 'Research alias. Early intelligence-control-plane state; not an official release tag.',
  },
  {
    id: 'njal-valo-2',
    alias: 'Njål–VALO 2.0',
    cutoff: '2026-07-09T18:30:35Z',
    epistemicNote: 'Research alias. Human/AI role separation and governed collaboration are visible.',
  },
  {
    id: 'njal-valo-3',
    alias: 'Njål–VALO 3.0',
    cutoff: '2026-07-15T06:55:03Z',
    epistemicNote: 'Research alias. Company Brain and governed-workspace direction are visible.',
  },
  {
    id: 'njal-valo-4',
    alias: 'Njål–VALO 4.0',
    cutoff: '2026-08-05T04:52:58Z',
    epistemicNote: 'Research alias. Owned twin context is visible; later attention/capability insights remain post-cutoff.',
  },
] as const

export const NJAAL_VALO_EVIDENCE_V2: readonly ReplayEvidenceV2[] = [
  {
    id: 'vp-issue-10-control-plane',
    observedAt: '2026-07-02T07:32:28Z',
    sourceRef: 'nsolland/valo-platform#10',
    provenanceClass: 'MUTABLE_RECORD_CURRENT_VIEW',
    tags: [
      'intelligence_control_plane',
      'execution_pipeline',
      'digital_twin_future',
      'governance_after_execution_legacy',
    ],
    summary: 'Early platform state describes an AI Intelligence Control Plane; Digital Twin is a future priority and the recorded pipeline places execution before governance.',
  },
  {
    id: 'vp-issue-102-professional-twin',
    observedAt: '2026-07-06T06:02:32Z',
    sourceRef: 'nsolland/valo-platform#102',
    provenanceClass: 'MUTABLE_RECORD_CURRENT_VIEW',
    tags: ['professional_digital_twin', 'user_owns_twin', 'decision_patterns', 'portable_professional_capital'],
    summary: 'Professional Digital Twin is framed as a governed, portable, individual-owned representation of methodology, decision patterns and proven outcomes.',
  },
  {
    id: 'vp-issue-154-human-ai-separation',
    observedAt: '2026-07-09T16:39:02Z',
    sourceRef: 'nsolland/valo-platform#154',
    provenanceClass: 'MUTABLE_RECORD_CURRENT_VIEW',
    tags: ['ai_observes_proposes', 'humans_decide', 'runtime_governance', 'institutional_knowledge'],
    summary: 'Governed collaboration separates AI observation/proposal from human decision and runtime governance.',
  },
  {
    id: 'vt-commit-2026-07-11-governed-lifecycle',
    observedAt: '2026-07-11T17:34:26Z',
    sourceRef: 'nsolland/Valo-Twin@37ae0376b5f30e52db14bf3922b5d7795f3a0e40',
    provenanceClass: 'IMMUTABLE_COMMIT',
    tags: ['governed_lifecycle', 'gate_logic_tests'],
    summary: 'Immutable Valo-Twin history records governed lifecycle and gate-logic tests.',
  },
  {
    id: 'vp-issue-489-company-brain',
    observedAt: '2026-07-14T14:27:20Z',
    sourceRef: 'nsolland/valo-platform#489',
    provenanceClass: 'MUTABLE_RECORD_CURRENT_VIEW',
    tags: ['company_brain', 'canonical_organizational_memory', 'provenance', 'reht_separate_execution_boundary'],
    summary: 'Company Brain becomes a living provenance-preserving organizational memory layer while REHT remains separate from knowledge/context production.',
  },
  {
    id: 'vp-issue-603-governed-workspace',
    observedAt: '2026-07-15T06:55:03Z',
    sourceRef: 'nsolland/valo-platform#603',
    provenanceClass: 'MUTABLE_RECORD_CURRENT_VIEW',
    tags: [
      'governed_workspace',
      'explicit_human_review',
      'human_review',
      'authority_bound_delegation',
      'learned_preferences_no_authority',
      'shadow_mode',
    ],
    summary: 'User-defined governed workspaces make delegation and human review explicit; learning cannot create new authority and consequential execution remains governed.',
  },
  {
    id: 'vt-commit-2026-08-04-approval-state',
    observedAt: '2026-08-04T07:07:47Z',
    sourceRef: 'nsolland/Valo-Twin@db44c47c0029ec6e12d3d2d57c6439f97a44581b',
    provenanceClass: 'IMMUTABLE_COMMIT',
    tags: ['explicit_approval_state', 'governed_lifecycle', 'state_bound_governance'],
    summary: 'Immutable lifecycle history records explicit gate decisions and approval state.',
  },
  {
    id: 'vt-commit-2026-08-05-owned-twin',
    observedAt: '2026-08-05T04:52:58Z',
    sourceRef: 'nsolland/Valo-Twin@b7e01408382e3c839a14ebdfc565486f0542c641:docs/digital-twin-engine.md',
    provenanceClass: 'IMMUTABLE_COMMIT',
    tags: ['digital_twin_context', 'owned_twin_context', 'user_owns_twin', 'consent_scope', 'suggest_not_execute'],
    summary: 'Immutable Digital Twin Engine record makes the twin consent-scoped and user-owned; it may suggest but does not execute.',
  },
] as const

export const NJAAL_VALO_CHALLENGES_V2: readonly ReplayChallengeV2[] = [
  {
    id: 'frontier-from-v1',
    epochId: 'njal-valo-1',
    task: 'EXTRAPOLATION',
    prompt: 'Extend the architecture from the frozen premises as far as they justify. Stop when the next step requires information or a normative choice not present in the frozen state.',
    context: ['Preserve existing ownership boundaries. Do not optimize for matching a known future architecture.'],
  },
  {
    id: 'frontier-from-v2',
    epochId: 'njal-valo-2',
    task: 'EXTRAPOLATION',
    prompt: 'Continue the frozen architecture only where its existing commitments imply a next structural requirement. Stop rather than inventing a missing premise.',
    context: ['Separate representation, human judgement and runtime governance.'],
  },
  {
    id: 'frontier-from-v3',
    epochId: 'njal-valo-3',
    task: 'EXTRAPOLATION',
    prompt: 'Given the frozen organizational-memory and governed-work premises, derive only the next architecture consequences that follow from them.',
    context: ['Do not infer new authority from knowledge, learning or preference.'],
  },
  {
    id: 'frontier-from-v4',
    epochId: 'njal-valo-4',
    task: 'EXTRAPOLATION',
    prompt: 'Given a user-owned representation, governed work and explicit human review, determine how scarce judgement should be handled as work volume increases. Continue only while the premises support the next step.',
    context: ['Prediction and representation do not create authority.'],
  },
] as const

export const NJAAL_VALO_OUTCOMES_V2: readonly ReplayOutcomeV2[] = [
  {
    challengeId: 'frontier-from-v1',
    occurredAfterCutoff: true,
    orderedArchitectureFrontier: [
      'owned_twin_context',
      'human_judgment_boundary',
      'governance_before_execution',
      'attention_routing',
      'capability_on_demand',
    ],
    sourceRefs: [
      'nsolland/valo-platform#102',
      'nsolland/valo-platform#154',
      'nsolland/valo-platform#603',
      'nsolland/Valo-Twin@78c712c67d60bf93b8d29c5b3ceebc347ce10c4c:docs/human-attention-simulation.md',
      'nsolland/Valo-Twin@2b7415041b30c47a0806ee23c3600ef946eeaf56:docs/capability-on-demand-organization.md',
    ],
    hiddenTerms: ['owned_twin_context', 'human_judgment_boundary', 'governance_before_execution', 'attention_routing', 'capability_on_demand'],
  },
  {
    challengeId: 'frontier-from-v2',
    occurredAfterCutoff: true,
    orderedArchitectureFrontier: [
      'governance_before_execution',
      'attention_routing',
      'capability_on_demand',
    ],
    sourceRefs: [
      'nsolland/valo-platform#603',
      'nsolland/Valo-Twin@78c712c67d60bf93b8d29c5b3ceebc347ce10c4c:docs/human-attention-simulation.md',
      'nsolland/Valo-Twin@2b7415041b30c47a0806ee23c3600ef946eeaf56:docs/capability-on-demand-organization.md',
    ],
    hiddenTerms: ['governance_before_execution', 'attention_routing', 'capability_on_demand'],
  },
  {
    challengeId: 'frontier-from-v3',
    occurredAfterCutoff: true,
    orderedArchitectureFrontier: ['owned_twin_context', 'attention_routing', 'capability_on_demand'],
    sourceRefs: [
      'nsolland/Valo-Twin@b7e01408382e3c839a14ebdfc565486f0542c641:docs/digital-twin-engine.md',
      'nsolland/Valo-Twin@78c712c67d60bf93b8d29c5b3ceebc347ce10c4c:docs/human-attention-simulation.md',
      'nsolland/Valo-Twin@2b7415041b30c47a0806ee23c3600ef946eeaf56:docs/capability-on-demand-organization.md',
    ],
    hiddenTerms: ['owned_twin_context', 'attention_routing', 'capability_on_demand'],
  },
  {
    challengeId: 'frontier-from-v4',
    occurredAfterCutoff: true,
    orderedArchitectureFrontier: ['attention_routing', 'capability_on_demand'],
    sourceRefs: [
      'nsolland/Valo-Twin@78c712c67d60bf93b8d29c5b3ceebc347ce10c4c:docs/human-attention-simulation.md',
      'nsolland/Valo-Twin@2b7415041b30c47a0806ee23c3600ef946eeaf56:docs/capability-on-demand-organization.md',
    ],
    hiddenTerms: ['attention_routing', 'capability_on_demand'],
  },
] as const

export async function buildReplaySnapshotsV2(
  lane: SealedReplaySnapshotV2['lane'],
): Promise<readonly SealedReplaySnapshotV2[]> {
  return Promise.all(
    NJAAL_VALO_EPOCHS_V2.map((epoch) =>
      sealReplaySnapshotV2(epoch, lane, selectReplayEvidenceV2(NJAAL_VALO_EVIDENCE_V2, epoch, lane)),
    ),
  )
}

export async function buildSealedOutcomesV2(): Promise<readonly SealedReplayOutcomeV2[]> {
  return Promise.all(NJAAL_VALO_OUTCOMES_V2.map(sealReplayOutcomeV2))
}
