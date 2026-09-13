# Work claim: Sim capability route boundary

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 0a8205f8a3c169eede7b7d8e50c4d66a950d5c32
Branch: research/sim-capability-route

Active delivery: adopt the useful execution-architecture patterns from simstudioai/sim and define a VALO integration/demonstrator in which Sim remains a capability composition/execution surface while every consequence-bearing effect is forced through fresh REHT/RACS authorization before external execution.

Owned files:
- docs/sim_capability_route_boundary.md
- .workclaims/2026-09-03-sim-capability-route.md

Dependencies:
- existing workspace conformance and sealed execution binding semantics
- existing REHT/RACS execution-authority boundary
- existing external adapter boundary

Invariants:
- Sim or any equivalent workflow runtime is a capability route, never an authority root
- credentials, workflow approval, model output, connector availability and HITL blocks do not create handlingsrett
- consequence-bearing tool execution has no permitted direct effect path around REHT/RACS
- authority is resolved fresh at consequence time
- DENY, DEFER, STEP_UP and HALT produce null external effect
- external runtime logs are evidence inputs, not authoritative VALO state
- provider/runtime invocation identity is preserved as provenance but cannot override VALO execution identity or authority
- named external runtimes remain optional adapters; native VALO semantics have zero dependency on Sim
