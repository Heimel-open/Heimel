# PEACE Protocol v0

**Canonical name:** PEACE Protocol  
**Expansion:** Personal Execution, Authority & Compute Environment  
**Canonical tagline:** **Your Sovereign State.**  
**Manifesto line:** **My mind. My house. My state.**

## Status

PEACE is the canonical name for the person-centric sovereign computing protocol.

The protocol is defined by a small set of world constraints and invariants, not by the current `valo-kernel` implementation. A new implementation should be independently derivable from the PEACE world contract and conformance requirements without copying a reference codebase.

`PACL` / `Personal AI Compute Layer` is deprecated terminology and MUST NOT be introduced into new normative material.

PEACE intentionally does not contain "AI" in the expansion. Models, agents, runtimes and compute are replaceable capability suppliers; they do not define the person's authority or continuity.

## The PEACE question

The canonical starting point is `protocol/peace-v0/PEACE_WORLD_V0.md`:

> Imagine a world where a person can continuously replace phones, models, agents, clouds, devices, runtimes, credentials and compute providers, while any of them may fail, disappear or be compromised. The person must remain the same logical principal, retain constitutional control of their digital domain, use external intelligence without giving it authority, survive changes between proposal and consequence, and preserve evidence without turning evidence automatically into truth or state. What must necessarily be true for that world to remain sovereign, safe and reconstructible?

PEACE is the minimal protocol semantics that fall out of that problem.

## Core distinctions

```text
capability to compute != authority to act
knowledge              != authority
proposal               != decision
authorization          != effect
evidence               != authoritative state
credential             != principal
operational dependency != constitutional control
implementation         != protocol
```

The logical principal remains the authority root. Credentials, keys, devices, models, providers, runtimes and execution locations may rotate or disappear without becoming the source of authority.

## Derived minimal lifecycle

A PEACE-conformant design must preserve semantic separation equivalent to:

```text
authoritative state
  -> bounded projection / disclosure
  -> replaceable worker / compute
  -> candidate
  -> fresh exact consequence authorization
  -> effect
  -> receipt / evidence
  -> admitted state transition
```

Recovery must preserve the same logical operative domain across replacement infrastructure.

This is a semantic lifecycle, not a required component diagram. Implementations may split, combine or rename internal components as long as the boundaries remain true.

## Sovereignty test

PEACE passes its sovereignty test only if loss or replacement of a provider, model, device, runtime, credential, key or compute substrate does not by itself destroy the person's ability to reconstruct and continue the operative domain without transferring constitutional control to the replacement infrastructure.

Capability may degrade. Constitutional control must survive.

## Implementation status

The Python `valo-kernel` work on PR #51 is one executable PEACE architecture proof. It demonstrates persistent governed state, replaceable credential custody, governed projection/disclosure, route admissibility, candidate flow, consequence-time authorization, receipts, runtime-loss recovery and a bounded TLA+ model checked by TLC.

It is **not** the normative PEACE runtime and Python has no privileged status. Another implementation may use another language, runtime, topology, storage model or cryptographic mechanism if it preserves PEACE semantics and passes the applicable conformance vectors.

VALO-specific components such as Kernel, reht, RACS, Gateway and Veritas are one composition that can realize PEACE. They are not mandatory PEACE vocabulary for independent implementations.

## Canonical protocol artifacts

- `protocol/peace-v0/PEACE_WORLD_V0.md` — the constraint-first world statement used for independent derivation.
- `protocol/peace-v0/PEACE_PROTOCOL_V0.md` — normative invariant and lifecycle semantics.
- `protocol/peace-v0/peace-envelope-v0.schema.json` — language-neutral logical envelope schema.
- `protocol/peace-v0/conformance-v0.json` — observable cross-language semantic vectors.
- `formal/PersonalDomain.tla` — bounded formal model for the current reference profile, not a universal implementation mandate.

## Naming rules

- Use **PEACE Protocol** for the protocol family.
- Use **Your Sovereign State.** as the canonical public tagline.
- Use **My mind. My house. My state.** as the manifesto line.
- Use **PEACE environment** for one person's governed operative domain where a noun is needed.
- Use **sovereign-domain continuity** for the implemented continuity invariant/contract family.
- Do not rename `reht`, RACS, Kernel, Veritas or other existing VALO components to PEACE.
- Do not use `PACL` in new canonical material.
