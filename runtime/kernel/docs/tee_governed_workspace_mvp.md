# TEE-backed Governed Workspace MVP

## Purpose

A Governed Workspace may require a hardware-attested confidential execution substrate before a worker receives the governed projection.

TEE is evidence about the execution environment. It is not authority.

Canonical boundary:

```text
Kernel governed state
  -> Governed Workspace
  -> verified TEE substrate attestation
  -> replaceable worker
  -> deterministic conformance
  -> attested execution binding
  -> fresh REHT authorization
  -> governed Gateway effect
  -> Veritas receipt / verification
```

The TEE proves properties of where execution is occurring. VALO still determines whether the proposed consequence-bearing action may occur.

## MVP contract

`ExecutionSubstrateRequirement` declares the workspace substrate constraint:

- explicit allowed TEE type(s)
- optional allowed measurement(s)
- maximum attestation age
- optional exact model digest
- optional exact workload digest
- confidentiality, integrity and isolation required

`ExecutionSubstrateAttestation` is provider-neutral verified evidence. It carries:

- `tee_type`
- `gpu_identity`
- `cc_mode`
- `measurement`
- `attestation_verifier`
- `attestation_evidence_digest`
- `attested_at`
- `valid_until`
- `model_digest`
- `workload_digest`
- deterministic `attestation_digest`

No named vendor, cloud or verifier is a Kernel dependency.

## Fail-closed rules

A TEE-required workspace is not compiled when attestation is:

- missing
- unsealed or tampered
- INVALID, REVOKED or UNKNOWN
- outside the allowed TEE type
- outside an allowed measurement set
- missing required confidentiality, integrity or isolation claims
- bound to a different model or workload
- future-dated, expired or stale
- valid for less time than the Governed Workspace

The same checks run again at candidate conformance. A stale attestation produces a non-PASS result, so no attested execution binding can be created.

## Execution binding

A PASS result creates `AttestedWorkspaceExecutionBinding` around the existing non-authoritative `WorkspaceExecutionBinding`.

The binding carries the exact attestation digest and receipt-relevant substrate claims forward to REHT/Gateway/Veritas. It still has:

```text
authority_effect = NO_AUTHORITY_CREATION
can_issue_clearance = false
```

The Kernel does not authorize or execute the external effect.

## Important boundary

This MVP validates and binds already-verified attestation evidence. It does not implement NVIDIA, AMD, Intel, cloud-specific quote verification or certificate-chain validation inside Kernel.

The verifier is an adapter/provider. Cryptographic quote verification happens outside the deterministic Kernel contract and returns normalized attestation evidence.

Fresh execution-time authorization remains REHT's responsibility. The governed effect path remains Gateway-owned. Veritas remains responsible for preserving and verifying execution evidence and outcome.

## Determinism

With identical Kernel state, WorkspaceSpec, substrate requirement, normalized attestation and evaluation time, compilation and conformance are deterministic. No model replay is required.
