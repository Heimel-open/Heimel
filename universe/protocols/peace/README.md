# PEACE Protocol

PEACE is an open protocol for keeping authority and authoritative state under the control of the person or organisation they belong to while models, agents, devices, compute and service providers remain replaceable.

> Everything can be routed except sovereignty.

## What PEACE defines

PEACE separates the governed domain from replaceable workers and providers.

```text
authoritative state  != provider state
proposal             != decision
authorization        != effect
evidence             != authority
routing              != authority
credential           != actor
replica              != sovereign
```

Any consequence-bearing action must pass a fresh authority check at the effect boundary. No model, router, cloud, payment rail or other replaceable provider becomes an authority root merely by participating in execution.

## Public interoperability surface

This repository intentionally contains only the material required to understand and independently implement the public PEACE interoperability contract:

- [Protocol specification](protocol/PEACE_PROTOCOL_V0.md)
- [Envelope schema](schemas/peace-envelope-v0.schema.json)
- [Conformance vectors](conformance/conformance-v0.json)

Research derivations, experimental routing/mesh work, model-specific state-transfer mechanisms, commercial capability composition, internal assurance methods and product implementation architecture are outside the public protocol surface.

Current draft: `0.1.0-draft.1`

## Relationship to reht

PEACE defines governed-domain and authority interoperability semantics. `reht` is one possible implementation of a fresh consequence gate. It is not required by PEACE.

## Project

Apache License 2.0. Contributions and protocol governance are documented in [CONTRIBUTING.md](CONTRIBUTING.md) and [GOVERNANCE.md](GOVERNANCE.md). Security reports: [SECURITY.md](SECURITY.md).
