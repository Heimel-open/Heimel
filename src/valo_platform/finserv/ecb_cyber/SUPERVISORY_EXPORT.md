# ECB Cyber Supervisory Export (#220)

Presentation + packaging layer for the ECB Cyber Action Plan vertical. Consumes
an existing `SubmissionPackage` (built from ECB data → `EcbCyberWorkflow` →
`ECBReadinessDashboard`) and produces regulator-ready artefacts: deterministic
XML, regulator-readable HTML, optional PDF, and a proof-of-evidence manifest.

## Architecture

```
ECB Cyber models (RegulatoryRequirement, Control, ControlAssessment,
  AccountableOwner, Evidence, MitigationAction, ThreatObservation,
  Approval, ControlException, Receipt, SubmissionPackage)
        |
        v
ExposureGraph (node refs linked from controls/assets)
        |
        v
EcbCyberWorkflow  (VAIG evaluates -> REHT clears -> Receipt)   [authority layer]
        |
        v
ECBReadinessDashboard  (presentation of readiness/gaps)        [presentation layer]
        |
        v
SubmissionPackage  (aggregated governed evidence)             [input contract]
        |
        v
SupervisoryExportBuilder  (THIS MODULE)                       [packaging layer]
        |
        +-- XML  (deterministic, sorted, machine-readable)
        +-- HTML (Jinja2; usable without PDF dependency)
        +-- PDF  (WeasyPrint; OPTIONAL [ecb] extra; fails clearly if absent)
        +-- ExportManifest (proof-of-evidence linkage)
```

## Data flow

`data -> EcbCyberWorkflow -> ECBReadinessDashboard -> SubmissionPackage
-> SupervisoryExportBuilder -> {XML, HTML, PDF, Manifest}`

The export layer performs **no** risk evaluation, admissibility decision, or
clearance issuance. It packages evidence that already exists.

## Export schema (versioned)

`SCHEMA_VERSION = "ecb-cyber-export/1.0"`, `POLICY_VERSION =
"ecb-cyber-action-plan/2026"`.

XML root `<ecbSupervisorySubmission>` carries: `schemaVersion`, `policyVersion`,
`submissionId`, `bank`, `asOf`, `generatedAt`, `readinessScore`, and child
sections: `evidenceManifest`, `regulatoryScope`, `controls`, `owners`,
`mitigationActions`, `threatObservations`, `approvals`, `exceptions`,
`unresolvedGaps`, `receipts`, `exposureGraphRefs`, `limitations`.

## Evidence linkage (proof-of-evidence)

The manifest links, per submission:
- controls <-> assessments <-> evidence (by `evidence_id`)
- assessments/actions -> accountable owners (by `owner_id`)
- mitigation actions -> milestones
- approvals (governance levels) -> actions
- exceptions -> controls (with expiry + receipt signature)
- canonical `Receipt` references (`receipt_id`) -> audit chain
- `GovernanceClearance` references (carried in `Receipt.metadata.clearance_ref`)
- exposure-graph node references (when an `ExposureGraph` is supplied)

Integrity fields in the manifest: `submission_id`, `generated_at`,
`schema_version`, `policy_version`, `source_snapshot_ids`, `receipt_chain_refs`,
`clearance_refs`, `content_hash` (SHA-256 of the XML), `evidence_count`,
`unresolved_gap_count`, `stale_assessment_count`.

## Deterministic behaviour

- XML element ordering is sorted (by `control_id`, `requirement_id`, `owner_id`,
  `action_id`, `observation_id`, `approval_id`, `exception_id`, and receipt/
  clearance refs) so byte-identical inputs produce byte-identical output.
- `generatedAt` is derived from the package's `as_of` (not wall-clock time), so
  repeated exports of the same package are stable.
- Receipt IDs must be supplied explicitly (or seeded) for determinism; the
  default `Receipt` UUID factory is non-deterministic — tests pin `receipt_id`.

## Fail-closed validation

`SupervisoryExportBuilder.validate()` returns a structured `ValidationResult`
(with error issues) and **does not** generate an export when any of:

- required evidence is missing (an assessment references an unknown `evidence_id`)
- receipt references are broken (a `Receipt` without `receipt_id`)
- accountable owners are absent (controls present but no `owners`)
- required fields are incomplete (`package_id`, `bank`, `as_of`,
  `readiness_score`, `export_format`)
- the package schema is invalid (`export_format` not in `pdf|xml`)

Fail-closed means: a structured validation failure is returned; no export is
produced; and **no REHT verdict is created**.

## Known limitations

- `SubmissionPackage` was extended (this issue) with `assessments`, `evidence`,
  `owners`, `threats`, `approvals`, `exceptions` to carry the evidence the
  export links. These are optional on the package; validation fails closed if
  required linkages are absent.
- PDF rendering requires the optional `ecb` dependency extra (WeasyPrint). HTML
  export is always available and sufficient for review.
- The export does not transmit to the ECB; it produces a document for the
  institution to submit through the competent authority's channel.
- Determinism assumes pinned `receipt_id` values; live Receipts generated with
  the default UUID factory will vary between runs.

## Regulatory disclaimer

This artefact is a packaging of records already produced by VAIG / REHT / RACS.
It asserts **no regulatory approval** and **no acceptance by the ECB**.
Submission acceptance is determined solely by the competent authority.

## Testing

- `tests/test_ecb_cyber_reporting.py` — unit: deterministic XML, stable ordering,
  valid evidence refs, missing-evidence failure, broken-receipt failure, stale
  assessment, unresolved gap, HTML render, PDF adapter behaviour, no governance
  authority in the reporting layer.
- `tests/integration/test_ecb_cyber_reporting_integration.py` — full slice on
  synthetic Meridian Euro Bank data: data -> workflow -> dashboard -> package ->
  XML/HTML/manifest.

## Repository discipline

- Branch: `hermes/ecb-cyber-220-supervisory-export`
- Reuses canonical contracts: `SubmissionPackage`, `GovernanceClearance`,
  `Receipt`, `EcbCyberWorkflow`, `ECBReadinessDashboard`, `ExposureGraph`.
- Does NOT evaluate risk, decide admissibility, issue `GovernanceClearance`,
  create a second receipt type, modify VAIG/REHT, or claim ECB approval.
