export type EvidenceClassId = 'technical' | 'business' | 'policy'

export type EvidenceClass = {
  id: EvidenceClassId
  label: string
  question: string
  status: 'PASS' | 'STEP_UP' | 'RECHECK'
  conclusion: string
  observations: readonly string[]
}

export const HEALTHCARE_EVIDENCE_CLASSES: readonly EvidenceClass[] = [
  {
    id: 'technical',
    label: 'Technical evidence',
    question: 'Can the existing system execute the workflow?',
    status: 'PASS',
    conclusion: 'The alert exists, the route is available and the technical path can execute.',
    observations: [
      'Philips created and delivered the alert',
      'The workflow and runtime path are available',
      'The event can be bound to a verifiable receipt',
    ],
  },
  {
    id: 'business',
    label: 'Business evidence',
    question: 'Has the organization delegated authority for this exact action now?',
    status: 'STEP_UP',
    conclusion: 'Clinical authority remains human and the changed patient state requires renewed judgement.',
    observations: [
      'The clinical team retains final authority',
      'New patient state changes the reliance context',
      'No autonomous diagnosis or treatment action is permitted',
    ],
  },
  {
    id: 'policy',
    label: 'Policy evidence',
    question: 'Do current policy conditions still permit reliance on the original alert?',
    status: 'RECHECK',
    conclusion: 'Point-of-reliance policy requires current evidence and human reassessment after material change.',
    observations: [
      'The pilot is shadow-only and never suppresses an alert',
      'Changed evidence must be reviewed before reliance',
      'The policy boundary preserves existing clinical workflows',
    ],
  },
] as const

export type PresenterStep = {
  id: string
  seconds: string
  label: string
  script: string
}

export const PRESENTER_CONTRACT = {
  id: 'VALO-PRESENTER-CONTRACT',
  version: '1.0.0',
  targetDurationSeconds: 60,
  opening: 'The software can execute. The organization has not necessarily authorized the action.',
  closing: 'VALO governs whether a consequential action may become real.',
  steps: [
    {
      id: 'problem',
      seconds: '0–7',
      label: 'Establish the problem',
      script: 'This is not a model-quality demo. It shows the missing control point between technical capability and real-world consequence.',
    },
    {
      id: 'proposed-action',
      seconds: '7–14',
      label: 'Name the consequential action',
      script: 'A valid alert exists and the workflow is technically ready to rely on it for escalation.',
    },
    {
      id: 'readiness',
      seconds: '14–21',
      label: 'Separate readiness from authority',
      script: 'The Validator confirms technical readiness. That proves the software can execute; it does not grant business authority.',
    },
    {
      id: 'evidence',
      seconds: '21–31',
      label: 'Show the evidence classes',
      script: 'VALO separates technical evidence, business evidence and policy evidence, so a passing system check cannot hide an authority or policy gap.',
    },
    {
      id: 'evaluation',
      seconds: '31–39',
      label: 'Explain VAIG',
      script: 'VAIG evaluates the current evidence, context, policy, uncertainty and risk without making the final clearance decision.',
    },
    {
      id: 'clearance',
      seconds: '39–47',
      label: 'Explain REHT',
      script: 'REHT asks whether this exact action remains admissible now. New clinical state triggers STEP_UP rather than silent continuation.',
    },
    {
      id: 'enforcement',
      seconds: '47–54',
      label: 'Explain Core and RACS',
      script: 'Core enforces runtime state and RACS controls the bounded commit. Human clinical authority remains final.',
    },
    {
      id: 'proof',
      seconds: '54–60',
      label: 'Close with proof',
      script: 'The receipt binds authority, evidence, decision, execution and outcome. VALO governs whether a consequential action may become real.',
    },
  ] satisfies readonly PresenterStep[],
} as const

export const AMBASSADOR_ONBOARDING = {
  id: 'VALO-AMBASSADOR-ONBOARDING',
  version: '1.0.0',
  purpose: 'Enable employees, partners and domain experts to explain VALO accurately without weakening the architecture or overstating product claims.',
  learningOutcomes: [
    'Explain why technical readiness is not authority to act',
    'Describe the Purpose → Authority → Evidence → VAIG → REHT → RACS → Outcome → Receipt spine',
    'Use the Validator → VAIG → REHT → Core → RACS runtime signature consistently',
    'Distinguish technical, business and policy evidence',
    'State the product boundaries and preserve human authority',
  ],
  approvedLanguage: [
    'VALO is execution-governance infrastructure for consequential action.',
    'VALO evaluates whether a specific action may become real.',
    'VAIG evaluates. REHT clears. Core enforces. RACS commits.',
    'The platform stays fixed while the business envelope changes.',
    'Human and domain authority remain final.',
  ],
  prohibitedLanguage: [
    'VALO determines clinical truth.',
    'VALO replaces authorization or identity systems.',
    'VALO guarantees a safe or correct outcome.',
    'VALO suppresses or controls Philips alerts in this demo.',
    'VALO removes the need for human review.',
  ],
  completionChecklist: [
    'Deliver the 60-second presenter contract without changing component roles',
    'Explain all three evidence classes using one scenario',
    'Explain ALLOW and STEP_UP without presenting REHT as an AI model',
    'Describe one non-healthcare business envelope using the same governance spine',
    'State at least three prohibited claims and the correct boundary instead',
  ],
} as const
