export const ENTERPRISE_GOVERNANCE_STAGES = [
  {
    id: 'purpose',
    label: 'Purpose',
    detail: 'Define the legitimate outcome the action must serve.',
  },
  {
    id: 'authority',
    label: 'Authority',
    detail: 'Resolve mandate, delegation, limits and accountable human authority.',
  },
  {
    id: 'evidence',
    label: 'Reality & evidence',
    detail: 'Bind the proposed action to current, observable and relevant facts.',
  },
  {
    id: 'evaluation',
    label: 'VAIG',
    detail: 'Evaluate context, policy, risk, uncertainty and evidence quality.',
  },
  {
    id: 'clearance',
    label: 'REHT',
    detail: 'Determine whether this exact action is admissible now.',
  },
  {
    id: 'commit',
    label: 'RACS',
    detail: 'Control the bounded transition from proposal to execution.',
  },
  {
    id: 'outcome',
    label: 'Outcome',
    detail: 'Observe what actually became real and whether purpose was preserved.',
  },
  {
    id: 'receipt',
    label: 'Receipt',
    detail: 'Prove authority, evidence, decision, execution and result.',
  },
] as const

export const RUNTIME_SIGNATURE = [
  {
    id: 'validator',
    label: 'Validator',
    detail: 'Technical readiness',
  },
  {
    id: 'vaig',
    label: 'VAIG',
    detail: 'Evidence and risk evaluation',
  },
  {
    id: 'reht',
    label: 'REHT',
    detail: 'Admissibility clearance',
  },
  {
    id: 'core',
    label: 'Core',
    detail: 'Runtime state enforcement',
  },
  {
    id: 'racs',
    label: 'RACS',
    detail: 'Controlled commit',
  },
] as const

export const INDUSTRY_ENVELOPES = [
  {
    id: 'healthcare',
    domain: 'Healthcare',
    proposedAction: 'Rely on a clinical alert for escalation',
    authority: 'Clinical role, hospital policy and current patient context',
    outcome: 'Human-reviewed clinical action',
    status: 'LIVE DEMO',
  },
  {
    id: 'finance',
    domain: 'Finance',
    proposedAction: 'Release a payment, investment or exposure change',
    authority: 'Mandate, limits, approvals and current financial state',
    outcome: 'Controlled financial commitment',
    status: 'REUSABLE ENVELOPE',
  },
  {
    id: 'manufacturing',
    domain: 'Manufacturing',
    proposedAction: 'Change a production parameter or physical workflow',
    authority: 'Engineering authority, safety state and operating policy',
    outcome: 'Controlled production change',
    status: 'REUSABLE ENVELOPE',
  },
  {
    id: 'public-sector',
    domain: 'Public sector',
    proposedAction: 'Issue or act on a consequential administrative decision',
    authority: 'Statutory delegation, procedure, evidence and human oversight',
    outcome: 'Traceable exercise of public authority',
    status: 'REUSABLE ENVELOPE',
  },
] as const

export const ENTERPRISE_POSITIONING = {
  category: 'Execution Governance Platform',
  headline: 'Technical readiness never authorizes business action.',
  explanation:
    'VALO governs whether a consequential action may become real. The governance spine stays constant while the business scenario, evidence and authority model change by domain.',
  signature:
    'Capability proposes. Authority permits. Evidence grounds. REHT clears. RACS commits. Receipts prove.',
} as const

export type EnterpriseGovernanceStageId = (typeof ENTERPRISE_GOVERNANCE_STAGES)[number]['id']
