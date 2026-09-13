# Work claim — capability transport contract

Owner: ChatGPT / Njål

Canonical base: `6459f1ef0f1fe248d5425d22d8ca679448e3d61c`

Branch: `adopt-fastapi-capability-transport-contract`

Active delivery: adopt the useful FastAPI/OpenAPI contract pattern without moving transport or authorization semantics into Kernel.

Owned files:
- `.workclaims/2026-09-04-fastapi-capability-transport.md`
- `docs/capability_transport_contract_v1.md`
- `docs/external_adapters_v2.md`

Dependencies:
- existing Kernel canonical contracts
- existing REHT/RACS/Gateway/Veritas boundaries
- no new runtime dependency

Acceptance:
- transport contract is explicitly non-authorizing
- executable API surfaces derive request/response schema from canonical typed contracts
- OpenAPI/SDK/docs/contract tests are generated artifacts, not parallel truth sources
- transport frameworks remain replaceable capability providers
- no `/execute` or direct effect path is introduced
- consequence-bearing effects still require fresh REHT authorization and governed Gateway enforcement
