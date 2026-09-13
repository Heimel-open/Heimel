# ADR: Perception adapters and evidence lineage

Status: Accepted
Date: 2026-08-21

## Decision

Voice isolation, noise suppression, denoising, enhancement, sensor fusion, preprocessing and equivalent perception transforms are treated as replaceable perception adapters. They are not trusted authority and are not core VALO dependencies.

A perception adapter may improve or transform an observation before downstream interpretation, but it may not silently replace the source observation as the evidentiary source of record.

Canonical lineage:

`original observation -> perception adapter + model/version/config -> transformed observation -> interpreter/STT + model/version -> derived representation/transcript -> downstream evidence -> decision -> action -> receipt`

The original observation remains the source of record where retention is permitted. Derived artifacts must remain attributable to the exact transformation chain that produced them.

## Invariants

1. Perception is not authority. A perception component may transform or classify input; it cannot authorize a consequence.
2. Adapter neutrality. Krisp/VIVA, local DSP, vendor models and future alternatives are interchangeable implementations behind the same boundary.
3. Provenance is mandatory. Evidence derived from transformed input records the source observation reference, adapter identity, adapter/model version, relevant configuration or policy version, transformed artifact reference or digest, and downstream interpreter/model identity.
4. No silent evidentiary substitution. A transformed signal or transcript must not be presented as if it were the unmodified source observation.
5. Deterministic correlation. Source, transformed artifact, interpretation, proposal, decision and receipt must be correlatable through stable references/digests.
6. Fail closed where provenance is required. If a consequence-bearing decision requires attributable perception evidence and the lineage cannot be established, the evidence is inadmissible for that decision.
7. Privacy and minimisation still apply. Preserving lineage does not require retaining raw personal content indefinitely; non-reversible digests and governed retention may be used where policy requires deletion or minimisation.

## Reference pattern: voice

`microphone -> voice isolation -> STT -> VAIG -> micro-REHT -> gateway -> Veritas`

Voice isolation cleans or separates the signal. STT interprets it. VAIG evaluates the resulting evidence/proposal. micro-REHT determines whether the exact consequence is authorized now. The gateway enforces the decision and Veritas records the governed outcome.

Krisp/VIVA is a reference implementation of the perception-adapter pattern only. VALO must not require Krisp or any specific perception vendor.

## Rationale

A governance receipt can be internally correct while still being based on an observation that was materially transformed before the governed boundary. Without lineage across that transform, later verification cannot establish what the system actually observed, what was changed, which model changed it, or whether the derived evidence was admissible.

The architecture therefore keeps perception, interpretation, evaluation, authorization and execution as separate roles: use the right intelligence at the right place, while preserving evidence across every material transformation.
