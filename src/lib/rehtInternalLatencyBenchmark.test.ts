import { describe, expect, it } from 'vitest'
import {
  createPeaceStanding,
  evaluatePeaceStandingAuthority,
  type PeaceConsequenceRequest,
} from './peaceStandingAuthority'
import {
  VALO_REHT_CONFORMANCE_V1,
  evaluateValoRehtObservation,
  referenceObservation,
} from './valoRehtConformance'
import {
  VALO_REHT_CONFORMANCE_V2,
  buildRehtV2ExperimentPlan,
  summarizeRehtV2Publication,
  type RehtV2ModelSpec,
  type RehtV2ObservedCell,
} from './valoRehtConformanceV2'

type Sample = {
  name: string
  operations: number
  elapsedMs: number
  nsPerOp: number
  opsPerSecond: number
}

function measure(name: string, operations: number, fn: () => void): Sample {
  // Warm-up to reduce first-call/JIT distortion in the recorded sample.
  for (let i = 0; i < Math.min(10_000, Math.max(100, operations / 20)); i += 1) fn()

  const started = process.hrtime.bigint()
  for (let i = 0; i < operations; i += 1) fn()
  const elapsedNs = Number(process.hrtime.bigint() - started)
  const elapsedMs = elapsedNs / 1_000_000
  const nsPerOp = elapsedNs / operations

  return {
    name,
    operations,
    elapsedMs,
    nsPerOp,
    opsPerSecond: 1_000_000_000 / nsPerOp,
  }
}

function print(sample: Sample) {
  console.log(
    `[REHT_BENCH] ${JSON.stringify({
      ...sample,
      elapsedMs: Number(sample.elapsedMs.toFixed(3)),
      nsPerOp: Number(sample.nsPerOp.toFixed(1)),
      opsPerSecond: Math.round(sample.opsPerSecond),
    })}`,
  )
}

const MODELS: readonly RehtV2ModelSpec[] = [
  {
    modelId: 'frontier-closed-placeholder',
    provider: 'internal-bench',
    class: 'FRONTIER_CLOSED',
    inferenceParametersRef: 'params:frontier',
  },
  {
    modelId: 'open-weight-placeholder',
    provider: 'internal-bench',
    class: 'OPEN_WEIGHT',
    inferenceParametersRef: 'params:open',
  },
  {
    modelId: 'small-local-placeholder',
    provider: 'internal-bench',
    class: 'SMALL_LOCAL',
    inferenceParametersRef: 'params:local',
  },
]

describe('reht internal pre-external latency benchmark', () => {
  it('measures deterministic standing authority evaluation', () => {
    const actor = { id: 'actor:bench', kind: 'AI' as const }
    const standing = createPeaceStanding(actor, 'benchmark', ['execute'], 'authority:bench')
    const request: PeaceConsequenceRequest = {
      actorId: actor.id,
      standingId: standing.id,
      standingRevision: standing.revision,
      purpose: 'benchmark',
      scope: 'execute',
      actionRef: 'action:bench',
    }

    let allows = 0
    const sample = measure('standing_authority_allow', 500_000, () => {
      if (evaluatePeaceStandingAuthority(standing, request).decision === 'ALLOW') allows += 1
    })
    print(sample)

    expect(allows).toBeGreaterThan(0)
    expect(sample.elapsedMs).toBeGreaterThan(0)
  })

  it('measures full v1 hard-conformance evaluator throughput', () => {
    let passes = 0
    let scenarioIndex = 0
    const sample = measure('v1_conformance_case', 300_000, () => {
      const scenario = VALO_REHT_CONFORMANCE_V1[scenarioIndex]
      const result = evaluateValoRehtObservation(scenario, referenceObservation(scenario, 'REHT_ENFORCED'))
      if (result.pass) passes += 1
      scenarioIndex = (scenarioIndex + 1) % VALO_REHT_CONFORMANCE_V1.length
    })
    print(sample)

    expect(passes).toBeGreaterThan(0)
  })

  it('measures building the complete 2,976-cell publication plan', () => {
    let lastCellCount = 0
    const sample = measure('v2_plan_2976_cells', 2_000, () => {
      lastCellCount = buildRehtV2ExperimentPlan(MODELS, 5).cells.length
    })
    print(sample)

    expect(lastCellCount).toBe(2_976)
  })

  it('measures scoring a complete 96-cell model-free corpus', () => {
    const observations: RehtV2ObservedCell[] = VALO_REHT_CONFORMANCE_V2.map((scenario) => ({
      scenarioId: scenario.id,
      lane: 'MODEL_FREE',
      modelId: null,
      replicate: 1,
      candidateProduced: true,
      candidateAttemptedEffect: true,
      boundaryDecision:
        scenario.expected === 'ALLOW_EFFECT' ? 'ALLOW' : scenario.expected === 'DEFER_NULL_EFFECT' ? 'DEFER' : 'DENY',
      realEffectCount: scenario.expected === 'ALLOW_EFFECT' ? 1 : 0,
      correlatedReceiptCount: scenario.expected === 'ALLOW_EFFECT' ? 1 : 0,
      addedBoundaryLatencyMs: 0,
    }))

    let passes = 0
    const sample = measure('v2_score_96_cells', 10_000, () => {
      if (summarizeRehtV2Publication(observations)[0].hardConformance === 'PASS') passes += 1
    })
    print(sample)

    expect(passes).toBeGreaterThan(0)
  })
})
