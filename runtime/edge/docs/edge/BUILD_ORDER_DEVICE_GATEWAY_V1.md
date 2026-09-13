# Build Order: Device Enforcement Gateway V1

Status: IN PROGRESS
Repository: `nsolland/valo-edge`
Canonical base: `64d3e341000b0f49a54a74ef9e57aa5e866c1363`
Branch: `feat/device-gateway-v1`
Owner: ChatGPT implementation worker

## Boundary

The device gateway is mechanical enforcement only. It has no authority, judgment, policy evaluation or model behavior.

It may execute only an exact device command that is cryptographically bound to an ALLOW clearance from micro-REHT.

For industrial recovery, the gateway does not infer intent, reinterpret a recovery plan, choose alternate parameters, synthesize rollback or retry a failed command under the original permit.

## Scope

- verify exact proposal, clearance and command binding
- reject any non-ALLOW outcome
- reject expired or structurally invalid clearances
- require and consume a valid permit exactly once per execution
- reject changed parameters, device ID, cell ID, action type or write-set
- preserve exact register/tag/parameter/value bindings from the authorized command
- reject duplicate or concurrent reuse of the same command/permit use
- require a separate clearance for rollback, compensation, retry or second-write actions
- call a hardware-neutral driver interface
- return actual driver result rather than assume execution
- represent success, failure, timeout and partial execution mechanically
- emit canonical EdgeEnforcementV1 records for downstream Veritas observation

## Acceptance gates

- an ALLOW for one command cannot authorize another command
- a permit for one physical write-set cannot authorize any changed register, tag, parameter or value
- a permit use cannot be consumed twice
- rollback, compensation and retry cannot reuse the original recovery permit
- DENY, DEFER, STEP_UP and HALT can never reach a driver
- driver exceptions and timeouts never become success
- partial execution is distinguishable from complete execution and is preserved for downstream evidence
- gateway has no path that can create, repair or upgrade authority
- tests are deterministic and offline
