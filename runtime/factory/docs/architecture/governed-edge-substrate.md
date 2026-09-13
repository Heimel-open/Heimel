# Governed edge substrate

Edge hardware and firmware are replaceable execution substrate. They can provide capabilities and evidence, but they do not receive or manufacture execution authority.

## Contract

`EdgeSubstrateManifest` pins the runtime facts that matter before a constrained device enters a governed path:

- runtime and board family
- firmware version
- accountable owner and device identity
- declared capabilities
- access and data scopes
- verification references
- verified network/TLS state
- audit reference

The manifest has `authority_effect = none`. Raw passwords, tokens, secrets and credentials are outside the contract and fail closed at the parser boundary.

`EdgeAdmissionRequest` describes one requested use of the runtime: observation, network egress or actuation. Required capabilities and requested access/data scopes are explicit.

`EdgeSubstrateDecision` is deterministic and replayable. The same pinned manifest and request produce the same `replay_digest`.

## Consequence-bearing paths

Observation may be admitted locally when the declared capabilities and scopes are sufficient.

Network egress is never executed by this module. An admissible request is routed to the governed egress boundary. Network use must have been verified for the pinned runtime; sensitive egress additionally requires verified TLS. A cloud-specific request must declare cloud egress as a capability.

Actuation is never authorized by this module. An otherwise admissible actuation request stops at `ADMISSIBLE_TO_REHT` and requires fresh REHT authorization before any effect path can continue.

This preserves the canonical separation:

`device facts -> substrate admission -> governed boundary -> fresh authorization -> effect -> receipt`

Substrate evidence cannot be promoted into authority.

## Why the runtime is pinned

Microcontroller support varies by board and firmware. A generic statement such as `runtime_family = micropython` is not sufficient evidence that networking, TLS, GPIO, I2C, SPI or another capability works on a particular device. Board family, firmware and verification references are therefore explicit inputs.

This also keeps hardware outside the strategic contract. RP2040, another MCU, Linux edge nodes or future runtimes can implement the same admission shape without changing REHT/RACS semantics.

## External patterns adopted

Three reviewed sources supplied useful validation and implementation pressure:

- Microsoft, *The AI Strategy Roadmap* (2026): explicit ownership, identity/access boundaries, controlled data availability, auditability and governance that scales with agent use. VALO adopts those as substrate facts and scope checks, not as Microsoft policy authority.
- Charles Bell, *MicroPython for the Internet of Things*, Second Edition (2024): board/firmware variability, network preflight, encryption/TLS capability and the principle that cloud connectivity should be deliberate rather than assumed. VALO adopts these as edge-runtime admission requirements, not book code.
- Garlando McCord Sr., *The Right Questions to Ask of the Universe — Operational Inquiry Spine v1.0* (2026): evidence traceability and replayability are useful external validation. The named framework, Greek primitives and its proprietary structure are not reproduced or implemented. Commercial/derivative use is explicitly license-restricted in the reviewed source; VALO therefore keeps only independently expressed generic evidence-engineering principles.

None of these sources may grant authority, alter policy, bypass REHT/RACS, or become a required external dependency.
