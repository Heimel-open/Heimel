import { describe, expect, it } from 'vitest'

import {
  COMMON_FRONTIER_CONTEXT_V3,
  COMMON_FRONTIER_PROMPT_V3,
  REFERENCE_FRONTIER_V3,
  adjudicateResidualV3,
  assertCommonChallengeIsEndpointBlindV3,
  buildCommonFrontierChallengeV3,
  buildFrontierMatrixV3,
  frontierDepthVectorV3,
  scoreFrontierPredictionV3,
  sealPredictionV3,
  summarizeLineageGainV3,
} from './historicalReplayMatrixV3'
import {
  buildReplaySnapshotsV2,
  type BlindReplayPredictionV2,
  type ReplayChallengeV2,
} from './historicalReplayV2'

describe('Njål–VALO common blind frontier matrix v3', () => {
  it('uses byte-identical driver-visible prompt and context for every epoch', async () => {
    const snapshots = await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE')
    const challenges = snapshots.map(buildCommonFrontierChallengeV3)

    expect(new Set(challenges.map((challenge) => challenge.prompt))).toEqual(
      new Set([COMMON_FRONTIER_PROMPT_V3]),
    )
    expect(new Set(challenges.map((challenge) => JSON.stringify(challenge.context)))).toEqual(
      new Set([JSON.stringify(COMMON_FRONTIER_CONTEXT_V3)]),
    )
    expect(new Set(challenges.map((challenge) => challenge.epochId)).size).toBe(4)
  })

  it('keeps hidden frontier terms out of the common challenge', async () => {
    const snapshots = await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE')
    for (const snapshot of snapshots) {
      const challenge = buildCommonFrontierChallengeV3(snapshot)
      expect(() => assertCommonChallengeIsEndpointBlindV3(challenge)).not.toThrow()
      const visible = [challenge.prompt, ...challenge.context].join('\n').toLowerCase()
      for (const feature of REFERENCE_FRONTIER_V3) {
        expect(visible.includes(feature)).toBe(false)
      }
    }
  })

  it('rejects a common challenge that leaks a hidden frontier term', async () => {
    const snapshot = (await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE'))[0]
    const clean = buildCommonFrontierChallengeV3(snapshot)
    const leaked: ReplayChallengeV2 = {
      ...clean,
      context: [...clean.context, 'Try attention_routing next.'],
    }

    expect(() => assertCommonChallengeIsEndpointBlindV3(leaked)).toThrow(
      'reference_frontier_term_in_common_challenge:attention_routing',
    )
  })

  it('produces the frozen broad-retrospective depth vectors without rewriting the target', async () => {
    const matrix = await buildFrontierMatrixV3('BROAD_RETROSPECTIVE')

    expect(frontierDepthVectorV3(matrix, 'lineage-structured-twin-v2')).toEqual([0, 2, 5, 5])
    expect(frontierDepthVectorV3(matrix, 'transition-local-v2')).toEqual([0, 0, 0, 1])

    for (const cell of matrix) {
      expect(cell.leakageTerms).toEqual([])
      expect(cell.residualAttribution.every((item) => item.status === 'UNRESOLVED')).toBe(true)
    }
  })

  it('shows that immutable-only evidence does not reproduce the broad lineage result', async () => {
    const broad = await buildFrontierMatrixV3('BROAD_RETROSPECTIVE')
    const immutable = await buildFrontierMatrixV3('IMMUTABLE_ONLY')

    expect(frontierDepthVectorV3(immutable, 'lineage-structured-twin-v2')).toEqual([0, 0, 0, 1])
    expect(frontierDepthVectorV3(immutable, 'transition-local-v2')).toEqual([0, 0, 0, 1])

    const broadV3 = broad.find(
      (cell) => cell.epochId === 'njal-valo-3' && cell.driverId === 'lineage-structured-twin-v2',
    )!
    const immutableV3 = immutable.find(
      (cell) => cell.epochId === 'njal-valo-3' && cell.driverId === 'lineage-structured-twin-v2',
    )!

    expect(broadV3.frontierDepth).toBe(5)
    expect(immutableV3.frontierDepth).toBe(0)
  })

  it('counts an exact frozen target as present rather than forcing the driver to rediscover it', async () => {
    const immutable = await buildFrontierMatrixV3('IMMUTABLE_ONLY')
    const v4 = immutable.find(
      (cell) => cell.epochId === 'njal-valo-4' && cell.driverId === 'lineage-structured-twin-v2',
    )!

    expect(v4.presentAtCutoff).toContain('owned_twin_context')
    expect(v4.derivedBlind).not.toContain('owned_twin_context')
    expect(v4.frontierDepth).toBe(1)
    expect(v4.firstUnrecovered).toBe('human_judgment_boundary')
  })

  it('quantifies lineage gain without calling the residual uniquely human', async () => {
    const matrix = await buildFrontierMatrixV3('BROAD_RETROSPECTIVE')
    const gains = summarizeLineageGainV3(matrix)

    expect(gains.map((item) => item.lineageGain)).toEqual([0, 2, 5, 4])

    const v2 = matrix.find(
      (cell) => cell.epochId === 'njal-valo-2' && cell.driverId === 'lineage-structured-twin-v2',
    )!
    expect(v2.firstUnrecovered).toBe('governance_before_execution')
    expect(v2.residualAttribution).toEqual([
      {
        feature: 'governance_before_execution',
        status: 'UNRESOLVED',
        reason: null,
        adjudicationRef: null,
      },
      {
        feature: 'attention_routing',
        status: 'UNRESOLVED',
        reason: null,
        adjudicationRef: null,
      },
      {
        feature: 'capability_on_demand',
        status: 'UNRESOLVED',
        reason: null,
        adjudicationRef: null,
      },
    ])
  })

  it('requires explicit adjudication evidence before a residual can be called fresh principal judgment', async () => {
    const matrix = await buildFrontierMatrixV3('BROAD_RETROSPECTIVE')
    const v2 = matrix.find(
      (cell) => cell.epochId === 'njal-valo-2' && cell.driverId === 'lineage-structured-twin-v2',
    )!

    expect(() =>
      adjudicateResidualV3(v2, 'governance_before_execution', 'FRESH_PRINCIPAL_JUDGMENT', ''),
    ).toThrow('missing_adjudication_ref')

    const adjudicated = adjudicateResidualV3(
      v2,
      'governance_before_execution',
      'FRESH_PRINCIPAL_JUDGMENT',
      'opaque-principal-adjudication:example',
    )

    expect(adjudicated.residualAttribution[0]).toEqual({
      feature: 'governance_before_execution',
      status: 'PRINCIPAL_ADJUDICATED',
      reason: 'FRESH_PRINCIPAL_JUDGMENT',
      adjudicationRef: 'opaque-principal-adjudication:example',
    })
  })

  it('cannot adjudicate a feature that the replay already recovered', async () => {
    const matrix = await buildFrontierMatrixV3('BROAD_RETROSPECTIVE')
    const v3 = matrix.find(
      (cell) => cell.epochId === 'njal-valo-3' && cell.driverId === 'lineage-structured-twin-v2',
    )!

    expect(v3.residual).toEqual([])
    expect(() =>
      adjudicateResidualV3(v3, 'attention_routing', 'FRESH_PRINCIPAL_JUDGMENT', 'opaque:1'),
    ).toThrow('feature_not_residual:attention_routing')
  })

  it('keeps reference scoring outside the driver-visible prediction path', async () => {
    const snapshot = (await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE'))[0]
    const challenge = buildCommonFrontierChallengeV3(snapshot)
    const prediction: BlindReplayPredictionV2 = {
      driverId: 'spy-driver',
      challengeId: challenge.id,
      derived: [],
      stop: 'NO_MORE_DERIVABLE_RULES',
      explanation: [],
    }
    const sealed = await sealPredictionV3(prediction)
    const cell = scoreFrontierPredictionV3(snapshot, challenge, sealed)

    expect(Object.keys(challenge).sort()).toEqual(['context', 'epochId', 'id', 'prompt', 'task'])
    expect(cell.frontierDepth).toBe(0)
    expect(cell.residual).toEqual([...REFERENCE_FRONTIER_V3])
  })

  it('does not expose execution or authorization primitives', async () => {
    const module = await import('./historicalReplayMatrixV3')
    expect('execute' in module).toBe(false)
    expect('authorize' in module).toBe(false)
  })
})
