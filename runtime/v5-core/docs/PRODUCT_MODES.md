# Product modes

“Sidecar, MCP, HTTP Proxy and Wrapper are not duplicates” remains true: they are
adapter/deployment forms, and none is an independent enforcement core.

All consequence-bearing modes use the same chain: RacsBridge → AiPlsCore →
GoldenExecutionPath → ExclusiveEffector. Adapters do not own governance
semantics.

Compatibility invariant: `same governance input -> same governance decision`.

## Integration

Integration mode verifies a synthetic signed permit, durably consumes it, asks
AiPlsCore for ALLOW, and may call a synthetic effector. Its execution receipt
states whether execution was attempted and whether an effect was applied.

## Shadow

Shadow mode performs verification and binding checks and reports:
`execution_allowed`, `would_execute`, `effect_applied=false`,
`shadow_mode=true`, reason, permit/action identifiers, binding/replay/expiry
status, and observation time. It never constructs execution authorization,
calls an effector, or writes the production consumption registry.

## Legacy telemetry compatibility

The HTTP/MCP/sidecar frame path and L1 ValoGuardrail remain available for
compatibility and parity observation. They are not the canonical execution
boundary. A legacy telemetry audit entry is not an execution receipt.

## Not implemented

Hardware-backed human reset and production WORM storage are not implemented.
The file-backed Python WORM component is a simulation. TLA+ coverage is bounded
to models and does not constitute formal verification of the Rust execution
chain.
