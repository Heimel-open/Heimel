# Source pattern adoption — 2026-08-17

Status: implemented in this change set.

## Active delivery

Add one provider-neutral edge-substrate admission boundary that turns runtime, ownership, scope and verification facts into a deterministic non-authorizing decision before edge work can reach governed egress or REHT.

## Adopted

### Microsoft — AI Strategy Roadmap

Adopt:

- explicit accountable owner and device identity
- explicit access and data scopes
- auditable runtime records
- verified foundations before scaling or wider integration
- agent/runtime visibility as a governance requirement

Do not adopt Microsoft products, operating model or policy as an authority dependency.

### Charles Bell — MicroPython for the Internet of Things, Second Edition

Adopt:

- exact board/runtime/firmware declaration
- verified networking before network-dependent work
- verified TLS for sensitive egress
- capability declaration for GPIO/I2C/SPI/network and similar device functions
- cloud egress only when explicitly requested and supported

Do not copy book source code or couple the contract to MicroPython. MicroPython is one replaceable runtime family.

### Garlando McCord Sr. — Operational Inquiry Spine v1.0

Adopt only independently expressed generic engineering ideas:

- consequence-bearing requests carry evidence references
- deterministic replay material is bound into the decision digest
- refusals expose the next boundary needed to continue safely

Do not implement the named Spine, Greek primitives, branded taxonomy or proprietary document structure. The reviewed document states that commercial/derivative use requires written permission, so this adoption deliberately remains non-derivative.

## Invariants

- `authority_effect` is always `none`.
- Edge admission never executes.
- Raw credentials are rejected.
- Undeclared capabilities or scope expansion fail closed.
- Sensitive network egress requires verified TLS.
- Network egress routes to the governed egress boundary.
- Actuation routes to fresh REHT; substrate admission cannot authorize it.
- External source material is validation/input, never policy or authority.

## Files

- `lib/edge_substrate.py`
- `tests/test_edge_substrate.py`
- `schemas/edge-substrate-decision.schema.json`
- `docs/architecture/governed-edge-substrate.md`
- `work/GOVERNED_EDGE_SOURCE_ADOPTION_CLAIM.md`

## Verification

The focused edge-substrate suite contains deterministic checks for non-authority, network/TLS preflight, scope containment, evidence requirements, replay stability, raw-secret rejection and fresh-REHT routing for actuation.
