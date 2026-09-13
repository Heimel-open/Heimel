# HEIMEL Live Demos

The demos are designed to make the mechanism observable rather than merely describe it.

## Executable Authority

**Live:** https://reht.valoresearch.org/demos/executable-authority/

Purpose: observe authority being resolved at the moment an action is about to become real.

Canonical Authority Drift scenario:

```text
08:00   mandate                    $50,000
09:00   authority changes          $25,000
09:05   attempted consequence      $45,000
                              ↓
                     fresh authority check
                              ↓
                       DENY / ESCALATE
                              ↓
                      verifiable receipt
```

The important observation is not that the original intent was invalid. It is that authority changed before consequence.

## EROC Replay

**Live:** https://reht.valoresearch.org/demos/eroc-replay/

Purpose: inspect the evidence path by replaying a governed execution from recorded artifacts.

Replay is part of the control model: a consequence should not only happen through a governed path; the decision and effect path should remain inspectable afterward.

## Demo rule

A HEIMEL demo must expose an actual mechanism or executable path. A static scenario, diagram or prose explanation is an illustration, not a demo.

## Public contract chain

The offline public-contract demo exercises MAL policy federation, c-MCP
binding, read-only surface conformance, VAIG gate status and procurement
evidence in one local process. It performs no network request and no external
effect:

```bash
python -m pip install "valo-sdk==0.1.3"
valo-contracts demo
```

The `heimel-boundary` package provides the minimal runnable consequence-boundary
reference: local authority state issues a permit for one exact effect, the
gateway rejects stale, expired, mismatched and replayed permits, and a receipt
records the local simulated outcome. It never calls an external effect.
