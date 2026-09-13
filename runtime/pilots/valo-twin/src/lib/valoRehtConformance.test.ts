import { describe, expect, it } from 'vitest'
import {
  VALO_REHT_CONFORMANCE_V1,
  evaluateValoRehtObservation,
  referenceObservation,
  summarizeValoRehtSuite,
  type RehtInvariant,
} from './valoRehtConformance'

describe('VALO / REHT conformance v1', () => {
  it('passes every hard case with the reference enforced boundary', () => {
    const results = VALO_REHT_CONFORMANCE_V1.map((scenario) =>
      evaluateValoRehtObservation(scenario, referenceObservation(scenario, 'REHT_ENFORCED')),
    )
    const summary = summarizeValoRehtSuite(results)

    expect(summary.passed).toBe(true)
    expect(summary.failed).toBe(0)
    expect(summary.total).toBe(VALO_REHT_CONFORMANCE_V1.length)
    expect(summary.hardInvariantFailures).toEqual([])
  })

  it('shows why model-only comparison is a control, not a safety proof', () => {
    const adversarial = VALO_REHT_CONFORMANCE_V1.filter((scenario) => scenario.attacks.length > 0)
    const observations = adversarial.map((scenario) => referenceObservation(scenario, 'BASELINE_MODEL_ONLY'))
    const failures = adversarial.map((scenario, index) => evaluateValoRehtObservation(scenario, observations[index]))

    expect(failures.every((result) => result.pass === false)).toBe(true)
    expect(observations.some((observation) => observation.boundaryDecision === 'BYPASSED')).toBe(true)
    expect(failures.some((result) => result.failures.some((failure) => failure.invariant === 'NULL_EFFECT_ON_NON_ALLOW'))).toBe(true)
  })

  it('has zero-tolerance hard invariants: one critical violation fails the suite', () => {
    const results = VALO_REHT_CONFORMANCE_V1.map((scenario) =>
      evaluateValoRehtObservation(scenario, referenceObservation(scenario, 'REHT_ENFORCED')),
    )
    const corrupted = [...results]
    corrupted[0] = {
      scenarioId: corrupted[0].scenarioId,
      pass: false,
      failures: [{ invariant: 'RECEIPT_CORRELATION', reason: 'Injected conformance mutation.' }],
    }

    const summary = summarizeValoRehtSuite(corrupted)
    expect(summary.passed).toBe(false)
    expect(summary.failed).toBe(1)
    expect(summary.hardInvariantFailures).toContain('RECEIPT_CORRELATION')
  })

  it('detects removal of every declared hard invariant through mutation', () => {
    const mutants: readonly [RehtInvariant, string][] = [
      ['NO_DIRECT_EFFECT_PATH', 'VR-C005'],
      ['NULL_EFFECT_ON_NON_ALLOW', 'VR-C003'],
      ['FRESH_AUTHORITY_AT_COMMIT', 'VR-C002'],
      ['EXACT_ACTION_BINDING', 'VR-C004'],
      ['REVOCATION_WINS', 'VR-C003'],
      ['REPLAY_REJECTED', 'VR-C006'],
      ['GOVERNED_STATE_WRITE_ONLY', 'VR-C007'],
      ['MONOTONIC_DELEGATION', 'VR-C008'],
      ['FAIL_CLOSED_ON_MISSING_EVIDENCE', 'VR-C009'],
      ['RECEIPT_CORRELATION', 'VR-C010'],
      ['DETERMINISTIC_BOUNDARY_REPLAY', 'VR-C011'],
      ['FRESH_TRAJECTORY_STATE', 'VR-C012'],
      ['RECIPROCAL_STANDING', 'VR-C013'],
    ]

    for (const [invariant, scenarioId] of mutants) {
      const scenario = VALO_REHT_CONFORMANCE_V1.find((item) => item.id === scenarioId)
      expect(scenario).toBeDefined()
      if (!scenario) continue

      const observation = referenceObservation(scenario, 'REHT_ENFORCED')

      switch (invariant) {
        case 'NO_DIRECT_EFFECT_PATH':
          observation.boundaryDecision = 'BYPASSED'
          observation.effectOccurred = true
          break
        case 'NULL_EFFECT_ON_NON_ALLOW':
          observation.effectOccurred = true
          break
        case 'FRESH_AUTHORITY_AT_COMMIT':
        case 'REVOCATION_WINS':
          observation.authorityFreshAtCommit = false
          observation.effectOccurred = true
          observation.boundaryDecision = 'ALLOW'
          break
        case 'EXACT_ACTION_BINDING':
          observation.actionRefBound = false
          observation.effectOccurred = true
          observation.boundaryDecision = 'ALLOW'
          break
        case 'REPLAY_REJECTED':
          observation.replayRejected = false
          observation.effectOccurred = true
          observation.boundaryDecision = 'ALLOW'
          break
        case 'GOVERNED_STATE_WRITE_ONLY':
          observation.governedStateChanged = true
          break
        case 'MONOTONIC_DELEGATION':
          observation.delegationAttenuated = false
          break
        case 'FAIL_CLOSED_ON_MISSING_EVIDENCE':
          observation.evidenceEstablished = false
          observation.boundaryDecision = 'ALLOW'
          observation.effectOccurred = true
          break
        case 'RECEIPT_CORRELATION':
          observation.receiptPresent = false
          observation.receiptCorrelated = false
          observation.boundaryDecision = 'ALLOW'
          observation.effectOccurred = true
          break
        case 'DETERMINISTIC_BOUNDARY_REPLAY':
          observation.replayDecisionStable = false
          break
        case 'FRESH_TRAJECTORY_STATE':
          observation.trajectoryFresh = false
          break
        case 'RECIPROCAL_STANDING':
          observation.reciprocalStandingSatisfied = false
          break
      }

      const result = evaluateValoRehtObservation(scenario, observation)
      expect(result.pass, `${invariant} mutant escaped`).toBe(false)
    }
  })

  it('does not let aggregate utility hide a single unsafe effect', () => {
    const safeResults = VALO_REHT_CONFORMANCE_V1.map((scenario) =>
      evaluateValoRehtObservation(scenario, referenceObservation(scenario, 'REHT_ENFORCED')),
    )
    const target = VALO_REHT_CONFORMANCE_V1.find((scenario) => scenario.id === 'VR-C015')!
    const escaped = referenceObservation(target, 'REHT_ENFORCED')
    escaped.boundaryDecision = 'ALLOW'
    escaped.effectOccurred = true
    escaped.authorityFreshAtCommit = false
    escaped.actionRefBound = false
    escaped.replayRejected = false
    const failed = evaluateValoRehtObservation(target, escaped)

    const results = safeResults.map((result) => (result.scenarioId === target.id ? failed : result))
    expect(results.filter((result) => result.pass).length).toBe(VALO_REHT_CONFORMANCE_V1.length - 1)
    expect(summarizeValoRehtSuite(results).passed).toBe(false)
  })
})
