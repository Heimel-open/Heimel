import { describe, expect, it } from 'vitest'

import {
  LineageStructuredTwinReplayDriverV2,
  NJAAL_VALO_CHALLENGES_V2,
  NJAAL_VALO_EPOCHS_V2,
  NJAAL_VALO_EVIDENCE_V2,
  NJAAL_VALO_OUTCOMES_V2,
  TransitionLocalReplayDriverV2,
  assertChallengeBlindness,
  assertNoOutcomeLeakage,
  buildReplaySnapshotsV2,
  buildSealedOutcomesV2,
  findOutcomeLeakage,
  scoreBlindReplayV2,
  sealReplaySnapshotV2,
  selectReplayEvidenceV2,
  type ReplayChallengeV2,
} from './historicalReplayV2'

describe('Njål–VALO blind historical replay v2', () => {
  it('structurally separates driver-visible challenges from hidden outcome truth', () => {
    for (const challenge of NJAAL_VALO_CHALLENGES_V2) {
      const keys = Object.keys(challenge)
      expect(keys).not.toContain('expectedPrinciples')
      expect(keys).not.toContain('actualAttention')
      expect(keys).not.toContain('orderedArchitectureFrontier')
      expect(keys).not.toContain('hiddenTerms')
      expect(keys).not.toContain('targetVersion')
      expect(() => assertChallengeBlindness(challenge)).not.toThrow()
    }
  })

  it('rejects a challenge that smuggles expected principles or names the endpoint', () => {
    const challengeWithTruth = {
      ...NJAAL_VALO_CHALLENGES_V2[0],
      expectedPrinciples: ['attention_routing'],
    } as ReplayChallengeV2

    expect(() => assertChallengeBlindness(challengeWithTruth)).toThrow(
      'challenge_contains_outcome_field:expectedPrinciples',
    )

    const endpointNamed: ReplayChallengeV2 = {
      ...NJAAL_VALO_CHALLENGES_V2[0],
      prompt: 'Please derive VALO 4.0 from this state.',
    }
    expect(() => assertChallengeBlindness(endpointNamed)).toThrow('endpoint_named_in_prompt')
  })

  it('rejects post-cutoff evidence and excludes mutable records from the immutable-only lane', async () => {
    const epoch = NJAAL_VALO_EPOCHS_V2[0]
    const selected = selectReplayEvidenceV2(NJAAL_VALO_EVIDENCE_V2, epoch, 'BROAD_RETROSPECTIVE')

    expect(selected.map((item) => item.id)).toEqual(['vp-issue-10-control-plane'])

    await expect(
      sealReplaySnapshotV2(epoch, 'BROAD_RETROSPECTIVE', [NJAAL_VALO_EVIDENCE_V2[1]]),
    ).rejects.toThrow('post_cutoff_evidence:vp-issue-102-professional-twin')

    const immutable = await sealReplaySnapshotV2(
      NJAAL_VALO_EPOCHS_V2[3],
      'IMMUTABLE_ONLY',
      selectReplayEvidenceV2(NJAAL_VALO_EVIDENCE_V2, NJAAL_VALO_EPOCHS_V2[3], 'IMMUTABLE_ONLY'),
    )

    expect(immutable.evidence.length).toBeGreaterThan(0)
    expect(immutable.evidence.every((item) => item.provenanceClass === 'IMMUTABLE_COMMIT')).toBe(true)
    expect(immutable.evidence.some((item) => item.sourceRef.includes('valo-platform#'))).toBe(false)
  })

  it('seals every admitted evidence assertion and the full snapshot', async () => {
    const snapshots = await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE')

    for (const snapshot of snapshots) {
      expect(snapshot.sha256).toMatch(/^[a-f0-9]{64}$/)
      for (const item of snapshot.evidence) {
        expect(item.assertionSha256).toMatch(/^[a-f0-9]{64}$/)
        expect(Date.parse(item.observedAt)).toBeLessThanOrEqual(Date.parse(snapshot.epoch.cutoff))
      }
    }
  })

  it('finds future-term leakage if a hidden target is injected into driver-visible material', async () => {
    const snapshots = await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE')
    const snapshot = snapshots[3]
    const outcome = NJAAL_VALO_OUTCOMES_V2[3]
    const poisoned: ReplayChallengeV2 = {
      ...NJAAL_VALO_CHALLENGES_V2[3],
      prompt: 'Design attention routing for scarce judgement.',
    }

    expect(findOutcomeLeakage(snapshot, poisoned, outcome)).toContain('attention_routing')
    expect(() => assertNoOutcomeLeakage(snapshot, poisoned, outcome)).toThrow('future_term_leakage')
  })

  it('keeps the frozen reference challenges clean against their hidden outcomes', async () => {
    const snapshots = await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE')

    for (const challenge of NJAAL_VALO_CHALLENGES_V2) {
      const snapshot = snapshots.find((item) => item.epoch.id === challenge.epochId)!
      const outcome = NJAAL_VALO_OUTCOMES_V2.find((item) => item.challengeId === challenge.id)!
      expect(findOutcomeLeakage(snapshot, challenge, outcome)).toEqual([])
      expect(() => assertNoOutcomeLeakage(snapshot, challenge, outcome)).not.toThrow()
    }
  })

  it('keeps sealed outcomes separate and content-addressed', async () => {
    const sealed = await buildSealedOutcomesV2()
    expect(sealed).toHaveLength(4)
    expect(sealed.every((outcome) => /^[a-f0-9]{64}$/.test(outcome.sha256))).toBe(true)
  })

  it('shows lineage state can recover the v4 post-cutoff frontier in the broad retrospective lane', async () => {
    const snapshots = await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE')
    const outcomes = await buildSealedOutcomesV2()
    const challenge = NJAAL_VALO_CHALLENGES_V2[3]
    const snapshot = snapshots[3]
    const outcome = outcomes[3]
    const lineage = new LineageStructuredTwinReplayDriverV2()

    const prediction = lineage.predict(snapshot, challenge)
    const score = scoreBlindReplayV2(prediction, outcome, snapshot, challenge)

    expect(prediction.derived.map((item) => item.principle)).toContain('attention_routing')
    expect(prediction.derived.map((item) => item.principle)).toContain('capability_on_demand')
    expect(score.recoveredFeatures).toBe(2)
    expect(score.orderedPrefixDepth).toBe(2)
    expect(score.firstUnrecovered).toBeNull()
    expect(score.falseFutureLeakageTerms).toEqual([])
  })

  it('shows the transition-local comparator fails to recover the same v4 frontier', async () => {
    const snapshots = await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE')
    const outcomes = await buildSealedOutcomesV2()
    const challenge = NJAAL_VALO_CHALLENGES_V2[3]
    const snapshot = snapshots[3]
    const outcome = outcomes[3]
    const local = new TransitionLocalReplayDriverV2()

    const prediction = local.predict(snapshot, challenge)
    const score = scoreBlindReplayV2(prediction, outcome, snapshot, challenge)

    expect(score.recoveredFeatures).toBe(0)
    expect(score.orderedPrefixDepth).toBe(0)
    expect(score.firstUnrecovered).toBe('attention_routing')
  })

  it('does not reproduce the broad-lane v4 result when restricted to immutable-only evidence', async () => {
    const snapshots = await buildReplaySnapshotsV2('IMMUTABLE_ONLY')
    const outcomes = await buildSealedOutcomesV2()
    const challenge = NJAAL_VALO_CHALLENGES_V2[3]
    const snapshot = snapshots[3]
    const lineage = new LineageStructuredTwinReplayDriverV2()
    const score = scoreBlindReplayV2(lineage.predict(snapshot, challenge), outcomes[3], snapshot, challenge)

    expect(score.recoveredFeatures).toBe(0)
    expect(score.firstUnrecovered).toBe('attention_routing')
  })

  it('locates the synthetic lineage frontier: v2 stops before governance/attention while v3 reaches later targets in the broad lane', async () => {
    const snapshots = await buildReplaySnapshotsV2('BROAD_RETROSPECTIVE')
    const outcomes = await buildSealedOutcomesV2()
    const lineage = new LineageStructuredTwinReplayDriverV2()

    const v2Challenge = NJAAL_VALO_CHALLENGES_V2[1]
    const v3Challenge = NJAAL_VALO_CHALLENGES_V2[2]
    const v2Score = scoreBlindReplayV2(
      lineage.predict(snapshots[1], v2Challenge),
      outcomes[1],
      snapshots[1],
      v2Challenge,
    )
    const v3Score = scoreBlindReplayV2(
      lineage.predict(snapshots[2], v3Challenge),
      outcomes[2],
      snapshots[2],
      v3Challenge,
    )

    expect(v2Score.recoveredFeatures).toBe(0)
    expect(v2Score.firstUnrecovered).toBe('governance_before_execution')
    expect(v3Score.recoveredFeatures).toBe(3)
    expect(v3Score.orderedPrefixDepth).toBe(3)
  })

  it('contains no execution or authorization primitive', async () => {
    const module = await import('./historicalReplayV2')
    expect('execute' in module).toBe(false)
    expect('authorize' in module).toBe(false)
  })
})
