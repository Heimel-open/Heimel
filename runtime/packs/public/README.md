# VALO Public Pack — Public Application Golden Path

Second vertical proof of the VALO architecture: a public case process run over
the same generic core as the commercial electrician job.

```text
søknad -> identitet -> hjemmel -> kompetanse -> evidens -> kvalifikasjon
      -> saksforberedelse -> vedtak -> underretning -> klagefrist -> avslutning
```

**Kanonisk regel: Ingen offentlig agentisk handling uten eksplisitt hjemmel og
kompetanse.**

## What it proves

- VALO can run **myndighetsnær koordinering uten å eie myndigheten**.
- The **same Kernel, Workflow ISA and Function Fabric** that drive the
  commercial electrician job drive a public application — no core split.
- Only the Public Pack is public-sector-specific.
- Legal basis, competence, delegation, representation, habilitet, rights
  effect and appeal rights are all first-class and enforced.

## Dependency anchors

- `valo-kernel` @ `108f770`
- `valo-workflow-isa` @ `2ccb25f`
- `valo-function-fabric` @ `b2f058d`

## Install & verify

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e ../valo-kernel --no-deps
.venv/bin/pip install -e ../valo-workflow-isa --no-deps
.venv/bin/pip install -e ../valo-function-fabric --no-deps
.venv/bin/pip install -e ../valo-trades-pack --no-deps
.venv/bin/python -m pytest -q
```

The positive golden path and the ten negative demonstrators run as tests.

- **The deterministic Public admissibility check runs at the PRE-EXECUTION boundary**, before REHT/Gateway: a decision the invariant rejects never reaches the Gateway (no real-world effect before rejection).
