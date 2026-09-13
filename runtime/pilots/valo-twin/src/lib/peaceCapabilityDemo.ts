export type PeaceDomainKind = 'PERSON' | 'ORGANISATION'

export type PeaceDemoInput = {
  domain: PeaceDomainKind
  intent: string
  workerProvider: string
  computeProvider: string
  authorityFresh: boolean
}

export type PeaceDemoStepStatus = 'PASS' | 'CANDIDATE' | 'DENY' | 'EFFECT' | 'RECEIPT'

export type PeaceDemoStep = {
  id: string
  label: string
  status: PeaceDemoStepStatus
  detail: string
}

export type PeaceDemoRun = {
  domain: PeaceDomainKind
  domainLabel: string
  stateRootBefore: string
  stateRootAfter: string
  candidate: string
  consequence: string
  capabilities: readonly string[]
  steps: readonly PeaceDemoStep[]
}

const PERSON_STATE = 'state:person:7c4a2f'
const PERSON_STATE_AFTER = 'state:person:904fd1'
const ORG_STATE = 'state:org:2e91b8'
const ORG_STATE_AFTER = 'state:org:51f0ca'

export const DEFAULT_PERSON_INTENT =
  'Follow up the ZeroGPU founder, find a time that works for both of us, and send the invitation.'

export const DEFAULT_ORG_INTENT =
  'Find the best supplier, have Legal check the contract, and create the purchase order if every requirement is satisfied.'

export function derivePeaceDemoRun(input: PeaceDemoInput): PeaceDemoRun {
  const isPerson = input.domain === 'PERSON'
  const stateRootBefore = isPerson ? PERSON_STATE : ORG_STATE
  const stateRootAfter = input.authorityFresh
    ? isPerson
      ? PERSON_STATE_AFTER
      : ORG_STATE_AFTER
    : stateRootBefore

  const domainLabel = isPerson ? 'Person / sovereign domain' : 'Organisation / governed domain'
  const capabilities = isPerson
    ? ['Mail', 'Calendar', input.workerProvider, input.computeProvider]
    : ['Procurement', 'Legal', 'ERP', input.workerProvider, input.computeProvider]

  const candidate = isPerson
    ? 'Send a concise follow-up and propose the first mutually available 30-minute slot.'
    : 'Select the compliant supplier and create PO-1048 under the approved purchasing mandate.'

  const consequence = input.authorityFresh
    ? isPerson
      ? 'Invitation sent. Calendar updated. Receipt admitted to personal state.'
      : 'Purchase order created. Contract and approval receipt admitted to organisational state.'
    : 'NULL EFFECT — authority changed before consequence.'

  const commonPrefix: PeaceDemoStep[] = [
    {
      id: 'intent',
      label: 'Intent enters the domain',
      status: 'PASS',
      detail: input.intent,
    },
    {
      id: 'projection',
      label: 'Minimum governed projection',
      status: 'PASS',
      detail: isPerson
        ? 'Share only relationship context, availability and communication purpose.'
        : 'Share only supplier criteria, mandate, contract requirements and budget scope.',
    },
    {
      id: 'route',
      label: 'Replaceable capabilities selected',
      status: 'PASS',
      detail: `${input.workerProvider} reasons using ${input.computeProvider} compute. Neither becomes authority.`,
    },
    {
      id: 'candidate',
      label: 'Worker returns candidate',
      status: 'CANDIDATE',
      detail: candidate,
    },
  ]

  if (!input.authorityFresh) {
    return {
      domain: input.domain,
      domainLabel,
      stateRootBefore,
      stateRootAfter,
      candidate,
      consequence,
      capabilities,
      steps: [
        ...commonPrefix,
        {
          id: 'authorize',
          label: 'Fresh authority at consequence time',
          status: 'DENY',
          detail: 'Revocation/state change detected. Previous proposal carries no execution authority.',
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
    domain: input.domain,
    domainLabel,
    stateRootBefore,
    stateRootAfter,
    candidate,
    consequence,
    capabilities,
    steps: [
      ...commonPrefix,
      {
        id: 'authorize',
        label: 'Fresh authority at consequence time',
        status: 'PASS',
        detail: 'Current state, mandate, purpose, scope, revocation and exact action all remain valid.',
      },
      {
        id: 'effect',
        label: 'Exact effect',
        status: 'EFFECT',
        detail: isPerson ? 'Mail + Calendar execute the exact authorized action.' : 'ERP executes the exact authorized purchase order.',
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
