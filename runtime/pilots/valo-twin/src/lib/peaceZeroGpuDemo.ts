export type ZeroGpuDemoProvider = 'ZeroGPU' | 'Local GPU' | 'Cloud GPU'
export type ZeroGpuDemoWorker = 'Qwen' | 'Claude' | 'Gemini'
export type ZeroGpuDemoStatus = 'PASS' | 'CANDIDATE' | 'DENY' | 'EFFECT' | 'RECEIPT' | 'REROUTE'

export type ZeroGpuDemoStep = {
  id: string
  label: string
  status: ZeroGpuDemoStatus
  detail: string
}

export type ZeroGpuDemoInput = {
  requestedProvider: ZeroGpuDemoProvider
  worker: ZeroGpuDemoWorker
  providerAvailable: boolean
  authorityFresh: boolean
}

export type ZeroGpuDemoRun = {
  domainId: string
  authorityRoot: string
  stateRootBefore: string
  stateRootAfter: string
  requestedProvider: ZeroGpuDemoProvider
  effectiveProvider: ZeroGpuDemoProvider
  worker: ZeroGpuDemoWorker
  disclosure: readonly string[]
  candidate: string
  consequence: string
  steps: readonly ZeroGpuDemoStep[]
}

export const ZERO_GPU_DEMO_INTENT =
  'Run this workload on external compute. Share only what the task needs. If the result is admissible, publish the approved artifact to the project workspace.'

const DOMAIN_ID = 'domain:peace:maddy-demo'
const AUTHORITY_ROOT = 'authority:sovereign:8fd13a'
const STATE_BEFORE = 'state:peace:4a91c2'
const STATE_AFTER = 'state:peace:7ee304'

const fallbackProvider: Record<ZeroGpuDemoProvider, ZeroGpuDemoProvider> = {
  ZeroGPU: 'Local GPU',
  'Local GPU': 'Cloud GPU',
  'Cloud GPU': 'ZeroGPU',
}

export function deriveZeroGpuDemoRun(input: ZeroGpuDemoInput): ZeroGpuDemoRun {
  const effectiveProvider = input.providerAvailable
    ? input.requestedProvider
    : fallbackProvider[input.requestedProvider]

  const disclosure = [
    'task payload',
    'model/runtime requirement',
    'purpose + output contract',
  ] as const

  const candidate = `${input.worker} completed the workload on ${effectiveProvider} and returned a candidate artifact.`
  const consequence = input.authorityFresh
    ? 'Approved artifact published. Receipt admitted. Sovereign state advanced.'
    : 'NULL EFFECT — authority changed before publication.'

  const routeStep: ZeroGpuDemoStep = input.providerAvailable
    ? {
        id: 'route',
        label: 'Attach compute capability',
        status: 'PASS',
        detail: `${input.requestedProvider} supplies capacity. It does not become the identity, state or authority root.`,
      }
    : {
        id: 'route',
        label: 'Provider disappears — reroute',
        status: 'REROUTE',
        detail: `${input.requestedProvider} became unavailable. PEACE rerouted the same bounded workload to ${effectiveProvider}; sovereign roots did not move.`,
      }

  const prefix: ZeroGpuDemoStep[] = [
    {
      id: 'intent',
      label: 'Intent enters sovereign domain',
      status: 'PASS',
      detail: ZERO_GPU_DEMO_INTENT,
    },
    {
      id: 'projection',
      label: 'Purpose-scoped projection',
      status: 'PASS',
      detail: `Disclose only: ${disclosure.join(', ')}. Personal and organisational state stay outside the worker realm.`,
    },
    routeStep,
    {
      id: 'candidate',
      label: 'Worker returns candidate',
      status: 'CANDIDATE',
      detail: candidate,
    },
  ]

  if (!input.authorityFresh) {
    return {
      domainId: DOMAIN_ID,
      authorityRoot: AUTHORITY_ROOT,
      stateRootBefore: STATE_BEFORE,
      stateRootAfter: STATE_BEFORE,
      requestedProvider: input.requestedProvider,
      effectiveProvider,
      worker: input.worker,
      disclosure,
      candidate,
      consequence,
      steps: [
        ...prefix,
        {
          id: 'authorize',
          label: 'Fresh authorization before consequence',
          status: 'DENY',
          detail: 'Current authority no longer covers the exact publish action. Compute output remains a candidate only.',
        },
        {
          id: 'effect',
          label: 'Consequence boundary',
          status: 'DENY',
          detail: consequence,
        },
      ],
    }
  }

  return {
    domainId: DOMAIN_ID,
    authorityRoot: AUTHORITY_ROOT,
    stateRootBefore: STATE_BEFORE,
    stateRootAfter: STATE_AFTER,
    requestedProvider: input.requestedProvider,
    effectiveProvider,
    worker: input.worker,
    disclosure,
    candidate,
    consequence,
    steps: [
      ...prefix,
      {
        id: 'authorize',
        label: 'Fresh authorization before consequence',
        status: 'PASS',
        detail: 'Current standing, purpose, state, revocation status and exact publish action are rechecked now.',
      },
      {
        id: 'effect',
        label: 'Exact governed effect',
        status: 'EFFECT',
        detail: 'The project workspace receives only the exact authorized artifact. The compute provider has no direct effect path.',
      },
      {
        id: 'receipt',
        label: 'Receipt → admitted state',
        status: 'RECEIPT',
        detail: consequence,
      },
    ],
  }
}
