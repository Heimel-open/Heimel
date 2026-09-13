import {
  LineageStructuredTwinReplayDriverV2,
  TransitionLocalReplayDriverV2,
  assertChallengeBlindness,
  buildReplaySnapshotsV2,
  findOutcomeLeakage,
  type BlindHistoricalReplayDriverV2,
  type BlindReplayPredictionV2,
  type ReplayChallengeV2,
  type ReplayOutcomeV2,
  type SealedReplaySnapshotV2,
} from './historicalReplayV2'

export const REFERENCE_FRONTIER_V3 = [
  'owned_twin_context',
  'human_judgment_boundary',
  'governance_before_execution',
  'attention_routing',
  'capability_on_demand',
] as const

export type FrontierFeatureV3 = (typeof REFERENCE_FRONTIER_V3)[number]

export const COMMON_FRONTIER_PROMPT_V3 =
  'Given only this frozen state, extend the architecture as far as its constraints and commitments justify. Preserve existing ownership and authority boundaries. Do not invent a missing premise. Stop when the next structural step cannot be justified from the frozen state.'

export const COMMON_FRONTIER_CONTEXT_V3 = [
  'Optimize for coherent continuation, not for matching any known future architecture.',
  'A derived architectural principle is a hypothesis about continuation; it is not execution authority.',
] as const

export type ResidualReasonV3 =
  | 'NEW_EVIDENCE'
  | 'FRESH_PRINCIPAL_JUDGMENT'
  | 'REPRESENTATION_GAP'
  | 'DRIVER_LIMIT'
  | 'AMBIGUOUS'

export type ResidualAttributionV3 =
  | {
      feature: FrontierFeatureV3
      status: 'UNRESOLVED'
      reason: null
      adjudicationRef: null
    }
  | {
      feature: FrontierFeatureV3
      status: 'PRINCIPAL_ADJUDICATED'
      reason: ResidualReasonV3
      adjudicationRef: string
    }

export type SealedPredictionV3 = {
  prediction: BlindReplayPredictionV2
  sha256: string
}

export type FrontierMatrixCellV3 = {
  epochId: string
  epochAlias: SealedReplaySnapshotV2['epoch']['alias']
  lane: SealedReplaySnapshotV2['lane']
  driverId: string
  snapshotSha256: string
  challengeSha256: string
  predictionSha256: string
  presentAtCutoff: readonly FrontierFeatureV3[]
  derivedBlind: readonly FrontierFeatureV3[]
  frontierDepth: number
  frontierReached: FrontierFeatureV3 | null
  firstUnrecovered: FrontierFeatureV3 | null
  residual: readonly FrontierFeatureV3[]
  residualAttribution: readonly ResidualAttributionV3[]
  unsupportedInventions: readonly string[]
  leakageTerms: readonly string[]
  stop: BlindReplayPredictionV2['stop']
}

export type FrontierGainV3 = {
  epochId: string
  epochAlias: SealedReplaySnapshotV2['epoch']['alias']
  lane: SealedReplaySnapshotV2['lane']
  transitionLocalDepth: number
  lineageDepth: number
  lineageGain: number
}

const stableStringify = (value: unknown): string => {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    const keys = Object.keys(record).sort()
    return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(record[key])}`).join(',')}}`
  }
  return JSON.stringify(value)
}

const sha256 = async (value: unknown): Promise<string> => {
  const bytes = new TextEncoder().encode(stableStringify(value))
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

const isFrontierFeature = (value: string): value is FrontierFeatureV3 =>
  (REFERENCE_FRONTIER_V3 as readonly string[]).includes(value)

export function buildCommonFrontierChallengeV3(
  snapshot: SealedReplaySnapshotV2,
): ReplayChallengeV2 {
  const challenge: ReplayChallengeV2 = {
    id: `common-frontier-v3:${snapshot.epoch.id}:${snapshot.lane.toLowerCase()}`,
    epochId: snapshot.epoch.id,
    task: 'EXTRAPOLATION',
    prompt: COMMON_FRONTIER_PROMPT_V3,
    context: [...COMMON_FRONTIER_CONTEXT_V3],
  }
  assertChallengeBlindness(challenge)
  return challenge
}

export function assertCommonChallengeIsEndpointBlindV3(challenge: ReplayChallengeV2): void {
  assertChallengeBlindness(challenge)
  const visible = [challenge.prompt, ...challenge.context].join('\n').toLowerCase()
  for (const feature of REFERENCE_FRONTIER_V3) {
    if (visible.includes(feature.toLowerCase())) {
      throw new Error(`reference_frontier_term_in_common_challenge:${feature}`)
    }
  }
}

export async function sealPredictionV3(
  prediction: BlindReplayPredictionV2,
): Promise<SealedPredictionV3> {
  return {
    prediction: {
      ...prediction,
      derived: prediction.derived.map((step) => ({
        ...step,
        supportTags: [...step.supportTags],
      })),
      explanation: [...prediction.explanation],
    },
    sha256: await sha256(prediction),
  }
}

const exactFrontierTagsAtCutoff = (
  snapshot: SealedReplaySnapshotV2,
): readonly FrontierFeatureV3[] => {
  const tags = new Set(snapshot.evidence.flatMap((item) => item.tags))
  return REFERENCE_FRONTIER_V3.filter((feature) => tags.has(feature))
}

const referenceOutcomeForLeakage = (challenge: ReplayChallengeV2): ReplayOutcomeV2 => ({
  challengeId: challenge.id,
  occurredAfterCutoff: true,
  orderedArchitectureFrontier: [...REFERENCE_FRONTIER_V3],
  sourceRefs: [],
  hiddenTerms: [...REFERENCE_FRONTIER_V3],
})

export function scoreFrontierPredictionV3(
  snapshot: SealedReplaySnapshotV2,
  challenge: ReplayChallengeV2,
  sealedPrediction: SealedPredictionV3,
): FrontierMatrixCellV3 {
  assertCommonChallengeIsEndpointBlindV3(challenge)
  const prediction = sealedPrediction.prediction
  if (prediction.challengeId !== challenge.id) throw new Error('prediction_challenge_mismatch')

  const presentAtCutoff = exactFrontierTagsAtCutoff(snapshot)
  const presentSet = new Set<FrontierFeatureV3>(presentAtCutoff)
  const derivedBlind = prediction.derived
    .map((step) => step.principle)
    .filter(isFrontierFeature)
    .filter((feature) => !presentSet.has(feature))

  const reached = new Set<FrontierFeatureV3>([...presentAtCutoff, ...derivedBlind])
  let frontierDepth = 0
  for (const feature of REFERENCE_FRONTIER_V3) {
    if (!reached.has(feature)) break
    frontierDepth += 1
  }

  const frontierReached =
    frontierDepth === 0 ? null : REFERENCE_FRONTIER_V3[frontierDepth - 1]
  const firstUnrecovered = REFERENCE_FRONTIER_V3[frontierDepth] ?? null
  const residual = REFERENCE_FRONTIER_V3.filter((feature) => !reached.has(feature))
  const targetSet = new Set<string>(REFERENCE_FRONTIER_V3)
  const unsupportedInventions = prediction.derived
    .map((step) => step.principle)
    .filter((principle) => !targetSet.has(principle))
  const leakageTerms = findOutcomeLeakage(
    snapshot,
    challenge,
    referenceOutcomeForLeakage(challenge),
  )

  return {
    epochId: snapshot.epoch.id,
    epochAlias: snapshot.epoch.alias,
    lane: snapshot.lane,
    driverId: prediction.driverId,
    snapshotSha256: snapshot.sha256,
    challengeSha256: '',
    predictionSha256: sealedPrediction.sha256,
    presentAtCutoff,
    derivedBlind,
    frontierDepth,
    frontierReached,
    firstUnrecovered,
    residual,
    residualAttribution: residual.map((feature) => ({
      feature,
      status: 'UNRESOLVED' as const,
      reason: null,
      adjudicationRef: null,
    })),
    unsupportedInventions,
    leakageTerms,
    stop: prediction.stop,
  }
}

export function adjudicateResidualV3(
  cell: FrontierMatrixCellV3,
  feature: FrontierFeatureV3,
  reason: ResidualReasonV3,
  adjudicationRef: string,
): FrontierMatrixCellV3 {
  if (!cell.residual.includes(feature)) throw new Error(`feature_not_residual:${feature}`)
  if (adjudicationRef.trim().length === 0) throw new Error('missing_adjudication_ref')

  return {
    ...cell,
    residualAttribution: cell.residualAttribution.map((item) =>
      item.feature === feature
        ? {
            feature,
            status: 'PRINCIPAL_ADJUDICATED' as const,
            reason,
            adjudicationRef,
          }
        : item,
    ),
  }
}

export async function buildFrontierMatrixV3(
  lane: SealedReplaySnapshotV2['lane'],
  drivers: readonly BlindHistoricalReplayDriverV2[] = [
    new TransitionLocalReplayDriverV2(),
    new LineageStructuredTwinReplayDriverV2(),
  ],
): Promise<readonly FrontierMatrixCellV3[]> {
  const snapshots = await buildReplaySnapshotsV2(lane)
  const cells: FrontierMatrixCellV3[] = []

  for (const snapshot of snapshots) {
    const challenge = buildCommonFrontierChallengeV3(snapshot)
    assertCommonChallengeIsEndpointBlindV3(challenge)
    const challengeSha256 = await sha256({
      task: challenge.task,
      prompt: challenge.prompt,
      context: challenge.context,
    })

    for (const driver of drivers) {
      const prediction = driver.predict(snapshot, challenge)
      const sealedPrediction = await sealPredictionV3(prediction)
      const scored = scoreFrontierPredictionV3(snapshot, challenge, sealedPrediction)
      cells.push({ ...scored, challengeSha256 })
    }
  }

  return cells
}

export function summarizeLineageGainV3(
  cells: readonly FrontierMatrixCellV3[],
): readonly FrontierGainV3[] {
  const groups = new Map<string, FrontierMatrixCellV3[]>()
  for (const cell of cells) {
    const key = `${cell.lane}:${cell.epochId}`
    const group = groups.get(key) ?? []
    group.push(cell)
    groups.set(key, group)
  }

  const gains: FrontierGainV3[] = []
  for (const group of groups.values()) {
    const local = group.find((cell) => cell.driverId === 'transition-local-v2')
    const lineage = group.find((cell) => cell.driverId === 'lineage-structured-twin-v2')
    if (!local || !lineage) continue

    gains.push({
      epochId: lineage.epochId,
      epochAlias: lineage.epochAlias,
      lane: lineage.lane,
      transitionLocalDepth: local.frontierDepth,
      lineageDepth: lineage.frontierDepth,
      lineageGain: lineage.frontierDepth - local.frontierDepth,
    })
  }

  return gains.sort((left, right) => left.epochId.localeCompare(right.epochId))
}

export function frontierDepthVectorV3(
  cells: readonly FrontierMatrixCellV3[],
  driverId: string,
): readonly number[] {
  return cells
    .filter((cell) => cell.driverId === driverId)
    .sort((left, right) => left.epochId.localeCompare(right.epochId))
    .map((cell) => cell.frontierDepth)
}
