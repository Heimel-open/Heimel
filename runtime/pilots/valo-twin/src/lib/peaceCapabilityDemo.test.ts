import { describe, expect, it } from 'vitest'
import { DEFAULT_PERSON_INTENT, derivePeaceDemoRun } from './peaceCapabilityDemo'

describe('PEACE capability inversion demo', () => {
  it('keeps sovereign state fixed when worker and compute capabilities are swapped', () => {
    const first = derivePeaceDemoRun({
      domain: 'PERSON',
      intent: DEFAULT_PERSON_INTENT,
      workerProvider: 'Claude',
      computeProvider: 'ZeroGPU',
      authorityFresh: true,
    })
    const second = derivePeaceDemoRun({
      domain: 'PERSON',
      intent: DEFAULT_PERSON_INTENT,
      workerProvider: 'Qwen',
      computeProvider: 'Local NPU',
      authorityFresh: true,
    })

    expect(first.stateRootBefore).toBe(second.stateRootBefore)
    expect(first.capabilities).not.toEqual(second.capabilities)
  })

  it('treats the worker output as a candidate before consequence authorization', () => {
    const run = derivePeaceDemoRun({
      domain: 'PERSON',
      intent: DEFAULT_PERSON_INTENT,
      workerProvider: 'Gemini',
      computeProvider: 'Cloud GPU',
      authorityFresh: true,
    })

    const candidateIndex = run.steps.findIndex((step) => step.id === 'candidate')
    const authorizationIndex = run.steps.findIndex((step) => step.id === 'authorize')
    const effectIndex = run.steps.findIndex((step) => step.id === 'effect')

    expect(run.steps[candidateIndex].status).toBe('CANDIDATE')
    expect(candidateIndex).toBeLessThan(authorizationIndex)
    expect(authorizationIndex).toBeLessThan(effectIndex)
  })

  it('fails closed when authority is revoked before effect', () => {
    const run = derivePeaceDemoRun({
      domain: 'PERSON',
      intent: DEFAULT_PERSON_INTENT,
      workerProvider: 'Claude',
      computeProvider: 'ZeroGPU',
      authorityFresh: false,
    })

    expect(run.steps.find((step) => step.id === 'authorize')?.status).toBe('DENY')
    expect(run.steps.find((step) => step.id === 'effect')?.status).toBe('DENY')
    expect(run.consequence).toContain('NULL EFFECT')
    expect(run.stateRootAfter).toBe(run.stateRootBefore)
  })

  it('uses the same semantic consequence path for person and organisation', () => {
    const person = derivePeaceDemoRun({
      domain: 'PERSON',
      intent: 'personal intent',
      workerProvider: 'Claude',
      computeProvider: 'ZeroGPU',
      authorityFresh: true,
    })
    const organisation = derivePeaceDemoRun({
      domain: 'ORGANISATION',
      intent: 'organisation intent',
      workerProvider: 'Claude',
      computeProvider: 'ZeroGPU',
      authorityFresh: true,
    })

    expect(person.steps.map((step) => step.id)).toEqual(organisation.steps.map((step) => step.id))
    expect(person.domainLabel).not.toBe(organisation.domainLabel)
  })
})
