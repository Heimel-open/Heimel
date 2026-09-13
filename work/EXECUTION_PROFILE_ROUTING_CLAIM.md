# Execution Profile Routing Claim

- Owner: Codex producer
- Repository: nsolland/valo-factory
- Canonical base: main@8774dd444660fa2f883c100516a46f975649edac
- Branch: feat/execution-profile-routing-20260815
- Delivery: hardware-neutral, completion-first execution-profile routing
- Authority effect: none

Owned files:
- work/EXECUTION_PROFILE_ROUTING_CLAIM.md
- lib/execution_profile_routing.py
- bin/valo-profile-route
- schemas/execution-profile-routing-receipt.schema.json
- tests/test_execution_profile_routing.py
- docs/architecture/execution-profile-routing.md

Dependencies:
- Existing provider/harness identities are inputs only.
- REHT remains the execution authorization boundary.
- Verifier evidence may inform observed completion; execution success alone must not be treated as verified completion.
- No dependency on hardware vendor, accelerator type, render-broker internals, or Unsloth internals.

Explicit exclusions:
- No execution authority.
- No runtime dispatch or provider credential changes.
- No global HALT / AuthorizedDelivery / issue #94 changes.
- No benchmark execution.
- No merge or self-attestation; independent QC remains separate.
