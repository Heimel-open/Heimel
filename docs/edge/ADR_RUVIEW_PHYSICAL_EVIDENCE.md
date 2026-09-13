# ADR — RuView as physical-world evidence source

Status: adopted
Date: 2026-08-09

## Decision

RuView is adopted as an optional local physical-world evidence source for VALO Edge.
It is not an authorization component, not an authoritative world model, and not a
direct state writer.

Canonical flow:

```text
RuView / WiFi CSI
      |
      v
RuViewAdapter
      |
      +--> SensorEvidenceV1
      +--> PhysicalStateEvidenceV1
      +--> ModelSignalV1 (only when a model actually participated)
      |
      v
Local VAIG Edge
      |
      v
micro-REHT / REHT for an exact consequence
      |
      v
Gateway -> physical world -> Veritas
      |
      v
verify / admit / canonical Kernel event
      |
      v
VALO Kernel -> WorldState
```

The authoritative World Model is already part of `nsolland/valo-kernel`. Its
contracts describe the governed world, `WorldState` is the working state, and the
Kernel is the deterministic state owner. RuView therefore belongs before the
Kernel as an observation/evidence source, not inside `WorldState` and not beside
the Kernel as another world model.

## Adopted RuView patterns

- Local, camera-free WiFi CSI sensing is useful as an additional physical evidence
  channel where vision is undesirable or line-of-sight is weak.
- Bind every observation to source, time, environment, calibration and pipeline
  version before VALO accepts it as sensor evidence.
- Preserve an upstream witness/attestation reference when available; deployments
  may require it fail-closed.
- Keep model confidence and calibration explicit. A model-derived RuView signal is
  evidence, never authority and never automatically physical truth.
- Support a model-free path for signal-processing outputs; do not invent model
  evidence when no model participated.
- Treat simulated RuView data as test evidence only. It cannot establish physical
  reality.
- Environment-specific calibration is part of admissibility. RuView documents that
  its adaptive classifier should be retrained when the ESP32 moves or the physical
  room setup changes.
- Presence, occupancy, falls, pose and vital-sign outputs remain observations or
  inferences until independently admitted. They must not become CONFIRMED Kernel
  facts merely because RuView emitted them.

## Benchmark discipline

Upstream benchmark surfaces are not internally consistent enough to become VALO
truth. As checked on 2026-08-09, the current RuView GitHub README says the older
"100% presence" result came from a single-class recording and was retracted, while
the `ruv/ruview` Hugging Face material still exposes 100% presence wording.

VALO therefore stores benchmark/model/version provenance as evidence metadata only.
Runtime authorization must use evidence from the deployed source and current
calibration, not marketing or model-card accuracy claims.

## Boundaries

Forbidden:

- RuView -> actuator directly
- RuView -> authoritative `WorldState` directly
- RuView confidence -> REHT ALLOW by itself
- simulated observations -> physical truth
- benchmark claims -> runtime evidence

Allowed:

- RuView -> VALO Edge evidence contracts
- Local VAIG -> explicit evidence gaps, freshness and contradictions
- micro-REHT/REHT -> authorize an exact consequence using the complete context
- Veritas/admission -> canonical Kernel event -> deterministic `WorldState`

## Sources reviewed

- https://github.com/ruvnet/RuView
- https://github.com/ruvnet/RuView/blob/main/docs/user-guide.md
- https://huggingface.co/ruv/ruview
