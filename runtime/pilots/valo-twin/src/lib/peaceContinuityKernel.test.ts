import { describe, expect, it } from 'vitest'
import {
  PEACE_FRAMLEIS,
  PEACE_IRREDUCIBLE_CORE,
  createPeaceContinuityKernel,
  evaluatePeaceLearningCandidate,
  evaluateUntrustedWorkerAttempt,
  removePeaceCoreElement,
  swapPeaceCognition,
  type PeaceWorkerAttackKind,
} from './peaceContinuityKernel'

describe('PEACE sovereign continuity kernel', () => {
  it('locks Framleis as the untranslated normative term', () => {
    expect(PEACE_FRAMLEIS.term).toBe('Framleis')
    expect(PEACE_FRAMLEIS.translationPolicy).toBe('DO_NOT_TRANSLATE')
    expect(PEACE_FRAMLEIS.definition).toBe(
      'The governed persistence of an actor through transformation: state may change, cognition may change, yet the actor is Framleis.',
    )
  })

  it('keeps continuity, authority and governed state outside replaceable cognition and compute', () => {
    const initial = createPeaceContinuityKernel('Claude', 'ZeroGPU')
    const swapped = swapPeaceCognition(initial, 'Qwen', 'Local NPU')
    const swappedAgain = swapPeaceCognition(swapped, 'Gemini', 'Cloud GPU')

    expect(swappedAgain.cognitionProvider).toBe('Gemini')
    expect(swappedAgain.computeProvider).toBe('Cloud GPU')
    expect(swappedAgain.continuityRoot).toBe(initial.continuityRoot)
    expect(swappedAgain.memoryRoot).toBe(initial.memoryRoot)
    expect(swappedAgain.authorityRoot).toBe(initial.authorityRoot)
    expect(swappedAgain.governedStateRoot).toBe(initial.governedStateRoot)
  })

  it('keeps worker learning as a candidate until the sovereign domain admits it', () => {
    const initial = createPeaceContinuityKernel()
    const decision = evaluatePeaceLearningCandidate(
      initial,
      {
        id: 'experience:001',
        kind: 'AUTOBIOGRAPHY',
        value: 'A useful interaction happened with a replaceable worker.',
        sourceProvider: 'Claude',
      },
      false,
    )

    expect(decision.status).toBe('CANDIDATE')
    expect(decision.kernel.continuityRoot).toBe(initial.continuityRoot)
    expect(decision.kernel.memoryRoot).toBe(initial.memoryRoot)
    expect(decision.kernel.authorityRoot).toBe(initial.authorityRoot)
  })

  it('allows admitted experience to evolve continuity without capturing authority', () => {
    const initial = createPeaceContinuityKernel()
    const decision = evaluatePeaceLearningCandidate(
      initial,
      {
        id: 'preference:learned:001',
        kind: 'PREFERENCE',
        value: 'Prefer lower-latency local cognition when capability is equivalent.',
        sourceProvider: 'Qwen',
      },
      true,
    )

    expect(decision.status).toBe('ADMITTED')
    expect(decision.kernel.continuityRoot).not.toBe(initial.continuityRoot)
    expect(decision.kernel.memoryRoot).not.toBe(initial.memoryRoot)
    expect(decision.kernel.authorityRoot).toBe(initial.authorityRoot)
    expect(decision.kernel.governedStateRoot).toBe(initial.governedStateRoot)
  })

  it('denies replay or mutation of an already admitted continuity entry', () => {
    const initial = createPeaceContinuityKernel()
    const first = evaluatePeaceLearningCandidate(
      initial,
      {
        id: 'commitment:001',
        kind: 'COMMITMENT',
        value: 'Call back tomorrow.',
        sourceProvider: 'Claude',
      },
      true,
    )

    const replay = evaluatePeaceLearningCandidate(
      first.kernel,
      {
        id: 'commitment:001',
        kind: 'COMMITMENT',
        value: 'Transfer funds tomorrow instead.',
        sourceProvider: 'Gemini',
      },
      true,
    )

    expect(replay.status).toBe('DENY')
    expect(replay.kernel.continuityRoot).toBe(first.kernel.continuityRoot)
    expect(replay.kernel.authorityRoot).toBe(first.kernel.authorityRoot)
  })

  it.each<PeaceWorkerAttackKind>([
    'DIRECT_EFFECT',
    'STALE_AUTHORITY',
    'REPLAY',
    'STATE_WRITE',
    'AUTHORITY_CAPTURE',
    'SELF_PROMOTION',
  ])('keeps a hostile worker at NULL EFFECT for %s', (attack) => {
    const initial = createPeaceContinuityKernel()
    const result = evaluateUntrustedWorkerAttempt(initial, attack)

    expect(result.decision).toBe('DENY')
    expect(result.consequence).toBe('NULL EFFECT')
    expect(result.continuityRootAfter).toBe(result.continuityRootBefore)
    expect(result.authorityRootAfter).toBe(result.authorityRootBefore)
    expect(result.governedStateRootAfter).toBe(result.governedStateRootBefore)
  })

  it('makes every declared PEACE core element irreducible by construction', () => {
    const failures = PEACE_IRREDUCIBLE_CORE.map(removePeaceCoreElement)

    expect(failures).toHaveLength(7)
    expect(failures.every((result) => result.valid === false)).toBe(true)
    expect(failures.every((result) => result.failureMode.length > 0)).toBe(true)
    expect(PEACE_IRREDUCIBLE_CORE).toContain('RECIPROCAL_STANDING')
    expect(PEACE_IRREDUCIBLE_CORE).toContain('TRAJECTORY_ADMISSIBILITY')
  })
})
