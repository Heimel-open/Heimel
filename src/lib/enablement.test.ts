import { describe, expect, it } from 'vitest'
import {
  AMBASSADOR_ONBOARDING,
  HEALTHCARE_EVIDENCE_CLASSES,
  PRESENTER_CONTRACT,
} from './enablement'

describe('Twin commercial enablement contracts', () => {
  it('separates technical, business and policy evidence', () => {
    expect(HEALTHCARE_EVIDENCE_CLASSES.map((item) => item.id)).toEqual([
      'technical',
      'business',
      'policy',
    ])
    expect(HEALTHCARE_EVIDENCE_CLASSES[0].status).toBe('PASS')
    expect(HEALTHCARE_EVIDENCE_CLASSES[1].status).toBe('STEP_UP')
    expect(HEALTHCARE_EVIDENCE_CLASSES[2].status).toBe('RECHECK')
  })

  it('locks the presenter contract to a versioned 60-second narrative', () => {
    expect(PRESENTER_CONTRACT.version).toBe('1.0.0')
    expect(PRESENTER_CONTRACT.targetDurationSeconds).toBe(60)
    expect(PRESENTER_CONTRACT.steps.map((step) => step.id)).toEqual([
      'problem',
      'proposed-action',
      'readiness',
      'evidence',
      'evaluation',
      'clearance',
      'enforcement',
      'proof',
    ])
    expect(PRESENTER_CONTRACT.opening).toContain('not necessarily authorized')
    expect(PRESENTER_CONTRACT.closing).toContain('may become real')
  })

  it('preserves component roles and human authority in the script', () => {
    const completeScript = PRESENTER_CONTRACT.steps.map((step) => step.script).join(' ')

    expect(completeScript).toContain('VAIG evaluates')
    expect(completeScript).toContain('REHT asks')
    expect(completeScript).toContain('Core enforces')
    expect(completeScript).toContain('RACS controls')
    expect(completeScript).toContain('Human clinical authority remains final')
  })

  it('defines approved language, prohibited claims and a completion check', () => {
    expect(AMBASSADOR_ONBOARDING.approvedLanguage).toContain(
      'VALO is execution-governance infrastructure for consequential action.',
    )
    expect(AMBASSADOR_ONBOARDING.prohibitedLanguage).toContain(
      'VALO guarantees a safe or correct outcome.',
    )
    expect(AMBASSADOR_ONBOARDING.completionChecklist).toHaveLength(5)
    expect(AMBASSADOR_ONBOARDING.learningOutcomes).toHaveLength(5)
  })
})
