# VALO Trades Pack — Electrician Golden Path

First vertical proof of the VALO architecture: one complete, realistic business
workflow run end-to-end over the generic core.

```text
Real customer need
        ↓
Function program (Function Fabric)
        ↓
Workflow ISA
        ↓
Governed execution (REHT/RACS/Gateway/Veritas/BARO)
        ↓
Real-world effect
        ↓
Verified business state (Kernel)
```

## What it proves

- The same Kernel, Workflow ISA and Function Fabric that serve public sector
  drive a commercial electrician job end to end.
- Only the Trades Pack is electrician-specific.
- `EV_CHARGER_JOB` runs request → quote → booking → qualified worker →
  evidence → invoice → payment → verified completion → CLOSED.
- Negative paths are enforced: expired credential at dispatch, double booking,
  quote drift, fake completion, green-while-dead payment, revoked authority,
  customer scope change.

## Dependency anchors

- `valo-kernel` @ `108f770`
- `valo-workflow-isa` @ `2ccb25f`
- `valo-function-fabric` @ `10e3e7a`

See `repo-manifest.yaml`. CI installs all three pinned anchors.

## Install & verify

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pip install -e ../valo-kernel --no-deps
.venv/bin/pip install -e ../valo-workflow-isa --no-deps
.venv/bin/pip install -e ../valo-function-fabric --no-deps
.venv/bin/python -m pytest -q
```

The golden path and the seven negative demonstrators run as tests.
