# AI-PLS Core

A minimal deterministic execution enforcement core for AI systems.

This crate is intentionally separate from the existing `l1-guardian`. It introduces no migration risk and has no dependencies on models, semantics, policy engines, VAIG or REHT.

## Boundary

Upstream systems evaluate reality, authority, policy, evidence and admissibility.

AI-PLS Core only enforces the resulting clearance:

- `Clear` -> `Normal`, execution allowed
- `Uncertain` -> `SafeMode`, execution denied
- `Denied` -> `Halt`, execution denied
- `Invalid` -> `Halt`, execution denied
- technical integrity failure -> `Halt`

Any caller may halt. Only a separately verified human path may reset.

## Non-responsibilities

The core does not interpret:

- AI confidence
- model output
- semantic meaning
- policy
- authority
- purpose
- risk scores

## Run tests

```bash
cargo test --manifest-path ai-pls-core/Cargo.toml
```
