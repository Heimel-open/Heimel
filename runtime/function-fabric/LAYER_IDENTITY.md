# Layer identity

`valo-function-fabric` defines what real functions mean as programs. It has no
execution identity: it compiles, validates, registers, simulates and explains —
it never executes.

Canonical ownership:

- VALO Kernel owns authoritative world state. Function Fabric never owns or
  copies business truth.
- Workflow ISA owns execution flow. Function Fabric compiles to Workflow ISA
  and never implements a second runtime.
- REHT is the sole execution authorization boundary. CHECK_AUTHORITY produces
  AuthorityEvidence, never an ALLOW.
- RACS, Gateway, Veritas, BARO remain the execution and verification layers.

Forbidden here: Goal Compiler, natural-language planning, Operator, Public UI,
Enterprise control tower, full vertical packs, ERP adapters, LLM agent
frameworks, direct Kernel writes, and any claim that Function Fabric executes.

Function Fabric owns: Function Definitions, the Registry, the Function Graph
language, the compiler (type/effects/governance), the standard library, packs,
simulation, explain, and provenance of compiled execution.
