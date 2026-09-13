# Work anchor — x402 / MPP settlement-route binding

Status: ACTIVE
Owner: ChatGPT
Claimed: 2026-08-16

Repository: `nsolland/valo-reht`
Canonical base: `a13719ed015d13915f3264ee55236965b8fe9de2`
Branch: `docs/x402-mpp-settlement-route-binding`

Owned files for this delivery:
- `docs/EXECUTION_AUTHORIZATION_REQUIREMENTS_V1.md`
- `docs/adoption/X402_MPP_AGENTIC_COMMERCE.md`
- `docs/work-anchors/2026-08-16-x402-mpp-settlement-route-binding.md`

Scope:
- make settlement-route mutation an explicit fresh-authorization condition;
- bind network, asset, recipient/payee, facilitator/payment processor, resource and amount where they are consequence-bearing;
- classify x402scan/MPPScan-style explorer data as discovery/observation evidence, never authority;
- preserve rail/provider neutrality and the single governed effect path.

Dependencies: none beyond current REHT execution-authorization contract.
