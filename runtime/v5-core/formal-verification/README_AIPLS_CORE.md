# AiPlsCore bounded model

This model is separate from the legacy L1 models. It covers the bounded
AiPlsCore state transition and abstract permit-consumption/receipt properties.
It does not prove the Rust implementation, signature verifier, filesystem
durability, or an effector.

Run:

```sh
java -cp tools/tla2tools.jar tlc2.TLC \
  formal-verification/AiPlsCore.tla \
  -config formal-verification/AiPlsCore.cfg
```

A code-to-spec refinement mapping has not yet been documented, so no claim of
formal verification of the Rust execution chain is made.
