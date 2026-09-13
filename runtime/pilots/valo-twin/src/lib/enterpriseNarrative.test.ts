import { describe, expect, it } from 'vitest'
import {
  ENTERPRISE_GOVERNANCE_STAGES,
  ENTERPRISE_POSITIONING,
  INDUSTRY_ENVELOPES,
  RUNTIME_SIGNATURE,
} from './enterpriseNarrative'

describe('canonical enterprise governance narrative', () => {
  it('keeps the enterprise governance spine in canonical order', () => {
    expect(ENTERPRISE_GOVERNANCE_STAGES.map((stage) => stage.id)).toEqual([
      'purpose',
      'authority',
      'evidence',
      'evaluation',
      'clearance',
      'commit',
      'outcome',
      'receipt',
    ])
  })

  it('preserves the signature runtime pipeline', () => {
    expect(RUNTIME_SIGNATURE.map((stage) => stage.label)).toEqual([
      'Validator',
      'VAIG',
      'REHT',
      'Core',
      'RACS',
    ])
  })

  it('reuses one platform contract across four business envelopes', () => {
    expect(INDUSTRY_ENVELOPES.map((envelope) => envelope.domain)).toEqual([
      'Healthcare',
      'Finance',
      'Manufacturing',
      'Public sector',
    ])
    expect(INDUSTRY_ENVELOPES.filter((envelope) => envelope.status === 'LIVE DEMO')).toHaveLength(1)
  })

  it('positions VALO around execution governance rather than model evaluation', () => {
    expect(ENTERPRISE_POSITIONING.category).toBe('Execution Governance Platform')
    expect(ENTERPRISE_POSITIONING.headline).toContain('never authorizes business action')
    expect(ENTERPRISE_POSITIONING.signature).toContain('RACS commits')
  })
})
