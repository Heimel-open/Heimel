# valo-insurance-pilot

Carrier-facing pilot pack for **machine-underwritable assurance**. Built on the
frozen `valo-insurance-pack` v0.1.0 baseline — it does **not** extend the core.

## The thesis

> **Underwriting is becoming executable.** A carrier can express a coverage
> condition as a machine-checkable `AssuranceProfileV1`, have every
> consequence-bearing action evaluated against it at commit time, and settle
> claims from a cryptographically-bound `ClaimsEvidencePackV1` — without the
> insurance layer ever granting execution authority.

## What this pack contains

| Asset | Path | Purpose |
|---|---|---|
| Scenario | `scenario/high-value-procurement.md` | One concrete use case |
| Policy condition | `scenario/policy-condition.yaml` | Draft coverage condition |
| Sample profile | `sample-profile/high-value-procurement.json` | `AssuranceProfileV1` |
| Sample claims pack | `sample-claims-pack/high-value-procurement-claims-pack.json` | Verifiable evidence bundle |
| Architecture | `architecture/1-page-architecture.md` | One-page chain |
| Generator | `scripts/generate_sample_claims_pack.py` | Reproduces the sample |

## The frozen chain

```text
AssuranceProfileV1
  -> CommitAssuranceEvaluationV1  (capability-set subsumption, fail-closed)
  -> reht                          (sole authorization boundary)
  -> RACS                          (signed GovernanceClearance verification)
  -> Gateway/PEP                   (execution enforcement point)
  -> Veritas                       (write-once receipt attestation)
  -> ClaimsEvidencePackV1          (deterministic, offline-verifiable)
```

Non-authority invariant: the insurance layer evaluates and attests; it never
issues a permit or executes an action.

## Verify the sample claims pack

```bash
pip install "valo-insurance-pack @ git+https://github.com/nsolland/valo-insurance-pack.git@v0.1.0"
python3 - <<'EOF'
import json
from valo_insurance_pack.claims.verifier import verify_claims_evidence_pack
from valo_insurance_pack.contracts.claims_evidence_pack import ClaimsEvidencePackV1
pack = ClaimsEvidencePackV1.model_validate(json.load(open("sample-claims-pack/high-value-procurement-claims-pack.json")))
report = verify_claims_evidence_pack(pack)
print("valid:", report.is_valid, "| checks:", len(report.checks_performed), "| errors:", report.errors)
EOF
```

## Reproduce the sample

```bash
PYTHONPATH=/path/to/valo-insurance-pack/src python3 scripts/generate_sample_claims_pack.py
```

The generated pack is a **synthetic** sample (mock ERP, mock authorizer) used
only for carrier-facing material. A real claims pack comes from the shadow
pilot chain.

## Out of scope

No new core features. This repo freezes the product slice and produces
carrier-facing material only.
