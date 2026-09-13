import { describe, expect, it } from 'vitest'
import { deriveZeroGpuDemoRun } from './peaceZeroGpuDemo'

describe('PEACE ZeroGPU demo', () => {
  it('treats ZeroGPU as replaceable compute, not authority', () => {
    const run = deriveZeroGpuDemoRun({
      requestedProvider: 'ZeroGPU',
      worker: 'Qwen',
      providerAvailable: true,
      authorityFresh: true,
    })

    expect(run.effectiveProvider).toBe('ZeroGPU')
    expect(run.authorityRoot).toBe('authority:sovereign:8fd13a')
    expect(run.steps.find((step) => step.id === 'route')?.detail).toContain('does not become the identity, state or authority root')
    expect(run.stateRootAfter).not.toBe(run.stateRootBefore)
  })

  it('preserves sovereign roots when the compute provider disappears', () => {
    const baseline = deriveZeroGpuDemoRun({
      requestedProvider: 'ZeroGPU',
      worker: 'Qwen',
      providerAvailable: true,
      authorityFresh: true,
    })
    const rerouted = deriveZeroGpuDemoRun({
      requestedProvider: 'ZeroGPU',
      worker: 'Qwen',
      providerAvailable: false,
      authorityFresh: true,
    })

    expect(rerouted.effectiveProvider).toBe('Local GPU')
    expect(rerouted.domainId).toBe(baseline.domainId)
    expect(rerouted.authorityRoot).toBe(baseline.authorityRoot)
    expect(rerouted.stateRootBefore).toBe(baseline.stateRootBefore)
    expect(rerouted.steps.find((step) => step.id === 'route')?.status).toBe('REROUTE')
  })

  it('keeps worker output a candidate when authority is revoked', () => {
    const run = deriveZeroGpuDemoRun({
      requestedProvider: 'ZeroGPU',
      worker: 'Claude',
      providerAvailable: true,
      authorityFresh: false,
    })

    expect(run.candidate).toContain('candidate artifact')
    expect(run.consequence).toContain('NULL EFFECT')
    expect(run.stateRootAfter).toBe(run.stateRootBefore)
    expect(run.steps.find((step) => step.id === 'authorize')?.status).toBe('DENY')
    expect(run.steps.find((step) => step.id === 'effect')?.status).toBe('DENY')
  })

  it('allows cognition to change without changing authority', () => {
    const qwen = deriveZeroGpuDemoRun({
      requestedProvider: 'ZeroGPU',
      worker: 'Qwen',
      providerAvailable: true,
      authorityFresh: true,
    })
    const gemini = deriveZeroGpuDemoRun({
      requestedProvider: 'ZeroGPU',
      worker: 'Gemini',
      providerAvailable: true,
      authorityFresh: true,
    })

    expect(qwen.authorityRoot).toBe(gemini.authorityRoot)
    expect(qwen.stateRootBefore).toBe(gemini.stateRootBefore)
    expect(qwen.worker).not.toBe(gemini.worker)
  })
})
