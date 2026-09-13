# Publication status

Status date: 2026-08-22

PEACE is a public, vendor-neutral interoperability protocol for governed-domain and authority semantics. It is not an authorization engine, execution runtime or source of authority.

## Public surface

The intended public surface is deliberately narrow:

- normative core protocol semantics required for interoperability;
- deterministic envelope schemas;
- core conformance vectors;
- licensing, governance, contribution and security process.

## Explicit exclusions

The public surface does not include or require:

- research derivations or discovery lineage;
- experimental routing/capability composition or model-specific state transfer;
- proprietary authorization/evaluation logic;
- private organizational policy or authority data;
- production credentials or deployment configuration;
- private runtime, product or infrastructure implementation.

## Publication rule

This is a public repository: a branch push is already disclosure. New substantive material must receive explicit human IP/publication review before the first public push. Merge-time CI is defense in depth, not the primary IP gate.

Repository visibility is not a versioned release by itself. A release requires an immutable version/tag, exact commit, declared license and green conformance checks on that commit.
